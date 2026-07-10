"""Jobs route — ranked job matches for the current user. HTTP only.

Postings aren't owned by anyone; the *ranking* is per-user: `GET /jobs` scores every
recent posting by how many of its skills the signed-in user has (design §9, F6), so
two users with different skill sets get different orderings. Everything is bounded to
the 21-day freshness window the jobs cron maintains.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models import JobPosting, JobSkill, User, UserSkill
from app.schemas.jobs import JobMatch, skill_refs

router = APIRouter(tags=["jobs"])

RECENT_DAYS = 21


@router.get("/jobs", response_model=list[JobMatch])
async def list_jobs(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[JobMatch]:
    user_skill_ids = set(
        (await db.scalars(select(UserSkill.skill_id).where(UserSkill.user_id == user.id))).all()
    )

    # §9 ranking: overlap = job_skills whose skill_id the user has, most overlap first,
    # ties broken by freshest posting. LEFT JOIN so a skill-less posting still ranks (0).
    cutoff = datetime.now(UTC) - timedelta(days=RECENT_DAYS)
    overlap = (
        func.count(JobSkill.skill_id)
        .filter(JobSkill.skill_id.in_(list(user_skill_ids)))
        .label("overlap")
    )
    statement = (
        select(JobPosting, overlap)
        .outerjoin(JobSkill, JobSkill.job_id == JobPosting.id)
        .where(JobPosting.posted_at > cutoff)
        .group_by(JobPosting.id)
        .order_by(overlap.desc(), JobPosting.posted_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(statement)).all()

    skills_by_job = await _load_job_skills(db, [job.id for job, _ in rows])
    return [
        _to_match(job, overlap_count, skills_by_job.get(job.id, set()), user_skill_ids)
        for job, overlap_count in rows
    ]


async def _load_job_skills(db: AsyncSession, job_ids: list[uuid.UUID]) -> dict[uuid.UUID, set[str]]:
    if not job_ids:
        return {}
    rows = await db.execute(
        select(JobSkill.job_id, JobSkill.skill_id).where(JobSkill.job_id.in_(job_ids))
    )
    skills_by_job: dict[uuid.UUID, set[str]] = {}
    for job_id, skill_id in rows:
        skills_by_job.setdefault(job_id, set()).add(skill_id)
    return skills_by_job


def _to_match(
    job: JobPosting, overlap: int, job_skill_ids: set[str], user_skill_ids: set[str]
) -> JobMatch:
    matched = sorted(job_skill_ids & user_skill_ids)
    missing = sorted(job_skill_ids - user_skill_ids)
    return JobMatch(
        id=job.id,
        company=job.company,
        title=job.title,
        location=job.location,
        url=job.url,
        posted_at=job.posted_at.date().isoformat(),
        overlap=overlap,
        matched_skills=skill_refs(matched),
        missing_skills=skill_refs(missing),
    )
