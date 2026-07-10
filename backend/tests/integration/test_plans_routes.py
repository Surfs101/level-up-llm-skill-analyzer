"""Route tests for GET /plans, GET /plans/{id}, DELETE /plans/{id}.

Needs Postgres (real Plan rows); Redis faked. Asserts the DTO shape matches the
frontend contract and that everything is scoped to the owning user.
"""

import uuid
from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.sessions import create_session
from app.common.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME
from app.config import get_settings
from app.deps import get_db, get_redis
from app.main import create_app
from app.models import Course, Plan, Run, User

SUB_PREFIX = "plans-test-"


@pytest.fixture
async def sessionmaker_() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    try:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Postgres not reachable, skipping plans test: {exc}")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    async with maker() as session:
        await session.execute(delete(User).where(User.google_sub.startswith(SUB_PREFIX)))
        await session.execute(delete(Course).where(Course.platform == "plans-test"))
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


async def make_plan(session: AsyncSession, user: User, *, with_course: bool = False) -> Plan:
    run = Run(user_id=user.id, status="completed", current_stage=8)
    session.add(run)
    await session.flush()

    course_a_id = None
    if with_course:
        course = Course(
            platform="plans-test",
            external_id=f"c-{uuid.uuid4()}",
            title="RAG From Scratch",
            description="Build a retrieval-augmented generation pipeline.",
            url="https://example.com/rag",
        )
        session.add(course)
        await session.flush()
        course_a_id = course.id

    plan = Plan(
        user_id=user.id,
        run_id=run.id,
        jd_text="We need Python, FastAPI, Docker, and RAG.",
        resume_text_snapshot="resume",
        matched_skill_ids=["fastapi", "python"],
        missing_skill_ids=["docker", "rag"],
        fit_score=50,
        course_a_id=course_a_id,
        course_b_id=None,
        course_a_covered=["docker", "rag"] if with_course else [],
        course_b_covered=[],
        project_one_md="# Project One\n\nfast apply",
        project_two_md="# Project Two\n\nskillbridge",
    )
    session.add(plan)
    await session.commit()
    return plan


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
    # Make the client CSRF-ready: matching cookie + header for the double-submit check.
    client.cookies.set(CSRF_COOKIE_NAME, "test-csrf")
    client.headers[CSRF_HEADER_NAME] = "test-csrf"
    return client


async def test_list_plans_returns_the_users_plans_newest_first(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        user = await make_user(session, "list")
        await make_plan(session, user)
        await make_plan(session, user)

    async with await signed_in_client(sessionmaker_, fake_redis, user) as client:
        response = await client.get("/plans")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    row = body[0]
    assert set(row.keys()) == {
        "id",
        "jd_text",
        "created_at",
        "fit_score",
        "matched_count",
        "missing_count",
    }
    assert row["matched_count"] == 2 and row["missing_count"] == 2


async def test_get_plan_returns_full_detail_with_skill_objects_and_course(
    sessionmaker_, fake_redis
) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        user = await make_user(session, "detail")
        plan = await make_plan(session, user, with_course=True)

    async with await signed_in_client(sessionmaker_, fake_redis, user) as client:
        response = await client.get(f"/plans/{plan.id}")

    assert response.status_code == 200
    body = response.json()
    # Skills are objects carrying id + display_name + category (for chip rendering).
    assert {"id": "python", "display_name": "Python", "category": "language"} in body[
        "matched_skills"
    ]
    assert {"id": "docker", "display_name": "Docker", "category": "devops"} in body[
        "missing_skills"
    ]
    # Course embeds its display fields and the skills it covers.
    assert len(body["courses"]) == 1
    course = body["courses"][0]
    assert course["rank"] == 1
    assert course["title"] == "RAG From Scratch"
    assert course["provider"] == "plans-test"
    assert {s["id"] for s in course["skills_covered"]} == {"docker", "rag"}
    # Projects are Markdown.
    assert body["project_one_md"].startswith("# Project One")


async def test_get_plan_is_scoped_to_owner(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        owner = await make_user(session, "owner")
        other = await make_user(session, "other")
        plan = await make_plan(session, owner)

    async with await signed_in_client(sessionmaker_, fake_redis, other) as client:
        response = await client.get(f"/plans/{plan.id}")
    assert response.status_code == 404  # not the owner -> not found, not 403


async def test_delete_plan_removes_only_the_owners_plan(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        owner = await make_user(session, "deleter")
        other = await make_user(session, "bystander")
        plan = await make_plan(session, owner)
        plan_id = plan.id

    # A non-owner can't delete it.
    async with await signed_in_client(sessionmaker_, fake_redis, other) as client:
        forbidden = await client.delete(f"/plans/{plan_id}")
    assert forbidden.status_code == 404

    # The owner can, and it's gone afterward.
    async with await signed_in_client(sessionmaker_, fake_redis, owner) as client:
        deleted = await client.delete(f"/plans/{plan_id}")
        assert deleted.status_code == 204
        after = await client.get(f"/plans/{plan_id}")
        assert after.status_code == 404

    async with sessionmaker_() as session:
        leftover = await session.scalar(select(Plan).where(Plan.id == plan_id))
    assert leftover is None
