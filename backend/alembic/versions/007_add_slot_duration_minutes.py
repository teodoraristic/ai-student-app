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


def upgrade() -> None:
    # Add slot_duration_minutes column to consultation_windows with default 15
    op.add_column(
        "consultation_windows",
        sa.Column("slot_duration_minutes", sa.Integer(), nullable=False, server_default="15"),
    )
    
    # Add slot_duration_minutes column to extra_slots with default 15
    op.add_column(
        "extra_slots",
        sa.Column("slot_duration_minutes", sa.Integer(), nullable=False, server_default="15"),
    )
    
    # Backfill existing data: thesis windows should be 60, regular should be 15
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
    op.drop_column("extra_slots", "slot_duration_minutes")
    op.drop_column("consultation_windows", "slot_duration_minutes")
