"""Allow NULL course_id on consultation_sessions (thesis slots).

Revision ID: 009
Revises: 008
Create Date: 2026-04-24

The ORM already maps course_id as optional; revision 002 made it nullable but some
databases may still have NOT NULL. Thesis booking creates sessions without a course
in chat context — align PostgreSQL with the model.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "consultation_sessions",
        "course_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "consultation_sessions",
        "course_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
