"""Resume artifacts (design doc §6).

We keep only the extracted .txt in R2, never the original PDF/DOCX — the binary is
deleted right after text extraction (§11). This row records where that .txt lives
and the sha256 of the original upload (for dedupe / re-upload detection).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    r2_key_text: Mapped[str] = mapped_column(String, nullable=False)  # R2 key of the .txt
    file_hash: Mapped[str] = mapped_column(String, nullable=False)  # sha256 of the original
    # The uploaded filename, shown as the dashboard's "last updated from" (F4/F5).
    filename: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
