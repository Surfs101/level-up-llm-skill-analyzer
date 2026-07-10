"""Integration check that the Phase-2 course schema is actually in the database.

Needs a reachable Postgres (the docker-compose `db`). CI has no database yet, so
every test here skips cleanly when the engine can't connect — a missing DATABASE_URL
or a down Postgres is a skip, not a failure.
"""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import NullPool, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.config import get_settings
from app.models import Course


@pytest.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """A fresh async engine per test, or skip if Postgres isn't reachable.

    pytest-asyncio gives each test its own event loop, and an asyncpg pool is bound
    to the loop it was created on — so we build a throwaway NullPool engine here
    (same DATABASE_URL the app uses) rather than the shared pooled app engine, and
    dispose it at teardown. A missing config or down database is a skip.
    """
    try:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # missing config or unreachable DB — not a test failure
        pytest.skip(f"Postgres not reachable, skipping schema test: {exc}")
    yield engine
    await engine.dispose()


async def test_core_tables_exist(db_engine: AsyncEngine) -> None:
    tables = (
        "courses",
        "course_skills",
        "course_embeddings",
        "users",
        "skills",
        "skill_aliases",
        "user_skills",
        "resumes",
        "runs",
        "plans",
        "job_postings",
        "job_skills",
    )
    async with db_engine.connect() as conn:
        for table in tables:
            found = await conn.scalar(text("SELECT to_regclass(:name)"), {"name": table})
            assert found is not None, f"table {table!r} is missing"


async def test_vector_extension_installed(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as conn:
        found = await conn.scalar(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
        assert found == "vector"


async def test_hnsw_index_exists(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as conn:
        found = await conn.scalar(
            text("SELECT indexname FROM pg_indexes WHERE indexname = :name"),
            {"name": "idx_course_embeddings_hnsw"},
        )
        assert found == "idx_course_embeddings_hnsw"


async def test_course_insert_select_rolls_back(db_engine: AsyncEngine) -> None:
    external_id = "schema-test-dummy"

    # Insert + read back inside one transaction, then roll it back.
    async with AsyncSession(db_engine) as session:
        course = Course(
            platform="deeplearning_ai",
            external_id=external_id,
            title="Dummy Course",
            url="https://example.com/dummy",
        )
        session.add(course)
        await session.flush()  # sends the INSERT without committing
        fetched = await session.get(Course, course.id)
        assert fetched is not None
        assert fetched.title == "Dummy Course"
        await session.rollback()

    # The rollback must have left nothing behind.
    async with AsyncSession(db_engine) as session:
        leftover = await session.scalar(select(Course).where(Course.external_id == external_id))
        assert leftover is None
