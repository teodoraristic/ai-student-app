"""Partial unique index for active bookings; one feedback per booking."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.alembic_migration_utils import has_unique_constraint

revision: str = "013_booking_feedback_constraints"
down_revision: Union[str, None] = "012_exam_schedule"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    op.create_index(
        "uq_bookings_student_session_active",
        "bookings",
        ["student_id", "session_id"],
        unique=True,
        sqlite_where=sa.text("status = 'ACTIVE'"),
        postgresql_where=sa.text("status = 'ACTIVE'"),
        if_not_exists=True,
    )
    if not has_unique_constraint(bind, "feedbacks", "uq_feedbacks_booking_id"):
        op.create_unique_constraint("uq_feedbacks_booking_id", "feedbacks", ["booking_id"])


def downgrade() -> None:
    op.drop_constraint("uq_feedbacks_booking_id", "feedbacks", type_="unique")
    op.drop_index("uq_bookings_student_session_active", table_name="bookings")
