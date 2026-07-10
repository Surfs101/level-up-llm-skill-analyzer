"""Health routes — /healthz and /readyz reflect dependency health (checks mocked)."""

from httpx import ASGITransport, AsyncClient

import app.api.health as health_api
from app.main import create_app


async def _true() -> bool:
    return True


async def _false() -> bool:
    return False


def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test")


async def test_healthz_ok_when_postgres_and_redis_are_up(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(health_api, "check_postgres", _true)
    monkeypatch.setattr(health_api, "check_redis", _true)

    async with client() as http:
        response = await http.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "postgres": True, "redis": True}


async def test_healthz_503_when_a_dependency_is_down(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(health_api, "check_postgres", _true)
    monkeypatch.setattr(health_api, "check_redis", _false)

    async with client() as http:
        response = await http.get("/healthz")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"


async def test_readyz_ok_when_all_checks_pass(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(health_api, "check_postgres", _true)
    monkeypatch.setattr(health_api, "check_redis", _true)
    monkeypatch.setattr(health_api, "check_taxonomy", lambda: True)
    monkeypatch.setattr(health_api, "check_openai", _true)

    async with client() as http:
        response = await http.get("/readyz")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


async def test_readyz_503_when_openai_unauthenticated(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(health_api, "check_postgres", _true)
    monkeypatch.setattr(health_api, "check_redis", _true)
    monkeypatch.setattr(health_api, "check_taxonomy", lambda: True)
    monkeypatch.setattr(health_api, "check_openai", _false)

    async with client() as http:
        response = await http.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["openai"] is False
