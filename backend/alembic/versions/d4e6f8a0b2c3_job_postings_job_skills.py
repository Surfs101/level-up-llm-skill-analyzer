"""job_postings, job_skills

Revision ID: d4e6f8a0b2c3
Revises: c3d5e7f9a1b2
Create Date: 2026-07-07

Pipeline 2's persistence: Greenhouse postings and the canonical skills each mentions
(design §6, §9). Chained onto the Pipeline 1 migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e6f8a0b2c3"
down_revision: str | None = "c3d5e7f9a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_postings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("gh_job_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("jd_text", sa.String(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company", "gh_job_id", name="uq_job_postings_company_gh_job_id"),
    )
    op.create_index("idx_jobs_posted_at", "job_postings", [sa.text("posted_at DESC")], unique=False)

    op.create_table(
        "job_skills",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("job_id", "skill_id"),
    )
    op.create_index("idx_job_skills_skill", "job_skills", ["skill_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_job_skills_skill", table_name="job_skills")
    op.drop_table("job_skills")
    op.drop_index("idx_jobs_posted_at", table_name="job_postings")
    op.drop_table("job_postings")
