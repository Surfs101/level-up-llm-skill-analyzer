"""Immutable plan snapshots (design doc §6).

A plan is a denormalized, frozen record of one completed analysis: the JD and resume
text, the matched/missing skill ids, the fit score, the two recommended courses (and
which gap skills each covers), and the two generated project write-ups. Everything is
copied in, so later edits to the user's skills or the taxonomy can never mutate a
saved plan. The skill-id lists are JSONB arrays of taxonomy slugs.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, SmallInteger, String, Uuid, desc, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (Index("idx_plans_user_created", "user_id", desc("created_at")),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("runs.id"), nullable=False)

    jd_text: Mapped[str] = mapped_column(String, nullable=False)
    resume_text_snapshot: Mapped[str] = mapped_column(String, nullable=False)

    matched_skill_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    missing_skill_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)  # priority-sorted
    fit_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0..100

    # The two recommended courses. Nullable per §6 DDL — a plan can be saved even if
    # the corpus yields fewer than two candidates for a niche gap.
    course_a_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("courses.id"), nullable=True
    )
    course_b_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("courses.id"), nullable=True
    )
    course_a_covered: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    course_b_covered: Mapped[list[str]] = mapped_column(JSONB, nullable=False)

    project_one_md: Mapped[str] = mapped_column(String, nullable=False)
    project_two_md: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
