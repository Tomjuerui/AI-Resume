"""FastAPI dependency injection.

Tech Design: "依赖注入 (如鉴权、获取 Redis 连接)"
"""

import redis.asyncio as redis

from core.config import settings


async def get_redis() -> redis.Redis:
    """Dependency: provide an async Redis connection from the pool.

    Usage in route:
        @router.get("/example")
        async def example(r: redis.Redis = Depends(get_redis)):
            ...
    """
    pool = redis.ConnectionPool.from_url(
        settings.redis_dsn,
        password=settings.redis_password or None,
        max_connections=10,
    )
    return redis.Redis(connection_pool=pool)
