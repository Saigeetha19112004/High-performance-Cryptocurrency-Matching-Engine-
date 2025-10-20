# client_test.py
import asyncio
import websockets
import json
import random
import time

ORDER_SUBMISSION_URL = "ws://localhost:8000"
MARKET_DATA_URL = "ws://localhost:8001"
TRADE_FEED_URL = "ws://localhost:8002"

# --- 1. Order Submission Logic ---

async def submit_order(order_data):
    """Connects, sends a single order, and waits for acceptance."""
    try:
        start_submission = time.perf_counter_ns()
        async with websockets.connect(ORDER_SUBMISSION_URL, subprotocols=["order-submission"]) as websocket:
            print(f"\n[CLIENT] Sending Order: {order_data['order_type']} {order_data['side']} {order_data['quantity']} @ {order_data.get('price', 'N/A')}")
            await websocket.send(json.dumps(order_data))
            response = await websocket.recv()
            print(f"[CLIENT] Engine Response: {response}")
        end_submission = time.perf_counter_ns()
        print(f"[BENCHMARK] Submission Time: {(end_submission - start_submission) / 1e6:.3f} ms")

    except Exception as e:
        print(f"[CLIENT ERROR] Could not connect or send order: {e}")

async def run_submission_scenarios():
    """Defines a sequence of test orders to submit."""
    user_id = 900
    
    # --- 1. Build the Book ---
    print("\n--- Phase 1: Building Book (Bids: 98, 95 Asks: 104, 105) ---")
    await submit_order({
        "user_id": user_id + 1, "order_type": "LIMIT", "side": "BUY", "price": 98.00, "quantity": 10.0 
    })
    # Time Priority Check: Oldest at 95.00
    await submit_order({
        "user_id": user_id + 2, "order_type": "LIMIT", "side": "BUY", "price": 95.00, "quantity": 15.0 
    })
    await submit_order({
        "user_id": user_id + 4, "order_type": "LIMIT", "side": "SELL", "price": 104.00, "quantity": 20.0 # BBO
    })
    await submit_order({
        "user_id": user_id + 5, "order_type": "LIMIT", "side": "SELL", "price": 105.00, "quantity": 10.0
    })
    
    await asyncio.sleep(1) 

    # --- 2. Market Order (Internal Order Protection & Fees) ---
    print("\n--- Phase 2: MARKET Order Match (Tests Fees & Latency) ---")
    # This BUY order should fill 20 @ 104.00 and 10 @ 105.00
    await submit_order({
        "user_id": user_id + 6, "order_type": "MARKET", "side": "BUY", "quantity": 30.0
    })
    
    await asyncio.sleep(1)

    # --- 3. FOK Order Check ---
    print("\n--- Phase 3: FOK Order Check (Should be rejected) ---")
    # Book is currently empty on Ask side. Bid is 98.00 (10 units).
    # This FOK SELL order requires 15 units. It should fail (no fill) and be rejected.
    await submit_order({
        "user_id": user_id + 7, "order_type": "FOK", "side": "SELL", "price": 90.00, "quantity": 15.0
    })
    
    await asyncio.sleep(1)

    # --- 4. Persistence Check ---
    print("\n--- Phase 4: PERSISTENCE CHECK (Manually Restart Server Now!) ---")
    print("Submit another order to check if the 10 units @ 98.00 are still there.")
    # This SELL order should match the remaining 10 units @ 98.00
    await submit_order({
        "user_id": user_id + 8, "order_type": "MARKET", "side": "SELL", "quantity": 10.0
    })

# --- 2. Data Subscription Logic ---

async def subscribe_feed(url, name):
    """Subscribes to a WebSocket feed and prints incoming messages."""
    try:
        async with websockets.connect(url) as websocket:
            print(f"\n[SUBSCRIBER] Connected to {name} feed: {url}")
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data.get('type') == 'L2_UPDATE':
                    bids = f"{data['bids'][0]['price']} ({data['bids'][0]['quantity']})" if data['bids'] else "EMPTY"
                    asks = f"{data['asks'][0]['price']} ({data['asks'][0]['quantity']})" if data['asks'] else "EMPTY"
                    print(f"--- {name} --- BBO: BIDS={bids} | ASKS={asks}")
                    
                elif data.get('type') == 'TRADE_REPORT':
                    for trade in data['trades']:
                         # Latency and Fees included in printout (BONUS #3 & #4)
                         latency_ms = trade.get('engine_latency_ns', 0) / 1e6
                         print(f"*** TRADE *** ID: {trade['trade_id']} | QTY: {trade['quantity']} @ {trade['price']} | Taker Fee: {trade['taker_fee']:.4f} | Latency: {latency_ms:.3f} ms")
                         
    except Exception as e:
        print(f"[SUBSCRIBER ERROR] Disconnected from {name} feed: {e}")

async def run_client():
    market_task = asyncio.create_task(subscribe_feed(MARKET_DATA_URL, "MARKET_DATA"))
    trade_task = asyncio.create_task(subscribe_feed(TRADE_FEED_URL, "TRADE_FEED"))
    
    await asyncio.sleep(1.5) 
    
    await run_submission_scenarios()
    
    await asyncio.gather(market_task, trade_task, return_exceptions=True)

if __name__ == "__main__":
    print("Starting client. Ensure engine_server.py is running in a separate terminal.")
    asyncio.run(run_client())