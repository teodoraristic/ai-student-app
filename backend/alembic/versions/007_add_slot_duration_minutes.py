"""Add slot_duration_minutes to consultation windows and extra slots.

Revision ID: 007
Revises: 006
Create Date: 2026-04-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
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

    # Backfill / align: thesis windows and thesis-type extra slots use 60 minutes
    op.execute("""
        UPDATE consultation_windows
        SET slot_duration_minutes = CASE
            WHEN type = 'thesis' THEN 60
            ELSE 15
        END
    """)

    op.execute("""
        UPDATE extra_slots
        SET slot_duration_minutes = CASE
            WHEN type = 'thesis' THEN 60
            ELSE 15
        END
    """)


def downgrade() -> None:
    bind = op.get_bind()
    es_cols = _column_names(bind, "extra_slots")
    if "slot_duration_minutes" in es_cols:
        op.drop_column("extra_slots", "slot_duration_minutes")
    cw_cols = _column_names(bind, "consultation_windows")
    if "slot_duration_minutes" in cw_cols:
        op.drop_column("consultation_windows", "slot_duration_minutes")
