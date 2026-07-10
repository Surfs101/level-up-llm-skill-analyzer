"""Step 04 (upsert) — writes postings + skills; re-upsert refreshes, no duplicates.

Needs Postgres (skip-if-no-DB via the db_sessionmaker fixture)."""

import importlib

from sqlalchemy import select

from app.models import JobPosting, JobSkill
from app.pipeline_two.state import JobsRefreshState

upsert_step = importlib.import_module("app.pipeline_two.04_upsert")


async def test_upsert_writes_posting_and_skills(
    db_sessionmaker, ensure_skill, make_posting, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    await ensure_skill("python")
    await ensure_skill("fastapi")
    monkeypatch.setattr(upsert_step, "get_sessionmaker", lambda: db_sessionmaker)

    posting = make_posting(company="test-up", gh_job_id="1", content="<p>Python FastAPI</p>")
    state = JobsRefreshState(
        companies=["test-up"],
        filtered=[posting],
        skills_by_job={"test-up/1": ["python", "fastapi"]},
    )

    new_state = await upsert_step.run(state)

    assert new_state.upserted_count == 1
    async with db_sessionmaker() as session:
        job = (
            await session.scalars(select(JobPosting).where(JobPosting.company == "test-up"))
        ).one()
        assert job.jd_text == "Python FastAPI"  # HTML stripped
        skills = (await session.scalars(select(JobSkill).where(JobSkill.job_id == job.id))).all()
        assert {row.skill_id for row in skills} == {"python", "fastapi"}


async def test_reupsert_refreshes_row_and_replaces_skills(
    db_sessionmaker, ensure_skill, make_posting, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    await ensure_skill("python")
    await ensure_skill("docker")
    monkeypatch.setattr(upsert_step, "get_sessionmaker", lambda: db_sessionmaker)

    first = make_posting(
        company="test-up2", gh_job_id="9", title="Old Title", content="<p>Python</p>"
    )
    await upsert_step.run(
        JobsRefreshState(
            companies=["x"], filtered=[first], skills_by_job={"test-up2/9": ["python"]}
        )
    )
    second = make_posting(
        company="test-up2", gh_job_id="9", title="New Title", content="<p>Docker</p>"
    )
    await upsert_step.run(
        JobsRefreshState(
            companies=["x"], filtered=[second], skills_by_job={"test-up2/9": ["docker"]}
        )
    )

    async with db_sessionmaker() as session:
        jobs = (
            await session.scalars(select(JobPosting).where(JobPosting.company == "test-up2"))
        ).all()
        assert len(jobs) == 1  # upsert on (company, gh_job_id), not a duplicate
        assert jobs[0].title == "New Title"
        skills = (
            await session.scalars(select(JobSkill).where(JobSkill.job_id == jobs[0].id))
        ).all()
        assert {row.skill_id for row in skills} == {"docker"}  # fully replaced
