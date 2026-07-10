"""users, skills, skill_aliases, user_skills

Revision ID: b2f4a1c7d3e8
Revises: 1cea5f98e020
Create Date: 2026-07-07

The shared identity + taxonomy foundation both Phase 3 (auth/dashboard) and Phase 4
(pipeline) build on. skills/skill_aliases mirror data/taxonomy/skills.json (loaded
by scripts/sync_taxonomy_to_db.py); users/user_skills hold the signed-in user and
their dashboard skill set.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2f4a1c7d3e8"
down_revision: str | None = "1cea5f98e020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("google_sub", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_sub", name="uq_users_google_sub"),
    )
    op.create_table(
        "skills",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("priority_rank", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "skill_aliases",
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("skill_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("alias"),
    )
    op.create_table(
        "user_skills",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("user_id", "skill_id"),
    )


def downgrade() -> None:
    op.drop_table("user_skills")
    op.drop_table("skill_aliases")
    op.drop_table("skills")
    op.drop_table("users")
