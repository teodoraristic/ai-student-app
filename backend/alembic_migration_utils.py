"""Idempotent checks for Alembic when revision 001 uses ORM create_all (full current schema)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.engine import Connection


def column_names(conn: Connection, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(conn).get_columns(table)}


def has_column(conn: Connection, table: str, column: str) -> bool:
    return column in column_names(conn, table)


def has_table(conn: Connection, table: str) -> bool:
    return sa.inspect(conn).has_table(table)


def has_fk(conn: Connection, table: str, fk_name: str) -> bool:
    for fk in sa.inspect(conn).get_foreign_keys(table):
        if fk.get("name") == fk_name:
            return True
    return False


def has_index(conn: Connection, table: str, index_name: str) -> bool:
    return any(idx.get("name") == index_name for idx in sa.inspect(conn).get_indexes(table))


def has_unique_constraint(conn: Connection, table: str, name: str) -> bool:
    for uc in sa.inspect(conn).get_unique_constraints(table):
        if uc.get("name") == name:
            return True
    return False
