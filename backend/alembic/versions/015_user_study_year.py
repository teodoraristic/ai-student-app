"""Add study_year to users (admin-provisioned students)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.alembic_migration_utils import has_column

revision: str = "015_user_study_year"
down_revision: Union[str, None] = "014_professor_ann_updated_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if has_column(bind, "users", "study_year"):
        return
    op.add_column("users", sa.Column("study_year", sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if not has_column(bind, "users", "study_year"):
        return
    op.drop_column("users", "study_year")
