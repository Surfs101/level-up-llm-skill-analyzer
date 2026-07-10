"""Pipeline 1 runs (design doc §6).

A run is the lifecycle record of one analysis for a signed-in user; the frontend
polls it to advance the progress UI. Guests have no row here — their run state
lives in Redis with a short TTL. `current_stage` (1..8) is bumped between steps by
the orchestrator so the poller knows how far along things are.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("resumes.id"), nullable=True
    )
    # queued | running | completed | failed
    status: Mapped[str] = mapped_column(String, nullable=False)
    current_stage: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # 1..8
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
