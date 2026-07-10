"""Step 04 logic — persist postings + their skills (design §9 step 4).

Each posting is upserted on its natural key (company, gh_job_id): a new posting is
inserted, an existing one is refreshed. Then that job's job_skills are fully replaced
(delete + re-insert) so the skill set always matches the current posting. jd_text is
the HTML-stripped text (same stripping step 03 used for matching).
"""

import uuid

from sqlalchemy import delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.html import strip_html
from app.greenhouse.client import GreenhousePosting
from app.models import JobPosting, JobSkill

from .schemas import UpsertResult


async def upsert(
    session: AsyncSession,
    postings: list[GreenhousePosting],
    skills_by_job: dict[str, list[str]],
) -> UpsertResult:
    for posting in postings:
        job_id = await _upsert_posting(session, posting)
        await _replace_skills(session, job_id, skills_by_job.get(_job_key(posting), []))
    await session.commit()
    return UpsertResult(upserted_count=len(postings))


def _job_key(posting: GreenhousePosting) -> str:
    return f"{posting.company}/{posting.gh_job_id}"


async def _upsert_posting(session: AsyncSession, posting: GreenhousePosting) -> uuid.UUID:
    insert = pg_insert(JobPosting).values(
        company=posting.company,
        gh_job_id=posting.gh_job_id,
        title=posting.title,
        location=posting.location,
        url=posting.url,
        jd_text=strip_html(posting.content),
        posted_at=posting.updated_at,
    )
    statement = insert.on_conflict_do_update(
        index_elements=["company", "gh_job_id"],
        set_={
            "title": insert.excluded.title,
            "location": insert.excluded.location,
            "url": insert.excluded.url,
            "jd_text": insert.excluded.jd_text,
            "posted_at": insert.excluded.posted_at,
            "ingested_at": func.now(),
        },
    ).returning(JobPosting.id)
    return (await session.execute(statement)).scalar_one()


async def _replace_skills(session: AsyncSession, job_id: uuid.UUID, skill_ids: list[str]) -> None:
    await session.execute(delete(JobSkill).where(JobSkill.job_id == job_id))
    for skill_id in skill_ids:
        session.add(JobSkill(job_id=job_id, skill_id=skill_id))
