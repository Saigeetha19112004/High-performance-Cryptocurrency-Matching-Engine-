# order_book.py
import time
import pickle # Used for Persistence (Bonus #2)
from typing import List, Dict, Union, Tuple
# Import updated constants and classes
from order_types import Order, PriceLevel, OrderIdMap, MAKER_FEE_RATE, TAKER_FEE_RATE 

class OrderBook:
    """
    The Limit Order Book implementing Price-Time Priority and Persistence.
    """
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bids: Dict[float, PriceLevel] = {}
        self.asks: Dict[float, PriceLevel] = {}
        self.orders_map: OrderIdMap = {} 
        self.next_order_id = 1
        self.next_trade_id = 1
        
    def get_new_id(self, is_trade=False) -> int:
        """Generates a unique, monotonically increasing ID."""
        if is_trade:
            new_id = self.next_trade_id
            self.next_trade_id += 1
            return new_id
        else:
            new_id = self.next_order_id
            self.next_order_id += 1
            return new_id

    # --- Structure Management and BBO ---

    def get_sorted_prices(self, side: str) -> List[float]:
        """Returns price keys sorted by priority (O(N) in this POC)."""
        if side == "BUY":
            return sorted(self.bids.keys(), reverse=True) # Highest price first
        else:
            return sorted(self.asks.keys())              # Lowest price first

    def get_bbo(self) -> Tuple[Union[float, None], Union[float, None]]:
        """Calculates Best Bid and Best Offer (BBO)."""
        best_bid = max(self.bids.keys()) if self.bids else None
        best_ask = min(self.asks.keys()) if self.asks else None
        return best_bid, best_ask

    def get_marketable_side(self, incoming_side: str) -> Tuple[Dict[float, PriceLevel], List[float]]:
        """Returns the opposing book and the prioritized price list."""
        if incoming_side == "BUY":
            return self.asks, self.get_sorted_prices("SELL")
        else:
            return self.bids, self.get_sorted_prices("BUY")

    # --- Persistence Methods (BONUS #2) ---
    def save_state(self, filename="orderbook_state.pkl"):
        """Saves the current order book state to a file."""
        data_to_save = {
            'bids': self.bids,
            'asks': self.asks,
            'orders_map': self.orders_map,
            'next_order_id': self.next_order_id,
            'next_trade_id': self.next_trade_id
        }
        with open(filename, 'wb') as f:
            pickle.dump(data_to_save, f)

    @classmethod
    def load_state(cls, symbol: str, filename="orderbook_state.pkl") -> 'OrderBook':
        """Loads and returns an OrderBook instance from a saved state file."""
        try:
            with open(filename, 'rb') as f:
                data = pickle.load(f)
            
            book = cls(symbol) # Create a new instance
            book.bids = data['bids']
            book.asks = data['asks']
            book.orders_map = data['orders_map']
            book.next_order_id = data['next_order_id']
            book.next_trade_id = data['next_trade_id']
            print(f"[PERSISTENCE] State successfully loaded from {filename}.")
            return book
        except FileNotFoundError:
            print("[PERSISTENCE] State file not found. Starting with empty book.")
            return cls(symbol) # Start fresh

    # --- Fee Calculation (BONUS #4) ---
    def _calculate_fees(self, fill_qty: float, execution_price: float) -> Tuple[float, float]:
        """Calculates maker and taker fees for a trade."""
        value = fill_qty * execution_price
        taker_fee = value * TAKER_FEE_RATE
        maker_fee = value * MAKER_FEE_RATE
        return taker_fee, maker_fee

    # --- Matching and Order Handling ---

    def add_limit_order(self, order: Order):
        """Adds a non-marketable limit order to its correct price level."""
        side_book = self.bids if order.side == "BUY" else self.asks
        if order.price not in side_book:
            side_book[order.price] = PriceLevel()
        side_book[order.price].append_order(order)
        self.orders_map[order.order_id] = order
    
    def _can_fok_fill(self, order: Order) -> bool:
        """Pre-checks if sufficient volume is available for FOK."""
        required_qty = order.quantity
        available_qty = 0.0
        opposing_book, sorted_prices = self.get_marketable_side(order.side)
        for price in sorted_prices:
            if order.side == "BUY" and order.price < price: break
            if order.side == "SELL" and order.price > price: break
            level = opposing_book.get(price)
            if level:
                available_qty += level.total_volume
            if available_qty >= required_qty:
                return True
        return False
        
    def _handle_remainder(self, order: Order, trades: List[Dict]):
        """Handles any unfilled quantity based on the order type."""
        remaining_qty = order.quantity
        if remaining_qty > 0:
            if order.order_type == "LIMIT":
                self.add_limit_order(order)
            elif order.order_type in ("MARKET", "IOC"):
                print(f"INFO: {order.order_type} ID {order.order_id} filled {order.initial_quantity - remaining_qty} and cancelled {remaining_qty}.")
                order.quantity = 0 
        
    def process_order(self, incoming_order: Order) -> List[Dict]:
        """The core single-threaded matching algorithm (The Waterfall)."""
        
        # --- Start Latency Timer (BONUS #3) ---
        start_time = time.perf_counter_ns()
        
        trades = []
        if incoming_order.order_type == "FOK" and not self._can_fok_fill(incoming_order):
            print(f"FOK Order {incoming_order.order_id} failed to fill completely. Order rejected.")
            return [] 

        # 2. Match Attempt
        opposing_book, sorted_prices = self.get_marketable_side(incoming_order.side)
        
        for price in sorted_prices:
            if incoming_order.quantity <= 0: break
            # Internal Order Protection / Trade-Through Check
            if (incoming_order.side == "BUY" and incoming_order.price < price) or \
               (incoming_order.side == "SELL" and incoming_order.price > price): 
                break 
            
            level = opposing_book.get(price)
            if not level: continue
            
            # Price-Time Priority (FIFO) Match
            while level.orders and incoming_order.quantity > 0:
                resting_order = level.get_top_order() 
                fill_qty = min(incoming_order.quantity, resting_order.quantity)
                execution_price = price 
                
                # Calculate Fees (BONUS #4)
                taker_fee, maker_fee = self._calculate_fees(fill_qty, execution_price)
                
                # Generate Trade Execution Report
                trade_report = {
                    "timestamp": time.time(),
                    "symbol": self.symbol,
                    "trade_id": self.get_new_id(is_trade=True),
                    "price": execution_price,
                    "quantity": fill_qty,
                    "aggressor_side": incoming_order.side,
                    "maker_order_id": resting_order.order_id,
                    "taker_order_id": incoming_order.order_id,
                    "taker_fee": taker_fee,
                    "maker_fee": maker_fee,
                }
                trades.append(trade_report)
                
                # Update Quantities and Cleanup
                incoming_order.quantity -= fill_qty
                resting_order.quantity -= fill_qty
                level.total_volume -= fill_qty
                
                if resting_order.quantity <= 0:
                    level.pop_oldest_order()
                    del self.orders_map[resting_order.order_id]
            
            if not level:
                del opposing_book[price]

        # 3. Handle Order Remainder
        self._handle_remainder(incoming_order, trades)
        
        # --- End Latency Timer (BONUS #3) ---
        end_time = time.perf_counter_ns()
        latency_ns = end_time - start_time
        
        # Attach latency to the first trade for benchmarking report
        if trades:
             trades[0]['engine_latency_ns'] = latency_ns
             
        # Save state (BONUS #2)
        self.save_state() 
        
        return trades