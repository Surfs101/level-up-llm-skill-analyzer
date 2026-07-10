"""Route tests for GET/PATCH /dashboard, scoped to the signed-in user.

Needs Postgres (real user_skills rows); skips cleanly when it isn't reachable, like
the other integration tests. Redis is faked, and get_current_user resolves the
session the same way it does in production — we just seed the session directly.
"""

from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.sessions import create_session
from app.common.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME
from app.config import get_settings
from app.deps import get_db, get_redis
from app.main import create_app
from app.models import Resume, Skill, User, UserSkill

# All test users share this google_sub prefix so teardown can purge them.
SUB_PREFIX = "dash-test-"

# (id, display_name, category, priority_rank) — real taxonomy ids, upserted so the
# test is self-contained even on a fresh skills table.
SEED_SKILLS = [
    ("python", "Python", "language", 1),
    ("typescript", "TypeScript", "language", 1),
    ("react", "React", "framework", 2),
    ("postgresql", "PostgreSQL", "database", 3),
    ("docker", "Docker", "devops", 3),
]


@pytest.fixture
async def sessionmaker_() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """A NullPool session factory with skills seeded, or skip if Postgres is down."""
    try:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # missing config or unreachable DB — not a failure
        pytest.skip(f"Postgres not reachable, skipping dashboard test: {exc}")

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        for skill_id, display_name, category, rank in SEED_SKILLS:
            await session.execute(
                pg_insert(Skill)
                .values(
                    id=skill_id, display_name=display_name, category=category, priority_rank=rank
                )
                .on_conflict_do_nothing(index_elements=["id"])
            )
        await session.commit()

    yield maker

    # Purge test users (user_skills cascade with them). Seeded skills are canonical
    # and shared, so we leave them.
    async with maker() as session:
        await session.execute(delete(User).where(User.google_sub.startswith(SUB_PREFIX)))
        await session.commit()
    await engine.dispose()


@pytest.fixture
def fake_redis() -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


async def make_user(session: AsyncSession, suffix: str, skills: list[tuple[str, str]]) -> User:
    """Create a user and their user_skills. `skills` is (skill_id, source) pairs."""
    user = User(google_sub=SUB_PREFIX + suffix, email=f"{suffix}@example.com", name=suffix)
    session.add(user)
    await session.flush()
    for skill_id, source in skills:
        session.add(UserSkill(user_id=user.id, skill_id=skill_id, source=source))
    await session.commit()
    return user


async def signed_in_client(
    app_maker: async_sessionmaker[AsyncSession],
    fake_redis: fakeredis.aioredis.FakeRedis,
    user: User,
) -> AsyncClient:
    """An httpx client carrying a valid session cookie for `user`."""
    app = create_app()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with app_maker() as session:
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


async def test_get_dashboard_groups_by_category(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        user = await make_user(
            session,
            "get",
            [("python", "extracted"), ("typescript", "manual"), ("react", "manual")],
        )

    async with await signed_in_client(sessionmaker_, fake_redis, user) as client:
        response = await client.get("/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"last_updated_from", "last_updated_at", "skills_by_category"}
    assert body["skills_by_category"] == {
        "language": ["python", "typescript"],  # sorted; source-agnostic
        "framework": ["react"],
    }
    assert body["last_updated_at"] is not None  # yyyy-mm-dd of the latest change


async def test_last_updated_from_reflects_the_latest_resume(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        user = await make_user(session, "resumed", [("python", "extracted")])
        session.add(
            Resume(
                user_id=user.id,
                r2_key_text="resumes/x.txt",
                file_hash="x",
                filename="resume-2026.pdf",
            )
        )
        await session.commit()

    async with await signed_in_client(sessionmaker_, fake_redis, user) as client:
        body = (await client.get("/dashboard")).json()

    assert body["last_updated_from"] == "resume-2026.pdf"  # no longer null (F4/F5)
    assert body["last_updated_at"] is not None


async def test_patch_add_and_remove_manual_skills(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        user = await make_user(session, "patch", [])

    async with await signed_in_client(sessionmaker_, fake_redis, user) as client:
        added = await client.patch("/dashboard", json={"add": ["postgresql", "docker"]})
        assert added.status_code == 200
        assert added.json()["skills_by_category"] == {
            "database": ["postgresql"],
            "devops": ["docker"],
        }

        removed = await client.patch("/dashboard", json={"remove": ["postgresql"]})
        assert removed.status_code == 200
        assert removed.json()["skills_by_category"] == {"devops": ["docker"]}


async def test_patch_unknown_skill_id_is_rejected(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        user = await make_user(session, "unknown", [])

    async with await signed_in_client(sessionmaker_, fake_redis, user) as client:
        response = await client.patch("/dashboard", json={"add": ["not-a-real-skill"]})

    assert response.status_code == 422


async def test_patch_remove_leaves_extracted_skills(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        user = await make_user(session, "extracted", [("python", "extracted")])

    async with await signed_in_client(sessionmaker_, fake_redis, user) as client:
        response = await client.patch("/dashboard", json={"remove": ["python"]})

    # Extracted skills aren't manual, so the remove is a no-op — python stays.
    assert response.json()["skills_by_category"] == {"language": ["python"]}


async def test_users_cannot_see_or_change_each_others_skills(sessionmaker_, fake_redis) -> None:  # type: ignore[no-untyped-def]
    async with sessionmaker_() as session:
        alice = await make_user(session, "alice", [("react", "manual")])
        bob = await make_user(session, "bob", [("docker", "manual")])

    async with await signed_in_client(sessionmaker_, fake_redis, alice) as client:
        # Alice sees only her own skills.
        body = (await client.get("/dashboard")).json()
        assert body["skills_by_category"] == {"framework": ["react"]}

        # Alice trying to remove Bob's skill id changes nothing for Bob.
        await client.patch("/dashboard", json={"remove": ["docker"]})

    async with sessionmaker_() as session:
        bobs = (await session.scalars(select(UserSkill).where(UserSkill.user_id == bob.id))).all()
    assert {row.skill_id for row in bobs} == {"docker"}
