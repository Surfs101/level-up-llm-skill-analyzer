"""resumes, runs, plans

Revision ID: c3d5e7f9a1b2
Revises: b2f4a1c7d3e8
Create Date: 2026-07-07

Pipeline 1's persistence: the resume artifact, the run lifecycle record, and the
immutable plan snapshot (design §6). Chained onto the auth migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d5e7f9a1b2"
down_revision: str | None = "b2f4a1c7d3e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("r2_key_text", sa.String(), nullable=False),
        sa.Column("file_hash", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_stage", sa.SmallInteger(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("jd_text", sa.String(), nullable=False),
        sa.Column("resume_text_snapshot", sa.String(), nullable=False),
        sa.Column("matched_skill_ids", postgresql.JSONB(), nullable=False),
        sa.Column("missing_skill_ids", postgresql.JSONB(), nullable=False),
        sa.Column("fit_score", sa.SmallInteger(), nullable=False),
        sa.Column("course_a_id", sa.Uuid(), nullable=True),
        sa.Column("course_b_id", sa.Uuid(), nullable=True),
        sa.Column("course_a_covered", postgresql.JSONB(), nullable=False),
        sa.Column("course_b_covered", postgresql.JSONB(), nullable=False),
        sa.Column("project_one_md", sa.String(), nullable=False),
        sa.Column("project_two_md", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["course_a_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["course_b_id"], ["courses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_plans_user_created", "plans", ["user_id", sa.text("created_at DESC")], unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_plans_user_created", table_name="plans")
    op.drop_table("plans")
    op.drop_table("runs")
    op.drop_table("resumes")
