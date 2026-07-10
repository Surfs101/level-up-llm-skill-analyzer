"""Step 05 logic — drop postings older than the window (design §9 step 5).

`DELETE FROM job_postings WHERE posted_at < now - 21 days`. This is the same 21-day
window step 02 filters on, so the table only ever holds recent postings. job_skills
rows go with their posting via ON DELETE CASCADE.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobPosting

from .schemas import PurgeResult

PURGE_AFTER_DAYS = 21


async def purge(session: AsyncSession, now: datetime | None = None) -> PurgeResult:
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=PURGE_AFTER_DAYS)
    result = await session.execute(delete(JobPosting).where(JobPosting.posted_at < cutoff))
    await session.commit()
    return PurgeResult(purged_count=result.rowcount or 0)
