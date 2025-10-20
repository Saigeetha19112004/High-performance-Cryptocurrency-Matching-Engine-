# engine_server.py
import asyncio
import json
import time

from websockets.server import serve, WebSocketServerProtocol, broadcast
from typing import Set, List, Dict
from order_book import OrderBook
from order_types import Order

# --- Global State & Isolation (Persistence Integrated) ---
# Load state on startup (BONUS #2)
ORDER_BOOK = OrderBook.load_state(symbol="BTC-USDT") 
ENGINE_QUEUE: asyncio.Queue = asyncio.Queue()

# Client subscription sets for real-time data
MARKET_DATA_SUBSCRIBERS: Set[WebSocketServerProtocol] = set()
TRADE_SUBSCRIBERS: Set[WebSocketServerProtocol] = set()

# --- 1. The Single-Threaded Core Loop ---

async def matching_engine_loop():
    """The heart of the system. Runs sequentially for strict FIFO processing."""
    print("Matching Engine Core Started: Waiting for Orders...")
    while True:
        try:
            incoming_order: Order = await ENGINE_QUEUE.get()
            
            trades = ORDER_BOOK.process_order(incoming_order)
            
            if trades:
                await broadcast_trades(trades)
                
            await broadcast_order_book_update()
            
            ENGINE_QUEUE.task_done()

        except Exception as e:
            print(f"CRITICAL ENGINE ERROR: {e}")

# --- 2. Real-Time Data Broadcasts ---

async def broadcast_trades(trades: List[Dict]):
    """Pushes trade reports to all subscribers."""
    if TRADE_SUBSCRIBERS:
        message = json.dumps({"type": "TRADE_REPORT", "trades": trades})
        await asyncio.gather(*(ws.send(message) for ws in TRADE_SUBSCRIBERS), return_exceptions=True)

async def broadcast_order_book_update():
    """Pushes the current BBO/L2 snapshot to all subscribers."""
    if MARKET_DATA_SUBSCRIBERS:
        # Get top 10 price levels
        bids = [{"price": p, "quantity": ORDER_BOOK.bids[p].total_volume} for p in ORDER_BOOK.get_sorted_prices("BUY")][:10]
        asks = [{"price": p, "quantity": ORDER_BOOK.asks[p].total_volume} for p in ORDER_BOOK.get_sorted_prices("SELL")][:10]
        
        update = {
            "type": "L2_UPDATE",
            "timestamp": time.time(),
            "symbol": ORDER_BOOK.symbol,
            "bids": bids,
            "asks": asks
        }
        message = json.dumps(update)
        await asyncio.gather(*(ws.send(message) for ws in MARKET_DATA_SUBSCRIBERS), return_exceptions=True)

# --- 3. WebSocket API Handlers (Order Submission is now at ws://localhost:8000) ---

async def order_submission_handler(websocket: WebSocketServerProtocol, path: str):
    """API endpoint to receive new orders and queue them for the engine."""
    async for message in websocket:
        try:
            order_data = json.loads(message)
            
            # Simple Validation
            if not all(k in order_data for k in ['user_id', 'side', 'quantity', 'order_type']):
                 await websocket.send(json.dumps({"status": "REJECTED", "reason": "Missing fields."}))
                 continue

            new_order = Order(
                order_id=ORDER_BOOK.get_new_id(),
                user_id=order_data['user_id'],
                side=order_data['side'].upper(),
                price=order_data.get('price', 0.0),
                quantity=order_data['quantity'],
                order_type=order_data['order_type'].upper()
            )
            
            await ENGINE_QUEUE.put(new_order)
            await websocket.send(json.dumps({"status": "ACCEPTED", "order_id": new_order.order_id}))
            
        except Exception as e:
            await websocket.send(json.dumps({"status": "ERROR", "reason": str(e)}))

async def market_data_feed(websocket: WebSocketServerProtocol, path: str):
    """Handles subscriptions for real-time BBO/L2 Order Book."""
    MARKET_DATA_SUBSCRIBERS.add(websocket)
    try:
        await broadcast_order_book_update()
        await websocket.wait_closed()
    finally:
        MARKET_DATA_SUBSCRIBERS.remove(websocket)

async def trade_execution_feed(websocket: WebSocketServerProtocol, path: str):
    """Handles subscriptions for Trade Execution Reports."""
    TRADE_SUBSCRIBERS.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        TRADE_SUBSCRIBERS.remove(websocket)

# --- Main Runner ---
async def main():
    asyncio.create_task(matching_engine_loop())
    
    order_server = serve(order_submission_handler, "localhost", 8000, subprotocols=["order-submission"])
    market_server = serve(market_data_feed, "localhost", 8001, subprotocols=["market-data"])
    trade_server = serve(trade_execution_feed, "localhost", 8002, subprotocols=["trades"])

    print("--- Matching Engine Server Running ---")
    print("Order Submission (Taker API): ws://localhost:8000")
    print("Market Data (L2/BBO Feed): ws://localhost:8001")
    print("Trade Execution Feed: ws://localhost:8002")
    
    async with order_server, market_server, trade_server:
        await asyncio.Future()

if __name__ == "__main__":
    import websockets
    asyncio.run(main())