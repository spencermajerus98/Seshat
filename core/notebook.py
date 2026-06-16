"""The automatic, timestamped lab notebook.

Every action in Seshat ultimately funnels through :func:`add_entry`, which
stamps ``created_at`` with the current local date/time unless one is supplied
(used when ingesting phone notes that carry their own timestamp). The user
never has to type a date or time.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Optional

from .db import Connection
from .models import ENTRY_TYPES, SOURCES

# Stored timestamp format: ISO-8601 to the second, local time.
TS_FMT = "%Y-%m-%dT%H:%M:%S"


def now_ts() -> str:
    return datetime.now().strftime(TS_FMT)


def add_entry(
    conn: Connection,
    text: str,
    *,
    entry_type: str = "note",
    source: str = "app",
    experiment_id: Optional[int] = None,
    protocol_id: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
    created_at: Optional[str] = None,
) -> int:
    """Insert a notebook entry and return its id.

    ``created_at`` defaults to now(); pass an ISO timestamp to preserve the
    original time of a synced note.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Notebook entry text cannot be empty.")
    if entry_type not in ENTRY_TYPES:
        entry_type = "note"
    if source not in SOURCES:
        source = "app"

    cur = conn.execute(
        """
        INSERT INTO notebook_entries
            (created_at, entry_type, source, experiment_id, protocol_id, text, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            created_at or now_ts(),
            entry_type,
            source,
            experiment_id,
            protocol_id,
            text,
            json.dumps(metadata) if metadata else None,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_entries(
    conn: Connection,
    *,
    on_date: Optional[date] = None,
    entry_type: Optional[str] = None,
    source: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict]:
    """Return notebook entries (newest first), optionally filtered."""
    clauses, params = [], []
    if on_date is not None:
        clauses.append("date(created_at) = ?")
        params.append(on_date.isoformat())
    if entry_type:
        clauses.append("entry_type = ?")
        params.append(entry_type)
    if source:
        clauses.append("source = ?")
        params.append(source)

    sql = """
        SELECT e.*, x.name AS experiment_name, p.title AS protocol_title
        FROM notebook_entries e
        LEFT JOIN experiments x ON x.id = e.experiment_id
        LEFT JOIN protocols   p ON p.id = e.protocol_id
    """
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY e.created_at DESC, e.id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"

    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def delete_entry(conn: Connection, entry_id: int) -> None:
    conn.execute("DELETE FROM notebook_entries WHERE id = ?", (entry_id,))
    conn.commit()


def distinct_entry_dates(conn: Connection) -> list[str]:
    """Dates (ISO) that have at least one entry, newest first."""
    rows = conn.execute(
        "SELECT DISTINCT date(created_at) AS d FROM notebook_entries ORDER BY d DESC"
    ).fetchall()
    return [r[0] for r in rows]
