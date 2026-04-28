"""Add preferred times to preparation vote.

Revision ID: 006
Revises: 005
Create Date: 2026-04-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.alembic_migration_utils import has_column

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if not has_column(bind, "preparation_votes", "preferred_times"):
        op.add_column("preparation_votes", sa.Column("preferred_times", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("preparation_votes", "preferred_times")