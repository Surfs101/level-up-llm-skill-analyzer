"""courses, course_skills, course_embeddings

Revision ID: 1cea5f98e020
Revises:
Create Date: 2026-06-10 04:18:32.680890

Hand-edits on top of autogenerate (which can't infer either):
  - CREATE EXTENSION vector before the embedding column is created.
  - the HNSW index on course_embeddings.embedding (vector_cosine_ops).
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1cea5f98e020"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pgvector's vector type must exist before any column uses it.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("duration_hours", sa.Numeric(), nullable=True),
        sa.Column("level", sa.String(), nullable=True),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform", "external_id", name="uq_courses_platform_external_id"),
    )
    op.create_table(
        "course_embeddings",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(1536), nullable=False),
        sa.Column(
            "embedded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("course_id"),
    )
    op.create_table(
        "course_skills",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("course_id", "skill_id"),
    )
    op.create_index("idx_course_skills_skill", "course_skills", ["skill_id"], unique=False)

    # HNSW index for sub-50ms cosine retrieval (autogenerate can't express this).
    op.execute(
        "CREATE INDEX idx_course_embeddings_hnsw "
        "ON course_embeddings USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_course_embeddings_hnsw")
    op.drop_index("idx_course_skills_skill", table_name="course_skills")
    op.drop_table("course_skills")
    op.drop_table("course_embeddings")
    op.drop_table("courses")
    op.execute("DROP EXTENSION IF EXISTS vector")
