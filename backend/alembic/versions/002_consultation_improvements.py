"""Consultation system improvements.

Revision ID: 002
Revises: 001
Create Date: 2026-04-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_final_year", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("consultation_sessions", sa.Column("announced_by_professor", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("waitlists", sa.Column("session_id", sa.Integer(), sa.ForeignKey("consultation_sessions.id"), nullable=True))
    op.alter_column("waitlists", "window_id", nullable=True)
    op.alter_column("consultation_sessions", "course_id", nullable=True)


def downgrade() -> None:
    op.alter_column("consultation_sessions", "course_id", nullable=False)
    op.alter_column("waitlists", "window_id", nullable=False)
    op.drop_column("waitlists", "session_id")
    op.drop_column("consultation_sessions", "announced_by_professor")
    op.drop_column("users", "is_final_year")
