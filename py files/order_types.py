# order_types.py
import time
from collections import deque
from typing import Deque, Dict, Tuple

# --- FEE CONSTANTS (BONUS #4) ---
# These rates are applied to the executed trade value (price * quantity)
MAKER_FEE_RATE = 0.0010  # 0.10% (Resting Order - Provides Liquidity)
TAKER_FEE_RATE = 0.0020  # 0.20% (Aggressive Order - Removes Liquidity)

class Order:
    """Represents a single order in the system."""
    def __init__(self, order_id: int, user_id: int, side: str, price: float, quantity: float, order_type: str):
        self.order_id = order_id
        self.user_id = user_id
        self.side = side          # "BUY" or "SELL"
        self.price = price        # Required for LIMIT, IOC, FOK
        self.quantity = quantity
        self.initial_quantity = quantity  # Original size for fee/audit reference
        self.timestamp = time.time()
        self.order_type = order_type # "LIMIT", "MARKET", "IOC", "FOK"

    def __repr__(self):
        return (f"Order(ID={self.order_id}, Side={self.side}, P={self.price:.2f}, "
                f"Q={self.quantity:.2f}, Type={self.order_type})")

class PriceLevel:
    """
    Container for all orders at a single price point.
    Uses deque to enforce Time Priority (FIFO).
    """
    def __init__(self):
        self.orders: Deque['Order'] = deque()
        self.total_volume: float = 0.0

    def append_order(self, order: 'Order'):
        """Adds a new order to the end of the queue (FIFO)."""
        self.orders.append(order)
        self.total_volume += order.quantity

    def pop_oldest_order(self) -> 'Order':
        """Removes and returns the oldest order (front of the queue)."""
        order = self.orders.popleft()
        self.total_volume -= order.quantity
        return order

    def get_top_order(self) -> 'Order':
        """Returns the oldest order without removing it."""
        return self.orders[0]

    def __bool__(self):
        return len(self.orders) > 0

# Type Alias for clarity
OrderIdMap = Dict[int, Order]