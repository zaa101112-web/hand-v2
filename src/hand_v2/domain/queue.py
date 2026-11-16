from collections import deque


class CommandQueue:
    """Bounded ordinary commands; STOP/release never enter this queue."""
    def __init__(self, capacity=8):
        self.capacity = capacity
        self._items = deque()

    def offer(self, command):
        if len(self._items) >= self.capacity:
            return False
        self._items.append(command)
        return True

    def take(self):
        return self._items.popleft() if self._items else None

    def clear(self):
        items = tuple(self._items)
        self._items.clear()
        return items

    def __len__(self):
        return len(self._items)
