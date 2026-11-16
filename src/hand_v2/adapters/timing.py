import heapq
import itertools
import time


class MonotonicClock:
    def now_ms(self):
        return time.monotonic_ns() // 1_000_000


class ManualClock:
    def __init__(self, now=0):
        self._now = now

    def now_ms(self):
        return self._now

    def advance_to(self, at_ms):
        if type(at_ms) is not int or at_ms < self._now:
            raise ValueError("manual time must advance monotonically")
        self._now = at_ms


class SequenceIds:
    def __init__(self):
        self._counter = itertools.count(1)

    def next_id(self, prefix="id"):
        return f"{prefix}-{next(self._counter):06d}"


class Scheduler:
    """Timers are ordered by deadline, then insertion order; no sleeping."""
    def __init__(self, clock):
        self.clock = clock
        self._queue = []
        self._ids = itertools.count(1)
        self._cancelled = set()

    def call_at(self, at_ms, callback):
        token = next(self._ids)
        heapq.heappush(self._queue, (max(at_ms, self.clock.now_ms()), token, callback))
        return token

    def cancel(self, token):
        if token is not None:
            self._cancelled.add(token)

    def run_due(self):
        while self._queue and self._queue[0][0] <= self.clock.now_ms():
            _, token, callback = heapq.heappop(self._queue)
            if token in self._cancelled:
                self._cancelled.remove(token)
            else:
                callback()

    def advance_to(self, at_ms):
        if not isinstance(self.clock, ManualClock):
            raise TypeError("advance_to is only supported for manual time")
        if at_ms < self.clock.now_ms():
            raise ValueError("cannot move backwards")
        while self._queue and self._queue[0][0] <= at_ms:
            self.clock.advance_to(self._queue[0][0])
            self.run_due()
        self.clock.advance_to(at_ms)
        self.run_due()
