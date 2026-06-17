"""Controlled vocabularies — the user-extensible dropdown lists.

A single ``vocab_terms`` table backs every managed dropdown (vectors, cells,
reagents/media, …). The UI reads terms for a category to populate a
multiselect and can append new terms inline.
"""

from __future__ import annotations

from .db import Connection

# Categories Seshat manages out of the box. The UI may surface others.
CATEGORIES = ["vector", "cell", "reagent"]
CATEGORY_LABELS = {
    "vector": "Vectors",
    "cell": "Cells / cell lines",
    "reagent": "Reagents / media",
}


def list_terms(conn: Connection, category: str) -> list[str]:
    rows = conn.execute(
        "SELECT value FROM vocab_terms WHERE category = ? ORDER BY value COLLATE NOCASE",
        (category,),
    ).fetchall()
    return [r[0] for r in rows]


def add_term(conn: Connection, category: str, value: str) -> None:
    value = (value or "").strip()
    if not value:
        return
    conn.execute(
        "INSERT OR IGNORE INTO vocab_terms (category, value) VALUES (?, ?)",
        (category, value),
    )
    conn.commit()


def add_terms(conn: Connection, category: str, values: list[str]) -> None:
    """Ensure each value exists in the category (used when saving multiselects)."""
    for v in values:
        add_term(conn, category, v)


def delete_term(conn: Connection, category: str, value: str) -> None:
    conn.execute(
        "DELETE FROM vocab_terms WHERE category = ? AND value = ?", (category, value)
    )
    conn.commit()
