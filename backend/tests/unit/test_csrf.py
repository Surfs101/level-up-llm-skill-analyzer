"""CSRF double-submit tests — the reject paths on the two protected writes.

All fakeredis, no Postgres: require_csrf runs as a route dependency, so a missing or
mismatched token is rejected with 403 before the handler (and its DB) runs. The
*accept* path (valid token → 200/204) is exercised by the dashboard/plans route tests,
which now send a matching cookie + header.
"""

import uuid

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

from app.common.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME
from app.deps import get_current_user, get_db, get_redis
from app.main import create_app
from app.models import User


async def override_get_db_noop():  # type: ignore[no-untyped-def]
    yield None  # a rejected request never reaches the handler's DB use


@pytest.fixture
def fake_redis() -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


def make_app(fake_redis):  # type: ignore[no-untyped-def]
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db_noop
    app.dependency_overrides[get_redis] = lambda: fake_redis
    # A signed-in user so auth passes and only the CSRF check can reject.
    app.dependency_overrides[get_current_user] = lambda: User(
        id=uuid.uuid4(), google_sub="csrf-test", email="c@example.com"
    )
    return app


async def test_patch_dashboard_without_csrf_is_forbidden(fake_redis) -> None:  # type: ignore[no-untyped-def]
    app = make_app(fake_redis)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch("/dashboard", json={})
    assert response.status_code == 403


async def test_patch_dashboard_with_mismatched_csrf_is_forbidden(fake_redis) -> None:  # type: ignore[no-untyped-def]
    app = make_app(fake_redis)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set(CSRF_COOKIE_NAME, "cookie-token")
        response = await client.patch(
            "/dashboard", json={}, headers={CSRF_HEADER_NAME: "different-token"}
        )
    assert response.status_code == 403


async def test_delete_plan_without_csrf_is_forbidden(fake_redis) -> None:  # type: ignore[no-untyped-def]
    app = make_app(fake_redis)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/plans/{uuid.uuid4()}")
    assert response.status_code == 403
