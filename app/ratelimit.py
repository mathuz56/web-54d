# app/ratelimit.py
import time
import threading

class RateLimiter:
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            q = [t for t in self._hits.get(key, []) if now - t < self.window]
            if len(q) >= self.limit:
                self._hits[key] = q
                return False
            q.append(now)
            self._hits[key] = q
            return True
