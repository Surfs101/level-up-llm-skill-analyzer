"""Unit tests for Redis-backed sessions, run against fakeredis (no live Redis)."""

import uuid
from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest

from app.auth.sessions import create_session, read_session, revoke_session

TTL = 604800  # 7 days


@pytest.fixture
async def client() -> AsyncIterator[fakeredis.aioredis.FakeRedis]:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield fake
    await fake.aclose()


async def test_create_then_read_returns_the_user(client: fakeredis.aioredis.FakeRedis) -> None:
    user_id = uuid.uuid4()
    session_id = await create_session(client, user_id, TTL)

    assert session_id  # non-empty opaque token
    assert await read_session(client, session_id, TTL) == user_id


async def test_read_unknown_session_returns_none(client: fakeredis.aioredis.FakeRedis) -> None:
    assert await read_session(client, "does-not-exist", TTL) is None


async def test_revoke_makes_the_session_unreadable(client: fakeredis.aioredis.FakeRedis) -> None:
    session_id = await create_session(client, uuid.uuid4(), TTL)

    await revoke_session(client, session_id)

    assert await read_session(client, session_id, TTL) is None


async def test_revoke_is_a_noop_for_a_missing_session(
    client: fakeredis.aioredis.FakeRedis,
) -> None:
    await revoke_session(client, "does-not-exist")  # must not raise


async def test_create_sets_a_ttl(client: fakeredis.aioredis.FakeRedis) -> None:
    session_id = await create_session(client, uuid.uuid4(), TTL)

    ttl = await client.ttl("session:" + session_id)
    assert 0 < ttl <= TTL


async def test_read_slides_the_ttl_back_to_full(client: fakeredis.aioredis.FakeRedis) -> None:
    session_id = await create_session(client, uuid.uuid4(), TTL)
    key = "session:" + session_id

    # Simulate a session that's about to expire, then read it.
    await client.expire(key, 5)
    assert await client.ttl(key) <= 5

    await read_session(client, session_id, TTL)

    assert await client.ttl(key) > 5  # the read pushed expiry back out
