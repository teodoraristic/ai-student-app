"""Ensure slot_duration_minutes exists (idempotent repair after 007).

Revision ID: 008
Revises: 007
Create Date: 2026-04-24

If revision 007 was recorded but add_column failed (e.g. duplicate column on some
environments), consultation_windows / extra_slots can be missing this column while
the ORM expects it — causing 500s on endpoints that load ConsultationWindow.
This migration only adds the column when absent, then normalizes values.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    cw_cols = _column_names(bind, "consultation_windows")
    if "slot_duration_minutes" not in cw_cols:
        op.add_column(
            "consultation_windows",
            sa.Column("slot_duration_minutes", sa.Integer(), nullable=False, server_default="15"),
        )

    es_cols = _column_names(bind, "extra_slots")
    if "slot_duration_minutes" not in es_cols:
        op.add_column(
            "extra_slots",
            sa.Column("slot_duration_minutes", sa.Integer(), nullable=False, server_default="15"),
        )

    op.execute("""
        UPDATE consultation_windows
        SET slot_duration_minutes = CASE
            WHEN type = 'THESIS' THEN 60
            ELSE 15
        END
    """)

    op.execute("""
        UPDATE extra_slots
        SET slot_duration_minutes = CASE
            WHEN type = 'THESIS' THEN 60
            ELSE 15
        END
    """)


def downgrade() -> None:
    """No-op: repair migration; reversing would not restore prior partial-failure states."""
    pass
