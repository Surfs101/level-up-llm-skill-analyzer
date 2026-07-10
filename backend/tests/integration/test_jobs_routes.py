"""Route tests for GET /jobs — overlap ranking, matched/missing, paging, per-user.

Needs Postgres (real job_postings/user_skills); Redis faked. Two users with different
skills must get different rankings (design §9, F6).
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, delete, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.sessions import create_session
from app.config import get_settings
from app.deps import get_db, get_redis
from app.main import create_app
from app.models import JobPosting, JobSkill, Skill, User, UserSkill
from app.nlp.taxonomy import get_skill_by_id

SUB_PREFIX = "jobs-test-"
COMPANY_PREFIX = "jobs-test-"
NOW = datetime.now(UTC)


@pytest.fixture
async def sessionmaker_() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    try:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Postgres not reachable, skipping jobs route test: {exc}")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    async with maker() as session:
        await session.execute(delete(User).where(User.google_sub.startswith(SUB_PREFIX)))
        await session.execute(
            delete(JobPosting).where(JobPosting.company.startswith(COMPANY_PREFIX))
        )
        await session.commit()
    await engine.dispose()


@pytest.fixture
def fake_redis() -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


async def seed_skill(session: AsyncSession, skill_id: str) -> None:
    skill = get_skill_by_id(skill_id)
    assert skill is not None
    await session.execute(
        pg_insert(Skill)
        .values(
            id=skill.id,
            display_name=skill.canonical_name,
            category=skill.category,
            priority_rank=skill.priority_rank,
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )


async def make_user(session: AsyncSession, suffix: str, skill_ids: list[str]) -> User:
    user = User(google_sub=SUB_PREFIX + suffix, email=f"{suffix}@example.com")
    session.add(user)
    await session.flush()
    for skill_id in skill_ids:
        session.add(UserSkill(user_id=user.id, skill_id=skill_id, source="manual"))
    await session.commit()
    return user


async def make_job(
    session: AsyncSession, name: str, skill_ids: list[str], *, days_ago: int = 1
) -> uuid.UUID:
    job = JobPosting(
        company=f"{COMPANY_PREFIX}{name}",
        gh_job_id=name,
        title=f"{name} role",
        location="Remote - US",
        url=f"https://boards.greenhouse.io/x/jobs/{name}",
        jd_text="text",
        posted_at=NOW - timedelta(days=days_ago),
    )
    session.add(job)
    await session.flush()
    for skill_id in skill_ids:
        session.add(JobSkill(job_id=job.id, skill_id=skill_id))
    await session.commit()
    return job.id


async def signed_in_client(maker, fake_redis, user) -> AsyncClient:  # type: ignore[no-untyped-def]
    app = create_app()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    session_id = await create_session(fake_redis, user.id, get_settings().session_ttl_seconds)
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    client.cookies.set(get_settings().session_cookie_name, session_id)
    return client


async def test_ranking_matched_missing_and_per_user_scoping(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        for skill_id in ("python", "fastapi", "react", "typescript", "docker"):
            await seed_skill(session, skill_id)
        await session.commit()

        alice = await make_user(session, "alice", ["python", "fastapi"])
        bob = await make_user(session, "bob", ["react", "typescript"])

        job_py = await make_job(session, "py", ["python", "fastapi"], days_ago=1)
        job_fe = await make_job(session, "fe", ["react", "typescript"], days_ago=1)
        await make_job(session, "ops", ["docker"], days_ago=2)

    # Alice (python/fastapi) ranks the Python job first, with the right matched/missing.
    async with await signed_in_client(sessionmaker_, fake_redis, alice) as client:
        alice_jobs = (await client.get("/jobs")).json()

    assert alice_jobs[0]["id"] == str(job_py)
    assert alice_jobs[0]["overlap"] == 2
    assert {s["id"] for s in alice_jobs[0]["matched_skills"]} == {"python", "fastapi"}
    assert alice_jobs[0]["missing_skills"] == []
    # The frontend chip shape: {id, display_name, category}.
    assert {"id": "python", "display_name": "Python", "category": "language"} in alice_jobs[0][
        "matched_skills"
    ]

    # Bob (react/typescript) ranks the frontend job first instead — different ranking.
    async with await signed_in_client(sessionmaker_, fake_redis, bob) as client:
        bob_jobs = (await client.get("/jobs")).json()

    assert bob_jobs[0]["id"] == str(job_fe)
    assert bob_jobs[0]["overlap"] == 2
    # Bob has none of the Python job's skills — it's all "missing" for him.
    py_for_bob = next(j for j in bob_jobs if j["id"] == str(job_py))
    assert py_for_bob["overlap"] == 0
    assert {s["id"] for s in py_for_bob["missing_skills"]} == {"python", "fastapi"}


async def test_pagination(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        await seed_skill(session, "python")
        await session.commit()
        user = await make_user(session, "pager", ["python"])
        await make_job(session, "a", ["python"], days_ago=1)
        await make_job(session, "b", ["python"], days_ago=2)
        await make_job(session, "c", ["python"], days_ago=3)

    async with await signed_in_client(sessionmaker_, fake_redis, user) as client:
        page1 = (await client.get("/jobs", params={"limit": 2, "offset": 0})).json()
        page2 = (await client.get("/jobs", params={"limit": 2, "offset": 2})).json()

    assert len(page1) == 2
    assert len(page2) == 1
    assert {j["id"] for j in page1}.isdisjoint({j["id"] for j in page2})


async def test_only_recent_jobs_are_returned(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        await seed_skill(session, "python")
        await session.commit()
        user = await make_user(session, "recent", ["python"])
        fresh = await make_job(session, "fresh", ["python"], days_ago=1)
        await make_job(session, "stale", ["python"], days_ago=30)  # outside the 21-day window

    async with await signed_in_client(sessionmaker_, fake_redis, user) as client:
        returned = (await client.get("/jobs")).json()

    ids = {j["id"] for j in returned}
    assert str(fresh) in ids
    assert all("stale" not in j["title"] for j in returned)


async def test_requires_authentication(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    app = create_app()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with sessionmaker_() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/jobs")
    assert response.status_code == 401
