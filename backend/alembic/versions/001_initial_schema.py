"""Initial schema from ORM metadata.

Revision ID: 001
Revises:
Create Date: 2026-04-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from backend.db.base import Base
    import backend.db.models  # noqa: F401, F403

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from backend.db.base import Base
    import backend.db.models  # noqa: F401, F403

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
