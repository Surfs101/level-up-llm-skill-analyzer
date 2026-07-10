"""Course catalogue models (design doc §6).

Three tables, one row-type each:
  - Course           one scraped course (platform + external_id is its identity)
  - CourseSkill      which canonical skills a course teaches (precision-mapped)
  - CourseEmbedding  the course's 1536-dim vector for RAG retrieval

The HNSW index on CourseEmbedding.embedding is NOT declared here: pgvector's index
options aren't something Alembic autogenerate understands, so it is created by hand
in the migration instead.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_courses_platform_external_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String, nullable=False)  # e.g. 'deeplearning_ai'
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    duration_hours: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    # beginner | intermediate | advanced
    level: Mapped[str | None] = mapped_column(String, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CourseSkill(Base):
    __tablename__ = "course_skills"
    __table_args__ = (Index("idx_course_skills_skill", "skill_id"),)

    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    # A canonical taxonomy slug, e.g. 'python'. The taxonomy lives in skills.json,
    # not Postgres this phase, so this is a plain string — deliberately NOT a FK to
    # a skills table.
    skill_id: Mapped[str] = mapped_column(String, primary_key=True)


class CourseEmbedding(Base):
    __tablename__ = "course_embeddings"

    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    embedded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
