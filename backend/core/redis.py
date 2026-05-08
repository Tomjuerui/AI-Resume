import redis.asyncio as redis
from core.config import settings

_pool: redis.ConnectionPool | None = None


async def get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(
            settings.redis_dsn,
            password=settings.redis_password or None,
            max_connections=10,
        )
    return redis.Redis(connection_pool=_pool)
