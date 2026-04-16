from collections import deque
from threading import Lock
from time import monotonic


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        if limit <= 0 or window_seconds <= 0:
            return True
        now = monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] < cutoff:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True


GLOBAL_RATE_LIMITER = RateLimiter()
