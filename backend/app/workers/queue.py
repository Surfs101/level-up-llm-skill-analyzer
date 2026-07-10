"""The Arq queue pool the API uses to enqueue jobs.

Built lazily and cached, so importing this module opens no connection. The API
depends on get_arq_pool() to enqueue run_pipeline_one; the worker process
(app/workers/settings.py) has its own connection.
"""

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import get_settings

_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    return _pool
