"""Add any_slot_on_day to waitlists for day-level interest without a session row."""

from alembic import op
import sqlalchemy as sa

from backend.alembic_migration_utils import has_column


revision = "011_waitlist_any_slot"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not has_column(bind, "waitlists", "any_slot_on_day"):
        op.add_column(
            "waitlists",
            sa.Column("any_slot_on_day", sa.Boolean(), nullable=False, server_default="false"),
        )
        op.alter_column("waitlists", "any_slot_on_day", server_default=None)


def downgrade() -> None:
    op.drop_column("waitlists", "any_slot_on_day")
