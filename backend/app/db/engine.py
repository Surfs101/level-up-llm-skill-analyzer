"""The async database engine and session factory.

The whole app reaches Postgres through the one engine built here. Everything is
lazy: the engine is created on first use, not at import, so simply importing this
module never requires a configured DATABASE_URL or an open database — that keeps
unit tests and tooling that don't touch the DB free of a Postgres dependency.
"""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

# We only support the asyncpg driver. A sync DSN (e.g. plain "postgresql://") would
# fail later inside the engine with a confusing error, so we reject it up front.
_ASYNC_DSN_PREFIX = "postgresql+asyncpg://"


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Build (once) and return the process-wide async engine."""
    database_url = get_settings().database_url
    if not database_url.startswith(_ASYNC_DSN_PREFIX):
        raise ValueError(
            f"DATABASE_URL must be an async DSN starting with {_ASYNC_DSN_PREFIX!r}, "
            f"got {database_url!r}"
        )
    return create_async_engine(database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Build (once) and return the session factory bound to the engine.

    expire_on_commit=False so attributes stay usable after commit — the common
    case when a request reads a row and serializes it in the response.
    """
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield one session, closing it when the caller is done.

    Used as a FastAPI dependency and anywhere a scoped session is needed.
    """
    async with get_sessionmaker()() as session:
        yield session
