"""Create / edit experiments and render them for Labguru.

Experiments are modular: their setup-condition values are stored as JSON keyed
by the field template of their :mod:`core.exp_types`. Scheduling uses
``start_date`` + ``duration_days`` to derive ``end_date`` for the calendar.
"""

from __future__ import annotations

import html as _html
import json
from datetime import date, datetime, timedelta
from typing import Any, Optional

from . import exp_types
from .db import Connection
from .notebook import TS_FMT, add_entry, now_ts


def compute_end_date(start_date: Optional[str], duration_days: Optional[int]) -> Optional[str]:
    """Inclusive end date: a 1-day experiment ends on its start date."""
    if not start_date or not duration_days:
        return start_date or None
    try:
        start = date.fromisoformat(start_date)
    except (TypeError, ValueError):
        return None
    return (start + timedelta(days=max(int(duration_days) - 1, 0))).isoformat()


def create_experiment(
    conn: Connection,
    *,
    name: str,
    type_id: Optional[int] = None,
    start_date: Optional[str] = None,
    duration_days: Optional[int] = None,
    protocol_id: Optional[int] = None,
    setup_values: Optional[dict[str, Any]] = None,
    description: Optional[str] = None,
    status: str = "planned",
    log: bool = True,
) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("Experiment name is required.")
    end_date = compute_end_date(start_date, duration_days)
    cur = conn.execute(
        """
        INSERT INTO experiments
            (name, description, planned_date, status, imported_at, metadata_json,
             type_id, start_date, end_date, duration_days, protocol_id, setup_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            description,
            start_date,
            status,
            now_ts(),
            None,
            type_id,
            start_date,
            end_date,
            duration_days,
            protocol_id,
            json.dumps(setup_values or {}),
        ),
    )
    experiment_id = int(cur.lastrowid)
    conn.commit()
    if log:
        add_entry(
            conn,
            f"Created experiment: {name}",
            entry_type="note",
            experiment_id=experiment_id,
        )
    return experiment_id


def update_experiment(
    conn: Connection,
    experiment_id: int,
    *,
    name: str,
    type_id: Optional[int],
    start_date: Optional[str],
    duration_days: Optional[int],
    protocol_id: Optional[int],
    setup_values: dict[str, Any],
    description: Optional[str],
    status: str,
    log: bool = True,
) -> None:
    end_date = compute_end_date(start_date, duration_days)
    conn.execute(
        """
        UPDATE experiments
        SET name=?, description=?, planned_date=?, status=?, type_id=?,
            start_date=?, end_date=?, duration_days=?, protocol_id=?, setup_json=?
        WHERE id=?
        """,
        (
            name.strip(),
            description,
            start_date,
            status,
            type_id,
            start_date,
            end_date,
            duration_days,
            protocol_id,
            json.dumps(setup_values or {}),
            experiment_id,
        ),
    )
    conn.commit()
    if log:
        add_entry(
            conn,
            f"Updated experiment: {name}",
            entry_type="note",
            experiment_id=experiment_id,
        )


def get_experiment(conn: Connection, experiment_id: int) -> Optional[dict]:
    r = conn.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,)).fetchone()
    if not r:
        return None
    exp = dict(r)
    exp["setup"] = json.loads(exp.get("setup_json") or "{}")
    return exp


def list_experiments(conn: Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT e.*, t.name AS type_name
        FROM experiments e
        LEFT JOIN experiment_types t ON t.id = e.type_id
        ORDER BY (e.start_date IS NULL), e.start_date, e.id DESC
        """
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["setup"] = json.loads(d.get("setup_json") or "{}")
        out.append(d)
    return out


def experiments_active_on(conn: Connection, on_date: date) -> list[dict]:
    """Experiments whose [start_date, end_date] span includes the given date."""
    iso = on_date.isoformat()
    rows = conn.execute(
        """
        SELECT e.*, t.name AS type_name
        FROM experiments e
        LEFT JOIN experiment_types t ON t.id = e.type_id
        WHERE e.start_date IS NOT NULL
          AND e.start_date <= ?
          AND COALESCE(e.end_date, e.start_date) >= ?
        ORDER BY e.start_date, e.id
        """,
        (iso, iso),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["setup"] = json.loads(d.get("setup_json") or "{}")
        out.append(d)
    return out


def delete_experiment(conn: Connection, experiment_id: int) -> None:
    conn.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))
    conn.commit()


