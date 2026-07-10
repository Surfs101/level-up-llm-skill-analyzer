"""Step 05 (purge old) — deletes postings older than 21 days, keeps recent.

Needs Postgres (skip-if-no-DB)."""

import importlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import JobPosting
from app.pipeline_two.state import JobsRefreshState

purge_step = importlib.import_module("app.pipeline_two.05_purge_old")


async def test_purge_deletes_only_postings_past_the_window(db_sessionmaker, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(purge_step, "get_sessionmaker", lambda: db_sessionmaker)
    now = datetime.now(UTC)

    async with db_sessionmaker() as session:
        session.add_all(
            [
                JobPosting(
                    company="test-purge",
                    gh_job_id="recent",
                    title="t",
                    url="u",
                    jd_text="x",
                    posted_at=now - timedelta(days=1),
                ),
                JobPosting(
                    company="test-purge",
                    gh_job_id="old",
                    title="t",
                    url="u",
                    jd_text="x",
                    posted_at=now - timedelta(days=30),
                ),
            ]
        )
        await session.commit()

    new_state = await purge_step.run(JobsRefreshState(companies=["x"]))

    assert new_state.purged_count >= 1  # counts every stale row in the table
    async with db_sessionmaker() as session:
        remaining = {
            row.gh_job_id
            for row in (
                await session.scalars(select(JobPosting).where(JobPosting.company == "test-purge"))
            ).all()
        }
    assert remaining == {"recent"}  # the 30-day-old one is gone
