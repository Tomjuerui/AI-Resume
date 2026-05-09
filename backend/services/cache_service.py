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
TASK_TTL = 900  # 15 minutes


def _make_key(file_md5: str, jd_text: str) -> str:
    """Build composite cache key from file MD5 and JD text."""
    jd_hash = hashlib.md5(jd_text.encode("utf-8")).hexdigest()
    return f"resume:{file_md5}:{jd_hash}"


def _make_final_key(file_md5: str, jd_text: str) -> str:
    return f"{_make_key(file_md5, jd_text)}:final"


def _make_task_key(task_id: str) -> str:
    return f"task:{task_id}"


def _make_task_index_key(file_md5: str, jd_text: str) -> str:
    jd_hash = hashlib.md5(jd_text.encode("utf-8")).hexdigest()
    return f"task_index:{file_md5}:{jd_hash}"


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


async def _read_cache(key: str) -> dict | None:
    """Read from Redis, fall back to memory cache."""
    try:
        r = await get_redis()
        data = await r.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    try:
        from services.memory_cache import get_memory_cache
        mc = get_memory_cache()
        data = mc.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


async def _write_cache(key: str, json_data: str, ttl: int) -> None:
    """Write to both Redis and memory cache."""
    try:
        r = await get_redis()
        await r.setex(key, ttl, json_data)
    except Exception:
        pass
    try:
        from services.memory_cache import get_memory_cache
        mc = get_memory_cache()
        mc.set(key, json_data, ttl=ttl)
    except Exception:
        pass


async def get_task_state(task_id: str) -> dict | None:
    """Retrieve async task state by task_id."""
    key = _make_task_key(task_id)
    return await _read_cache(key)


async def set_task_state(task_id: str, state: dict, ttl: int = TASK_TTL) -> None:
    """Store async task state (Redis + Memory fallback)."""
    await _write_cache(_make_task_key(task_id), json.dumps(state, ensure_ascii=False), ttl)


async def get_final_result(file_md5: str, jd_text: str) -> dict | None:
    """Retrieve final async analysis result, with legacy fallback."""
    result = await _read_cache(_make_final_key(file_md5, jd_text))
    if result:
        return result
    return await get_cached_result(file_md5, jd_text)


async def set_final_result(file_md5: str, jd_text: str, result: dict, ttl: int = DEFAULT_TTL) -> None:
    """Store final async result (new key + legacy key)."""
    json_data = json.dumps(result, ensure_ascii=False)
    await _write_cache(_make_final_key(file_md5, jd_text), json_data, ttl)
    await set_cached_result(file_md5, jd_text, result, ttl)


async def get_task_index(file_md5: str, jd_text: str) -> str | None:
    """Return existing task_id for the same file+JD, or None."""
    key = _make_task_index_key(file_md5, jd_text)
    try:
        r = await get_redis()
        data = await r.get(key)
        if data:
            return data.decode("utf-8") if isinstance(data, bytes) else str(data)
    except Exception as e:
        logger.warning("Redis task-index read failed: %s", e)

    try:
        from services.memory_cache import get_memory_cache
        mc = get_memory_cache()
        return mc.get(key)
    except Exception:
        return None


async def set_task_index(file_md5: str, jd_text: str, task_id: str, ttl: int = TASK_TTL) -> None:
    """Store idempotency index: (file_md5, jd_text) → task_id."""
    key = _make_task_index_key(file_md5, jd_text)
    try:
        r = await get_redis()
        await r.setex(key, ttl, task_id)
    except Exception as e:
        logger.warning("Redis task-index write failed: %s", e)
    try:
        from services.memory_cache import get_memory_cache
        mc = get_memory_cache()
        mc.set(key, task_id, ttl=ttl)
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