# ── Tasks ────────────────────────────────────────────────────────────────────
def add_task(
    conn: Connection,
    experiment_id: int,
    task_name: str,
    *,
    planned_date: Optional[str] = None,
    sample: Optional[str] = None,
    reagent: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO experiment_tasks
            (experiment_id, task_name, planned_date, sample, reagent, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """,
        (experiment_id, task_name.strip(), planned_date, sample, reagent, notes),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_tasks(conn: Connection, experiment_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM experiment_tasks WHERE experiment_id=? "
        "ORDER BY planned_date IS NULL, planned_date, id",
        (experiment_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def set_task_status(conn: Connection, task_id: int, status: str) -> None:
    conn.execute("UPDATE experiment_tasks SET status=? WHERE id=?", (status, task_id))
    conn.commit()


# ── Labguru-ready report ──────────────────────────────────────────────────────
def _resolve_setup(conn: Connection, exp: dict) -> list[tuple[str, str]]:
    """Return [(label, value_str)] for an experiment's setup conditions."""
    type_fields = []
    if exp.get("type_id"):
        t = exp_types.get_type(conn, exp["type_id"])
        if t:
            type_fields = t["fields"]
    label_by_key = {f["key"]: f["label"] for f in type_fields}
    kind_by_key = {f["key"]: f["kind"] for f in type_fields}

    rows: list[tuple[str, str]] = []
    setup = exp.get("setup") or {}
    # Preserve template order, then any extra keys.
    keys = [f["key"] for f in type_fields] + [k for k in setup if k not in label_by_key]
    for key in keys:
        val = setup.get(key)
        if val in (None, "", [], {}):
            continue
        label = label_by_key.get(key, key.replace("_", " ").title())
        if kind_by_key.get(key) == "protocol":
            pr = conn.execute("SELECT title FROM protocols WHERE id=?", (val,)).fetchone()
            val_str = pr["title"] if pr else f"#{val}"
        elif isinstance(val, list):
            val_str = ", ".join(str(v) for v in val)
        else:
            val_str = str(val)
        rows.append((label, val_str))
    return rows


def build_experiment_report(conn: Connection, experiment_id: int) -> dict[str, str]:
    """Render an experiment's setup as html/markdown/plain text for Labguru."""
    exp = get_experiment(conn, experiment_id)
    if not exp:
        return {"html": "", "markdown": "", "text": ""}

    type_name = ""
    if exp.get("type_id"):
        t = exp_types.get_type(conn, exp["type_id"])
        type_name = t["name"] if t else ""

    schedule = ""
    if exp.get("start_date"):
        schedule = exp["start_date"]
        if exp.get("end_date") and exp["end_date"] != exp["start_date"]:
            schedule += f" → {exp['end_date']}"
        if exp.get("duration_days"):
            schedule += f" ({exp['duration_days']} day(s))"

    setup_rows = _resolve_setup(conn, exp)

    # Markdown
    md = [f"## {exp['name']}"]
    if type_name:
        md.append(f"**Type:** {type_name}")
    if schedule:
        md.append(f"**Scheduled:** {schedule}")
    if exp.get("status"):
        md.append(f"**Status:** {exp['status']}")
    if exp.get("description"):
        md.append(f"\n{exp['description']}")
    if setup_rows:
        md.append("\n**Setup conditions**")
        md += [f"- **{label}:** {value}" for label, value in setup_rows]

    # Plain text
    txt = [exp["name"]]
    if type_name:
        txt.append(f"Type: {type_name}")
    if schedule:
        txt.append(f"Scheduled: {schedule}")
    if exp.get("status"):
        txt.append(f"Status: {exp['status']}")
    if exp.get("description"):
        txt.append("")
        txt.append(exp["description"])
    if setup_rows:
        txt.append("")
        txt.append("Setup conditions:")
        txt += [f"  - {label}: {value}" for label, value in setup_rows]

    # HTML (rich paste into Labguru)
    h = [f"<h2>{_html.escape(exp['name'])}</h2>", "<ul>"]
    if type_name:
        h.append(f"<li><strong>Type:</strong> {_html.escape(type_name)}</li>")
    if schedule:
        h.append(f"<li><strong>Scheduled:</strong> {_html.escape(schedule)}</li>")
    if exp.get("status"):
        h.append(f"<li><strong>Status:</strong> {_html.escape(exp['status'])}</li>")
    h.append("</ul>")
    if exp.get("description"):
        h.append(f"<p>{_html.escape(exp['description'])}</p>")
    if setup_rows:
        h.append("<p><strong>Setup conditions</strong></p><ul>")
        h += [
            f"<li><strong>{_html.escape(label)}:</strong> {_html.escape(value)}</li>"
            for label, value in setup_rows
        ]
        h.append("</ul>")

    return {"html": "\n".join(h), "markdown": "\n".join(md), "text": "\n".join(txt)}
