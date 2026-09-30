"""Dialect-aware ``INSERT … ON CONFLICT`` for PostgreSQL and SQLite."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Table
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session


def upsert(
    session: Session,
    table: Table,
    rows: Sequence[dict[str, Any]],
    *,
    conflict_columns: Sequence[str],
    update_columns: Sequence[str] | None = None,
) -> None:
    """Insert rows; on conflict update ``update_columns`` (or do nothing if empty)."""
    if not rows:
        return
    dialect = session.get_bind().dialect.name
    insert_fn = postgresql.insert if dialect == "postgresql" else sqlite.insert
    stmt = insert_fn(table).values(list(rows))
    if update_columns:
        stmt = stmt.on_conflict_do_update(
            index_elements=list(conflict_columns),
            set_={col: stmt.excluded[col] for col in update_columns},
        )
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=list(conflict_columns))
    session.execute(stmt)
