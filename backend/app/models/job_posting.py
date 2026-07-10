"""Greenhouse job postings (design doc §6, §9).

Populated by Pipeline 2 (the 6-hour jobs cron): one row per open posting, plus the
canonical skills it mentions. `GET /jobs` ranks postings by how many of the user's
skills overlap `job_skills`, so the skill ids here are the SAME taxonomy slugs the
matcher produces for resumes and JDs — symmetric extraction is what makes the overlap
score meaningful.

  - JobPosting   one posting; (company, gh_job_id) is its natural identity
  - JobSkill     a canonical skill a posting mentions (a real FK to skills)
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid, desc, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class JobPosting(Base):
    __tablename__ = "job_postings"
    __table_args__ = (
        UniqueConstraint("company", "gh_job_id", name="uq_job_postings_company_gh_job_id"),
        Index("idx_jobs_posted_at", desc("posted_at")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company: Mapped[str] = mapped_column(String, nullable=False)  # Greenhouse board slug
    gh_job_id: Mapped[str] = mapped_column(String, nullable=False)  # Greenhouse's job id
    title: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    jd_text: Mapped[str] = mapped_column(String, nullable=False)  # HTML-stripped posting text
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class JobSkill(Base):
    __tablename__ = "job_skills"
    __table_args__ = (Index("idx_job_skills_skill", "skill_id"),)

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("job_postings.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[str] = mapped_column(String, ForeignKey("skills.id"), primary_key=True)
