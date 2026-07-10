"""Server-side sessions, backed by Redis.

A session is a random opaque id stored only in an HttpOnly cookie; the mapping
session_id -> user_id lives in Redis with a sliding TTL. No JWTs, no data in the
cookie, nothing in localStorage — logout just deletes the Redis key and the session
is gone.

Every function takes the Redis client as an argument (the routes pass the shared
one via get_redis) so this module stays pure and unit-testable against fakeredis.
"""

import secrets
import uuid
from collections.abc import Awaitable
from datetime import UTC, datetime, timedelta
from typing import cast

import redis.asyncio as redis

_KEY_PREFIX = "session:"

# redis-py's async methods are typed with a sync/async union return, so mypy can't
# see that awaiting them is valid. We cast the specific calls we await to their
# real awaitable type — a known redis-py typing gap, not a real ambiguity.


async def create_session(client: redis.Redis, user_id: uuid.UUID, ttl_seconds: int) -> str:
    """Create a session for a user and return its id (goes in the cookie).

    The id is 32 random bytes, URL-safe encoded — unguessable, no collisions in
    practice.
    """
    session_id = secrets.token_urlsafe(32)
    await _write(client, session_id, user_id, ttl_seconds)
    return session_id


async def read_session(client: redis.Redis, session_id: str, ttl_seconds: int) -> uuid.UUID | None:
    """Return the session's user_id, or None if it's missing or expired.

    Sliding expiry: every successful read pushes the TTL back out to the full
    window, so an active user is never logged out mid-use.
    """
    stored = await cast("Awaitable[str | None]", client.hget(_KEY_PREFIX + session_id, "user_id"))
    if stored is None:
        return None
    await _write(client, session_id, uuid.UUID(stored), ttl_seconds)  # slide the window
    return uuid.UUID(stored)


async def revoke_session(client: redis.Redis, session_id: str) -> None:
    """Delete a session (logout). A no-op if it's already gone."""
    await client.delete(_KEY_PREFIX + session_id)


async def _write(
    client: redis.Redis, session_id: str, user_id: uuid.UUID, ttl_seconds: int
) -> None:
    """Store user_id + expires_at under the session key and (re)set its TTL."""
    key = _KEY_PREFIX + session_id
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
    mapping = {"user_id": str(user_id), "expires_at": expires_at.isoformat()}
    await cast("Awaitable[int]", client.hset(key, mapping=mapping))
    await cast("Awaitable[bool]", client.expire(key, ttl_seconds))
