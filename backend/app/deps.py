"""FastAPI dependencies shared across routes.

Three things live here: a request-scoped DB session, the shared Redis client, and
the current-user guard that every authenticated endpoint depends on.
"""

from collections.abc import AsyncIterator

import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.sessions import read_session
from app.config import get_settings
from app.db.engine import get_sessionmaker
from app.db.redis import get_redis_client
from app.models import User


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield one DB session per request, closing it when the request ends."""
    async with get_sessionmaker()() as session:
        yield session


def get_redis() -> redis.Redis:
    """The shared async Redis client."""
    return get_redis_client()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: redis.Redis = Depends(get_redis),
) -> User:
    """Resolve the signed-in user, or raise 401. For authenticated-only endpoints."""
    user = await _resolve_current_user(request, db, client)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: redis.Redis = Depends(get_redis),
) -> User | None:
    """Resolve the signed-in user, or None. For endpoints that also serve guests."""
    return await _resolve_current_user(request, db, client)


async def _resolve_current_user(
    request: Request, db: AsyncSession, client: redis.Redis
) -> User | None:
    """The sid cookie -> Redis session (slides its TTL) -> the User. None if a missing
    cookie, an expired/absent session, or a soft-deleted account."""
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        return None
    user_id = await read_session(client, session_id, settings.session_ttl_seconds)
    if user_id is None:
        return None
    user = await db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        return None
    return user
