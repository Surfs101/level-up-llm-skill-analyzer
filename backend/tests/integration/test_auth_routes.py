"""Route tests for the auth flow, with Google fully mocked (no live Google/JWKS).

Split by what they need:
  - login redirect + unauthenticated /me need neither Postgres nor Redis and run
    everywhere (fakeredis stands in for the client).
  - the full callback -> /me -> logout flow needs Postgres (it upserts a real user),
    so it skips cleanly when the database isn't reachable, like the schema test.
"""

from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth import google
from app.auth.google import GoogleClaims
from app.config import get_settings
from app.deps import get_db, get_redis
from app.main import create_app
from app.models import User

TEST_SUB = "test-google-sub-auth-routes"


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def fake_redis() -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


def client_for(app: FastAPI) -> AsyncClient:
    """An httpx client that talks to the ASGI app and does not auto-follow redirects."""
    return AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    )


async def test_login_redirects_to_google_with_pkce(app: FastAPI, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # Register Google with explicit endpoints so Authlib needs no network discovery,
    # but keep the real PKCE machinery so we can assert the challenge is sent.
    oauth = OAuth()
    oauth.register(
        name="google",
        client_id="test-client-id",
        client_secret="test-secret",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        access_token_url="https://oauth2.googleapis.com/token",
        client_kwargs={"scope": "openid email profile", "code_challenge_method": "S256"},
    )
    monkeypatch.setattr(google, "get_oauth", lambda: oauth)
    csrf_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[get_redis] = lambda: csrf_redis

    async with client_for(app) as http:
        response = await http.get("/auth/google/login")

    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "code_challenge=" in location
    assert "code_challenge_method=S256" in location
    assert "client_id=test-client-id" in location


async def test_me_without_a_session_is_401(app: FastAPI, fake_redis) -> None:  # type: ignore[no-untyped-def]
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async with client_for(app) as http:
        response = await http.get("/me")

    assert response.status_code == 401


# --- Full flow (needs Postgres) ---------------------------------------------


@pytest.fixture
async def db_sessionmaker() -> AsyncIterator[async_sessionmaker]:
    """A NullPool session factory, or skip if Postgres isn't reachable."""
    try:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # missing config or unreachable DB — not a failure
        pytest.skip(f"Postgres not reachable, skipping auth flow test: {exc}")

    yield async_sessionmaker(engine, expire_on_commit=False)

    # Clean up the user this test created, then drop the engine.
    async with async_sessionmaker(engine)() as session:
        await session.execute(delete(User).where(User.google_sub == TEST_SUB))
        await session.commit()
    await engine.dispose()


async def test_callback_creates_session_then_me_then_logout(
    app: FastAPI,
    fake_redis,  # type: ignore[no-untyped-def]
    db_sessionmaker: async_sessionmaker,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    async def fake_claims(_request: object) -> GoogleClaims:
        return GoogleClaims(
            google_sub=TEST_SUB,
            email="grad@example.com",
            name="New Grad",
            avatar_url="https://example.com/avatar.png",
        )

    monkeypatch.setattr(google, "fetch_verified_claims", fake_claims)

    async def override_get_db() -> AsyncIterator[object]:
        async with db_sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async with client_for(app) as http:
        # Callback: upserts the user, creates a session, sets the sid cookie.
        callback = await http.get("/auth/google/callback")
        assert callback.status_code == 303
        assert callback.headers["location"] == "/analyze"
        settings = get_settings()
        assert settings.session_cookie_name in callback.cookies

        # The user was persisted.
        async with db_sessionmaker() as session:
            user = await session.scalar(select(User).where(User.google_sub == TEST_SUB))
            assert user is not None
            assert user.email == "grad@example.com"

        # /me returns the signed-in user (cookie carried by the client jar).
        me = await http.get("/me")
        assert me.status_code == 200
        body = me.json()
        assert body["email"] == "grad@example.com"
        assert body["name"] == "New Grad"
        assert body["avatar_url"] == "https://example.com/avatar.png"
        assert body["id"] == str(user.id)

        # Logout revokes the session and clears the cookie -> /me is 401 again.
        logout = await http.post("/auth/google/logout")
        assert logout.status_code == 204

        after = await http.get("/me")
        assert after.status_code == 401
