"""Remove is_urgent from bookings (feature removed)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.alembic_migration_utils import has_column

revision: str = "016_drop_booking_is_urgent"
down_revision: Union[str, None] = "015_user_study_year"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if not has_column(bind, "bookings", "is_urgent"):
        return
    op.drop_column("bookings", "is_urgent")


def downgrade() -> None:
    bind = op.get_bind()
    if has_column(bind, "bookings", "is_urgent"):
        return
    op.add_column(
        "bookings",
        sa.Column("is_urgent", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("bookings", "is_urgent", server_default=None)
