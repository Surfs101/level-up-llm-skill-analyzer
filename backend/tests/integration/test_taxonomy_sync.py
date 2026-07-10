"""Integration check that sync_taxonomy_to_db mirrors skills.json into Postgres.

Needs a reachable Postgres with migrations applied (docker-compose `db` +
`alembic upgrade head`). Like the schema test, a missing DATABASE_URL or a down
database is a skip, not a failure — CI has no DB yet.
"""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import NullPool, func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.config import get_settings
from app.models import Skill, SkillAlias
from app.nlp.taxonomy import get_all_skills
from scripts.sync_taxonomy_to_db import sync


@pytest.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """A fresh NullPool engine per test, or skip if Postgres isn't reachable."""
    try:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # missing config or unreachable DB — not a test failure
        pytest.skip(f"Postgres not reachable, skipping sync test: {exc}")
    yield engine
    await engine.dispose()


async def test_sync_loads_every_skill_and_alias_and_is_idempotent(db_engine: AsyncEngine) -> None:
    skills = get_all_skills()
    expected_skills = len(skills)
    expected_aliases = sum(len(skill.aliases) for skill in skills)

    # Sync twice in one transaction: the second run must not add or duplicate rows.
    # Roll back at the end so the test leaves the database untouched.
    async with AsyncSession(db_engine) as session:
        await sync(session)
        await sync(session)
        await session.flush()

        skill_count = await session.scalar(select(func.count()).select_from(Skill))
        alias_count = await session.scalar(select(func.count()).select_from(SkillAlias))

        assert skill_count == expected_skills
        assert alias_count == expected_aliases

        await session.rollback()
