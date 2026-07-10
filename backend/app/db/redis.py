"""The shared async Redis client.

One client serves everything that touches Redis — OAuth sessions now, guest-run
state and rate-limit counters in later phases. Built lazily and memoized, like the
Postgres engine (app/db/engine.py), so importing this module never opens a
connection or requires REDIS_URL to be set.

decode_responses=True means reads come back as str, not bytes — sessions store and
compare plain strings.
"""

from functools import lru_cache

import redis.asyncio as redis

from app.config import get_settings


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    """Build (once) and return the process-wide async Redis client."""
    # from_url lacks precise type hints in redis-py. decode_responses=True means
    # reads come back as str.
    client: redis.Redis = redis.from_url(  # type: ignore[no-untyped-call]
        get_settings().redis_url, decode_responses=True
    )
    return client
