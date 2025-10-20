# id_generator.py

class IDGenerator:
    """
    A simple, fast, non-thread-safe, monotonically increasing ID generator.
    Designed to be used only from within the single-threaded engine loop
    or a single I/O thread to guarantee uniqueness without locks.
    """
    def __init__(self, start_id: int = 1):
        self._id = start_id

    def get_new_id(self) -> int:
        """Generates and returns a new unique ID."""
        new_id = self._id
        self._id += 1
        return new_id