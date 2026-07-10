"""Redis-backed fixed-window rate limits (design §10, §11).

The §10 scheme: an INCR-per-window counter. The first request in a window sets the
key with a TTL; each request increments; once the count passes the limit the request
is refused with 429. IPs are never stored — the key uses a sha256 of the client IP
with a per-day salt, so the identifier rotates daily and can't be reversed.

We hand-roll this (rather than slowapi's separate storage) so it reuses the one async
Redis client — which is also what keeps the limits testable against fakeredis.
"""

import hashlib
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

import redis.asyncio as redis
from fastapi import Depends, Request

from app.config import get_settings
from app.deps import get_redis

_DAY_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class RateLimit:
    limit: int
    window_seconds: int


class RateLimitExceeded(Exception):
    """Raised when a caller is over the limit — main.py turns it into a 429."""

    def __init__(self, retry_after: int) -> None:
        super().__init__("rate limit exceeded")
        self.retry_after = retry_after


# Per IP on /auth/* (a person clicks sign-in a few times; this stops hammering).
AUTH_IP_LIMIT = RateLimit(limit=20, window_seconds=60)
# Guests: 5 analyses per 24h per IP (§10, F3).
GUEST_ANALYZE_LIMIT = RateLimit(limit=5, window_seconds=_DAY_SECONDS)
# Signed-in users: 20 analyses per day (§11).
USER_ANALYZE_LIMIT = RateLimit(limit=20, window_seconds=_DAY_SECONDS)


async def enforce(client: redis.Redis, key: str, rule: RateLimit) -> None:
    """Count this request against `key`; raise RateLimitExceeded if over the limit."""
    count = await cast("Awaitable[int]", client.incr(key))
    if count == 1:  # first hit in the window — start its TTL
        await cast("Awaitable[bool]", client.expire(key, rule.window_seconds))
    if count > rule.limit:
        raise RateLimitExceeded(retry_after=rule.window_seconds)


def hashed_ip(request: Request) -> str:
    """A daily-rotating, non-reversible id for the client IP — the IP is never stored."""
    return hashlib.sha256(f"{_client_ip(request)}:{_daily_salt()}".encode()).hexdigest()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()  # first hop = real client (behind Railway's proxy)
    return request.client.host if request.client else "unknown"


def _daily_salt() -> str:
    today = datetime.now(UTC).date().isoformat()
    return hashlib.sha256(f"{get_settings().session_secret}:{today}".encode()).hexdigest()


async def limit_auth_endpoints(request: Request, client: redis.Redis = Depends(get_redis)) -> None:
    """Route dependency: per-IP limit on the /auth/* endpoints."""
    await enforce(client, f"rl:auth:{hashed_ip(request)}", AUTH_IP_LIMIT)
