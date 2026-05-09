"""In-memory LRU cache fallback when Redis is unavailable.

PRD Section 6: "如无外置组件条件，演示时可短暂降级为内存 LRU Cache，
但在设计思路上必须预留接口"
"""

from collections import OrderedDict
import logging
import time

logger = logging.getLogger(__name__)

DEFAULT_MAX_SIZE = 128
DEFAULT_TTL = 3600  # 1 hour


class LRUMemoryCache:
    """Simple LRU cache with TTL support for fallback when Redis is down."""

    def __init__(self, max_size: int = DEFAULT_MAX_SIZE) -> None:
        self._max_size = max_size
        self._store: OrderedDict[str, tuple[float, str]] = OrderedDict()
        # OrderedDict[ key -> (expire_at, json_data) ]

    def _evict_expired(self) -> None:
        now = time.monotonic()
        expired = [k for k, (exp, _) in self._store.items() if exp < now]
        for k in expired:
            del self._store[k]

    def get(self, key: str) -> str | None:
        self._evict_expired()
        entry = self._store.get(key)
        if entry is None:
            return None
        expire_at, data = entry
        if expire_at < time.monotonic():
            del self._store[key]
            return None
        # Move to end (most recently used)
        self._store.move_to_end(key)
        return data

    def set(self, key: str, value: str, ttl: int = DEFAULT_TTL) -> None:
        self._evict_expired()
        if key in self._store:
            self._store.move_to_end(key)
        else:
            # Evict LRU if at capacity
            while len(self._store) >= self._max_size:
                self._store.popitem(last=False)
        expire_at = time.monotonic() + ttl
        self._store[key] = (expire_at, value)
        logger.debug("Memory cache set: key=%s, entries=%d", key, len(self._store))

    @property
    def size(self) -> int:
        self._evict_expired()
        return len(self._store)


# Global singleton for fallback
_memory_cache: LRUMemoryCache | None = None


def get_memory_cache() -> LRUMemoryCache:
    global _memory_cache
    if _memory_cache is None:
        _memory_cache = LRUMemoryCache()
    return _memory_cache
