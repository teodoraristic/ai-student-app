"""Add updated_at to professor_announcements (ORM parity)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.alembic_migration_utils import has_column

revision: str = "014_professor_ann_updated_at"
down_revision: Union[str, None] = "013_booking_feedback_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if has_column(bind, "professor_announcements", "updated_at"):
        return
    op.add_column(
        "professor_announcements",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("professor_announcements", "updated_at")
