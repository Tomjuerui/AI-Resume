import json
from pathlib import Path

from core.redis import get_redis
from services.pdf_service import compute_md5


async def get_cached_result(file_path: Path) -> dict | None:
    """Try to retrieve cached analysis result by file MD5."""
    r = await get_redis()
    key = f"resume:{compute_md5(file_path)}"
    data = await r.get(key)
    if data:
        return json.loads(data)
    return None


async def set_cached_result(file_path: Path, result: dict, ttl: int = 3600) -> None:
    """Cache analysis result with TTL (default 1 hour)."""
    r = await get_redis()
    key = f"resume:{compute_md5(file_path)}"
    await r.setex(key, ttl, json.dumps(result, ensure_ascii=False))
