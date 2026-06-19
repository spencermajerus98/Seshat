"""Notebook entries + the Dashboard aggregate."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from core import notebook, sync

from .. import config, security
from ..deps import current_session, db as db_lock
from ..schemas import EntryCreate

router = APIRouter(prefix="/api", tags=["notebook"])


@router.get("/notebook/entries")
def list_entries(
    date: Optional[str] = None,
    entry_type: Optional[str] = None,
    source: Optional[str] = None,
    limit: Optional[int] = 500,
    sess: security.Session = Depends(current_session),
):
    on_date = dt.date.fromisoformat(date) if date else None
    with db_lock(sess) as conn:
        return notebook.list_entries(
            conn,
            on_date=on_date,
            entry_type=entry_type,
            source=source,
            limit=limit,
        )


@router.post("/notebook/entries")
def add_entry(body: EntryCreate, sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        try:
            entry_id = notebook.add_entry(
                conn,
                body.text,
                entry_type=body.entry_type,
                experiment_id=body.experiment_id,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc))
    return {"id": entry_id}


@router.delete("/notebook/entries/{entry_id}")
def delete_entry(entry_id: int, sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        notebook.delete_entry(conn, entry_id)
    return {"ok": True}


@router.get("/notebook/dates")
def entry_dates(sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        return notebook.distinct_entry_dates(conn)


@router.get("/dashboard")
def dashboard(sess: security.Session = Depends(current_session)):
    today = dt.date.today()
    with db_lock(sess) as conn:
        today_entries = notebook.list_entries(conn, on_date=today)
        protocols = conn.execute("SELECT count(*) FROM protocols").fetchone()[0]
        experiments = conn.execute("SELECT count(*) FROM experiments").fetchone()[0]
        tasks = [
            dict(r)
            for r in conn.execute(
                """
                SELECT t.id, t.task_name, t.planned_date, t.sample, t.reagent,
                       x.name AS experiment_name
                FROM experiment_tasks t
                JOIN experiments x ON x.id = t.experiment_id
                WHERE t.status = 'pending'
                ORDER BY t.planned_date IS NULL, t.planned_date, t.id
                LIMIT 100
                """
            ).fetchall()
        ]
    return {
        "entries_today": len(today_entries),
        "protocols": protocols,
        "experiments": experiments,
        "pending_notes": sync.count_pending(config.inbox_dir()),
        "pending_tasks": tasks,
        "today_entries": today_entries,
    }


@router.post("/dashboard/tasks/{task_id}/complete")
def complete_task(task_id: int, sess: security.Session = Depends(current_session)):
    """Mark a task done and log a 'task_done' notebook entry (Dashboard action)."""
    with db_lock(sess) as conn:
        row = conn.execute(
            "SELECT task_name, experiment_id FROM experiment_tasks WHERE id=?",
            (task_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Task not found.")
        conn.execute("UPDATE experiment_tasks SET status='done' WHERE id=?", (task_id,))
        conn.commit()
        notebook.add_entry(
            conn,
            f"Completed task: {row['task_name']}",
            entry_type="task_done",
            experiment_id=row["experiment_id"],
        )
    return {"ok": True}
