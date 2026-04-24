"""Add hall to professor profile.

Revision ID: 004
Revises: 003
Create Date: 2026-04-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("professor_profiles", sa.Column("hall", sa.String(length=255), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("professor_profiles", "hall")