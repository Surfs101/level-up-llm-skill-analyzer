"""resumes.filename

Revision ID: f6a8b0c2d4e6
Revises: e5f7a9b1c3d4
Create Date: 2026-07-07

The uploaded resume filename, so /dashboard can show "last updated from <file>" (F4/F5).
Nullable — older resume rows predate it.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a8b0c2d4e6"
down_revision: str | None = "e5f7a9b1c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("filename", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("resumes", "filename")
