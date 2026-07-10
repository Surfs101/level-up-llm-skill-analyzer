"""Pipeline 2 end-to-end: fetch → filter → extract → upsert → purge.

Greenhouse is mocked (fixture postings) and Postgres is real (skip-if-no-DB). Asserts
that only recent US/Canada postings land in job_postings with their skills, and that
the purge step drops a pre-seeded stale row.
"""

import importlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import NullPool, delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.greenhouse.client import GreenhousePosting
from app.models import JobPosting, JobSkill, Skill
from app.nlp.taxonomy import get_skill_by_id
from app.pipeline_two import run_refresh
from app.pipeline_two.state import JobsRefreshState


def build_posting(
    gh_job_id: str, *, location: str | None, content: str, updated_at: datetime
) -> GreenhousePosting:
    return GreenhousePosting(
        company="test-e2e",
        gh_job_id=gh_job_id,
        title="Backend Engineer",
        location=location,
        url=f"https://boards.greenhouse.io/test-e2e/jobs/{gh_job_id}",
        content=content,
        updated_at=updated_at,
    )


fetch_logic = importlib.import_module("app.pipeline_two.01_fetch_boards.logic")
upsert_step = importlib.import_module("app.pipeline_two.04_upsert")
purge_step = importlib.import_module("app.pipeline_two.05_purge_old")

NOW = datetime.now(UTC)


@pytest.fixture
async def sessionmaker_() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    try:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Postgres not reachable, skipping jobs e2e: {exc}")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    async with maker() as session:
        await session.execute(delete(JobPosting).where(JobPosting.company.startswith("test-e2e")))
        await session.commit()
    await engine.dispose()


async def _seed_skill(maker, skill_id: str) -> None:  # type: ignore[no-untyped-def]
    skill = get_skill_by_id(skill_id)
    assert skill is not None
    async with maker() as session:
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


async def test_full_refresh_writes_recent_us_postings_and_purges_stale(
    sessionmaker_, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    await _seed_skill(sessionmaker_, "python")
    await _seed_skill(sessionmaker_, "fastapi")

    # A stale row already in the table — the purge step should drop it.
    async with sessionmaker_() as session:
        session.add(
            JobPosting(
                company="test-e2e-stale",
                gh_job_id="s",
                title="t",
                url="u",
                jd_text="x",
                posted_at=NOW - timedelta(days=40),
            )
        )
        await session.commit()

    keep = build_posting(
        "1",
        location="Remote - US",
        content="<p>Python and FastAPI</p>",
        updated_at=NOW - timedelta(days=2),
    )
    foreign = build_posting(
        "2",
        location="London, United Kingdom",
        content="<p>Python</p>",
        updated_at=NOW,
    )
    stale = build_posting(
        "3",
        location="Remote - US",
        content="<p>Python</p>",
        updated_at=NOW - timedelta(days=30),
    )

    async def fake_fetch_boards(_companies: list[str]) -> list:  # type: ignore[type-arg]
        return [keep, foreign, stale]

    monkeypatch.setattr(fetch_logic, "fetch_boards", fake_fetch_boards)
    monkeypatch.setattr(upsert_step, "get_sessionmaker", lambda: sessionmaker_)
    monkeypatch.setattr(purge_step, "get_sessionmaker", lambda: sessionmaker_)

    final = await run_refresh(JobsRefreshState(companies=["test-e2e"]))

    # Only the recent US posting was kept and upserted.
    assert final.upserted_count == 1
    async with sessionmaker_() as session:
        jobs = (
            await session.scalars(select(JobPosting).where(JobPosting.company == "test-e2e"))
        ).all()
        assert {job.gh_job_id for job in jobs} == {"1"}
        skills = (
            await session.scalars(select(JobSkill).where(JobSkill.job_id == jobs[0].id))
        ).all()
        assert {row.skill_id for row in skills} == {"python", "fastapi"}

        # The pre-seeded stale row was purged.
        stale_left = await session.scalar(
            select(JobPosting).where(JobPosting.company == "test-e2e-stale")
        )
        assert stale_left is None
    assert final.purged_count >= 1
