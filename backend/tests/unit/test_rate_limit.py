"""Rate-limit tests — the enforce() helper and the three route limits.

All fakeredis, no Postgres: the guest /analyze path touches no DB, and the authed +
auth-endpoint cases mock the user / OAuth so the DB is never reached.
"""

import uuid

import fakeredis.aioredis
import pytest
from authlib.integrations.starlette_client import OAuth
from httpx import ASGITransport, AsyncClient

from app.auth import google
from app.common.rate_limit import RateLimit, RateLimitExceeded, enforce
from app.deps import get_current_user_optional, get_db, get_redis
from app.main import create_app
from app.models import User
from app.workers.queue import get_arq_pool

PDF = ("r.pdf", b"%PDF-1.4", "application/pdf")


class FakeArqPool:
    async def enqueue_job(self, name: str, *args: object) -> None:
        return None


@pytest.fixture
def fake_redis() -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


async def override_get_db_noop():  # type: ignore[no-untyped-def]
    yield None  # guests / pre-limit rejections never touch the DB


async def test_enforce_allows_up_to_limit_then_raises(fake_redis) -> None:  # type: ignore[no-untyped-def]
    rule = RateLimit(limit=3, window_seconds=60)
    for _ in range(3):
        await enforce(fake_redis, "k", rule)  # 1st–3rd are fine
    with pytest.raises(RateLimitExceeded):
        await enforce(fake_redis, "k", rule)  # 4th is over
    assert await fake_redis.ttl("k") > 0  # the window TTL was set


async def test_guest_analyze_limited_to_five_per_day(fake_redis) -> None:  # type: ignore[no-untyped-def]
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db_noop
    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_arq_pool] = lambda: FakeArqPool()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(5):  # a guest (no cookie) — 5 allowed
            ok = await client.post("/analyze", data={"jd_text": "x"}, files={"resume": PDF})
            assert ok.status_code == 202
        blocked = await client.post("/analyze", data={"jd_text": "x"}, files={"resume": PDF})

    assert blocked.status_code == 429  # the 6th
    assert blocked.json()["error"] == "rate_limited"


async def test_authed_analyze_limited_to_twenty_per_day(fake_redis) -> None:  # type: ignore[no-untyped-def]
    user = User(id=uuid.uuid4(), google_sub="rl-user", email="rl@example.com")
    await fake_redis.set(f"rl:user:{user.id}", "20")  # already at the daily limit

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db_noop
    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_arq_pool] = lambda: FakeArqPool()
    app.dependency_overrides[get_current_user_optional] = lambda: user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        blocked = await client.post("/analyze", data={"jd_text": "x"}, files={"resume": PDF})

    assert blocked.status_code == 429  # the 21st — rejected before any DB write


async def test_auth_endpoints_limited_per_ip(fake_redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    oauth = OAuth()
    oauth.register(
        name="google",
        client_id="x",
        client_secret="y",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        access_token_url="https://oauth2.googleapis.com/token",
        client_kwargs={"scope": "openid", "code_challenge_method": "S256"},
    )
    monkeypatch.setattr(google, "get_oauth", lambda: oauth)

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db_noop
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as client:
        statuses = [(await client.get("/auth/google/login")).status_code for _ in range(21)]

    assert all(s in (302, 307) for s in statuses[:20])  # first 20 redirect to Google
    assert statuses[20] == 429  # the 21st in the window
