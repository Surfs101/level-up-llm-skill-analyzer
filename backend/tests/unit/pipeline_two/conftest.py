"""Shared fixtures for the Pipeline 2 step tests.

A GreenhousePosting builder, a Postgres session factory (steps 04–05), and a skill
seeder so job_skills' FK to skills is satisfied. Steps 01–03 are pure and need only
the builder.
"""

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy import NullPool, delete, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.greenhouse.client import GreenhousePosting
from app.models import JobPosting, Skill
from app.nlp.taxonomy import get_skill_by_id

# All test postings use this company prefix so teardown can purge them.
TEST_COMPANY_PREFIX = "test-"


@pytest.fixture
def make_posting() -> Callable[..., GreenhousePosting]:
    def _make(
        company: str = "test-acme",
        gh_job_id: str = "1",
        *,
        title: str = "Backend Engineer",
        location: str | None = "Remote - US",
        content: str = "<p>Python</p>",
        updated_at: datetime | None = None,
    ) -> GreenhousePosting:
        return GreenhousePosting(
            company=company,
            gh_job_id=gh_job_id,
            title=title,
            location=location,
            url=f"https://boards.greenhouse.io/{company}/jobs/{gh_job_id}",
            content=content,
            updated_at=updated_at or datetime(2026, 7, 1, tzinfo=UTC),
        )

    return _make


@pytest.fixture
async def db_sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """A NullPool session factory, or skip if Postgres isn't reachable."""
    try:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # missing config or unreachable DB — not a failure
        pytest.skip(f"Postgres not reachable, skipping DB test: {exc}")

    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker

    # Purge test postings (job_skills cascade with them); leave seeded skills.
    async with maker() as session:
        await session.execute(
            delete(JobPosting).where(JobPosting.company.startswith(TEST_COMPANY_PREFIX))
        )
        await session.commit()
    await engine.dispose()


@pytest.fixture
async def ensure_skill(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> Callable[[str], object]:
    """Insert a real taxonomy skill (idempotent) so job_skills' FK is satisfied."""

    async def _ensure(skill_id: str) -> None:
        skill = get_skill_by_id(skill_id)
        assert skill is not None, f"{skill_id!r} is not a real taxonomy id"
        async with db_sessionmaker() as session:
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
            await session.commit()

    return _ensure
