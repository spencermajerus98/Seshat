"""Experiment types and their modular field templates.

An experiment *type* (e.g. "Lentiviral transduction", "CRISPR knock-in") owns a
list of **field definitions** describing the setup conditions to capture. Each
field is a dict:

    {"key": "vectors", "label": "Vectors used", "kind": "multiselect", "vocab": "vector"}

``kind`` ∈ {text, textarea, number, date, select, multiselect, protocol, checkbox}.
``vocab`` (for select/multiselect) names a controlled list in :mod:`core.vocab`.
This makes experiments modular: a type defines its fields, experiments of that
type render them, and the user can add/edit fields or whole new types.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from .db import Connection
from .notebook import now_ts

VALID_KINDS = ["text", "textarea", "number", "date", "select", "multiselect", "protocol", "checkbox"]


def default_field_template() -> list[dict[str, Any]]:
    """The minimum setup conditions every new type starts with (customizable)."""
    return [
        {"key": "vectors", "label": "Vectors used", "kind": "multiselect", "vocab": "vector"},
        {"key": "cells", "label": "Cells used", "kind": "multiselect", "vocab": "cell"},
        {"key": "reagents", "label": "Reagents / media", "kind": "multiselect", "vocab": "reagent"},
        {"key": "protocol", "label": "Protocol", "kind": "protocol"},
        {"key": "objective", "label": "Objective / notes", "kind": "textarea"},
    ]


def list_types(conn: Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name, fields_json FROM experiment_types ORDER BY name COLLATE NOCASE"
    ).fetchall()
    out = []
    for r in rows:
        out.append({"id": r["id"], "name": r["name"], "fields": json.loads(r["fields_json"])})
    return out


def get_type(conn: Connection, type_id: int) -> Optional[dict]:
    r = conn.execute(
        "SELECT id, name, fields_json FROM experiment_types WHERE id = ?", (type_id,)
    ).fetchone()
    if not r:
        return None
    return {"id": r["id"], "name": r["name"], "fields": json.loads(r["fields_json"])}


def get_type_by_name(conn: Connection, name: str) -> Optional[dict]:
    r = conn.execute(
        "SELECT id FROM experiment_types WHERE lower(name) = lower(?)", (name,)
    ).fetchone()
    return get_type(conn, r["id"]) if r else None


def create_type(
    conn: Connection, name: str, fields: Optional[list[dict]] = None
) -> int:
    """Create a type (or return the existing id if the name is taken)."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Experiment type name is required.")
    existing = get_type_by_name(conn, name)
    if existing:
        return existing["id"]
    fields = fields if fields is not None else default_field_template()
    cur = conn.execute(
        "INSERT INTO experiment_types (name, fields_json, created_at) VALUES (?, ?, ?)",
        (name, json.dumps(fields), now_ts()),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_type_fields(conn: Connection, type_id: int, fields: list[dict]) -> None:
    conn.execute(
        "UPDATE experiment_types SET fields_json = ? WHERE id = ?",
        (json.dumps(fields), type_id),
    )
    conn.commit()


def rename_type(conn: Connection, type_id: int, new_name: str) -> None:
    conn.execute(
        "UPDATE experiment_types SET name = ? WHERE id = ?", (new_name.strip(), type_id)
    )
    conn.commit()


def slugify(label: str) -> str:
    """Turn a human field label into a stable dict key."""
    import re

    key = re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")
    return key or "field"
