"""Track approved thesis professor on the student.

Revision ID: 003
Revises: 002
Create Date: 2026-04-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("thesis_professor_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_thesis_professor_id_users",
        "users",
        "users",
        ["thesis_professor_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_thesis_professor_id_users", "users", type_="foreignkey")
    op.drop_column("users", "thesis_professor_id")
