"""Redis caching layer with in-memory LRU fallback.

Cache key: resume:{pdf_md5}:{jd_md5}
"""

import hashlib
import json
import logging
from pathlib import Path

from core.redis import get_redis
from services.pdf_service import compute_md5

logger = logging.getLogger(__name__)

DEFAULT_TTL = 3600  # 1 hour


def _make_key(file_md5: str, jd_text: str) -> str:
    """Build composite cache key from file MD5 and JD text."""
    jd_hash = hashlib.md5(jd_text.encode("utf-8")).hexdigest()
    return f"resume:{file_md5}:{jd_hash}"


async def get_cached_result(file_md5: str, jd_text: str) -> dict | None:
    """Try to retrieve cached analysis result by file MD5 + JD hash."""
    key = _make_key(file_md5, jd_text)

    # Try Redis first
    try:
        r = await get_redis()
        data = await r.get(key)
        if data:
            logger.info("Redis cache hit: key=%s", key)
            return json.loads(data)
    except Exception as e:
        logger.warning("Redis read failed, falling back to memory cache: %s", e)

    # Fallback to in-memory LRU cache
    try:
        from services.memory_cache import get_memory_cache
        mc = get_memory_cache()
        data = mc.get(key)
        if data:
            logger.info("Memory cache hit: key=%s", key)
            return json.loads(data)
    except Exception:
        pass

    return None


async def set_cached_result(
    file_md5: str, jd_text: str, result: dict, ttl: int = DEFAULT_TTL
) -> None:
    """Cache analysis result with TTL.

    Writes to both Redis and in-memory fallback cache.
    """
    key = _make_key(file_md5, jd_text)
    json_data = json.dumps(result, ensure_ascii=False)

    # Write to Redis
    try:
        r = await get_redis()
        await r.setex(key, ttl, json_data)
        logger.info("Redis cache set: key=%s", key)
    except Exception as e:
        logger.warning("Redis write failed, using memory cache only: %s", e)

    # Always write to memory cache as backup
    try:
        from services.memory_cache import get_memory_cache
        mc = get_memory_cache()
        mc.set(key, json_data, ttl=ttl)
    except Exception:
        pass


# ── Backward-compatible wrappers (file_path based) ──

async def get_cached_result_by_path(file_path: Path) -> dict | None:
    """Legacy: retrieve cached result by file path (MD5 only, no JD)."""
    r = await get_redis()
    key = f"resume:{compute_md5(file_path)}"
    data = await r.get(key)
    if data:
        return json.loads(data)
    return None


async def set_cached_result_by_path(
    file_path: Path, result: dict, ttl: int = DEFAULT_TTL
) -> None:
    """Legacy: cache result by file path MD5."""
    r = await get_redis()
    key = f"resume:{compute_md5(file_path)}"
    await r.setex(key, ttl, json.dumps(result, ensure_ascii=False))
