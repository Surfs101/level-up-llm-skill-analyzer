"""Route tests for POST /analyze and GET /runs/{id} — signed-in AND guest.

Needs Postgres (real Resume/Run rows for the authed path); Redis is faked and the Arq
enqueue is a fake pool that records the job. OpenAI/the worker are never touched —
/analyze only creates the run record and enqueues. Guests get a Redis record, no DB rows.
"""

import uuid
from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.sessions import create_session
from app.config import get_settings
from app.deps import get_db, get_redis
from app.guest_runs import create_guest_run, read_guest_run, save_guest_plan
from app.main import create_app
from app.models import Run, User
from app.workers.queue import get_arq_pool

SUB_PREFIX = "analyze-test-"


def app_with_overrides(maker, fake_redis, pool):  # type: ignore[no-untyped-def]
    app = create_app()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_arq_pool] = lambda: pool
    return app


class FakeArqPool:
    def __init__(self) -> None:
        self.jobs: list[tuple] = []

    async def enqueue_job(self, name: str, *args: object) -> None:
        self.jobs.append((name, args))


@pytest.fixture
async def sessionmaker_() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    try:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Postgres not reachable, skipping analyze test: {exc}")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    async with maker() as session:
        await session.execute(delete(User).where(User.google_sub.startswith(SUB_PREFIX)))
        await session.commit()
    await engine.dispose()


@pytest.fixture
def fake_redis() -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


async def make_user(session: AsyncSession, suffix: str) -> User:
    user = User(google_sub=SUB_PREFIX + suffix, email=f"{suffix}@example.com")
    session.add(user)
    await session.commit()
    return user


async def signed_in_client(maker, fake_redis, user, pool) -> AsyncClient:  # type: ignore[no-untyped-def]
    app = app_with_overrides(maker, fake_redis, pool)
    session_id = await create_session(fake_redis, user.id, get_settings().session_ttl_seconds)
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    client.cookies.set(get_settings().session_cookie_name, session_id)
    return client


def guest_client(maker, fake_redis, pool) -> AsyncClient:  # type: ignore[no-untyped-def]
    """An httpx client with NO session cookie — i.e. a guest."""
    app = app_with_overrides(maker, fake_redis, pool)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_analyze_creates_a_run_and_enqueues(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        user = await make_user(session, "enqueue")
    pool = FakeArqPool()

    async with await signed_in_client(sessionmaker_, fake_redis, user, pool) as client:
        response = await client.post(
            "/analyze",
            data={"jd_text": "Python and Docker role"},
            files={"resume": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )

    assert response.status_code == 202
    run_id = response.json()["run_id"]

    # A queued Run row exists for this user.
    async with sessionmaker_() as session:
        run = await session.get(Run, uuid.UUID(run_id))
        assert run is not None
        assert run.user_id == user.id
        assert run.status == "queued"

    # The pipeline job was enqueued with the run id.
    assert len(pool.jobs) == 1
    name, args = pool.jobs[0]
    assert name == "run_pipeline_one"
    assert args[0] == run_id


async def test_analyze_without_session_creates_a_guest_run(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    pool = FakeArqPool()

    async with guest_client(sessionmaker_, fake_redis, pool) as client:
        response = await client.post(
            "/analyze",
            data={"jd_text": "role"},
            files={"resume": ("r.pdf", b"%PDF-1.4", "application/pdf")},
        )

    assert response.status_code == 202  # not 401 — guests are welcome
    run_id = response.json()["run_id"]

    # No DB run row was created; the run lives only in Redis.
    async with sessionmaker_() as session:
        assert await session.get(Run, uuid.UUID(run_id)) is None
    guest_record = await read_guest_run(fake_redis, uuid.UUID(run_id))
    assert guest_record is not None and guest_record["status"] == "queued"

    # The job was enqueued with is_guest=True (the 5th positional arg).
    name, args = pool.jobs[0]
    assert name == "run_pipeline_one"
    assert args[0] == run_id
    assert args[4] is True


async def test_get_run_returns_a_completed_guest_plan(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    run_id = uuid.uuid4()
    await create_guest_run(fake_redis, run_id, "jd")
    await save_guest_plan(
        fake_redis,
        run_id,
        {
            "id": str(uuid.uuid4()),
            "jd_text": "jd",
            "created_at": "2026-07-07",
            "fit_score": 42,
            "matched_skills": [{"id": "python", "display_name": "Python", "category": "language"}],
            "missing_skills": [],
            "courses": [],
            "project_one_md": "p1",
            "project_two_md": "p2",
        },
    )

    async with guest_client(sessionmaker_, fake_redis, FakeArqPool()) as client:
        response = await client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["plan_id"] is None
    assert body["plan"]["fit_score"] == 42
    assert body["plan"]["matched_skills"][0]["id"] == "python"


async def test_get_run_unknown_id_is_404(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with guest_client(sessionmaker_, fake_redis, FakeArqPool()) as client:
        response = await client.get(f"/runs/{uuid.uuid4()}")
    assert response.status_code == 404  # not a DB run, not a guest record → gone/expired


async def test_get_run_returns_status_and_ui_stage(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        user = await make_user(session, "poll")
        run = Run(user_id=user.id, status="running", current_stage=4)  # gap analysis
        session.add(run)
        await session.commit()
        run_id = run.id

    async with await signed_in_client(sessionmaker_, fake_redis, user, FakeArqPool()) as client:
        response = await client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["current_stage"] == 4
    assert body["ui_stage"] == 3  # step 4 -> "Finding the gap" (index 3)


async def test_get_run_is_scoped_to_the_owner(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        owner = await make_user(session, "owner")
        other = await make_user(session, "other")
        run = Run(user_id=owner.id, status="queued")
        session.add(run)
        await session.commit()
        run_id = run.id

    # `other` must not see `owner`'s run — 404, not 403.
    async with await signed_in_client(sessionmaker_, fake_redis, other, FakeArqPool()) as client:
        response = await client.get(f"/runs/{run_id}")

    assert response.status_code == 404
