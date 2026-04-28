"""Ensure conversations.updated_at exists (ORM insert must satisfy NOT NULL).

Revision ID: 010
Revises: 009
Create Date: 2026-04-24

Some databases added a NOT NULL conversations.updated_at without a server default;
SQLAlchemy inserts that omit the column then fail. This revision adds the column only
when missing, with a default for backfill.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "conversations" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("conversations")}
    if "updated_at" in cols:
        return
    op.add_column(
        "conversations",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """No-op: updated_at may have existed before this revision; dropping it is unsafe."""
