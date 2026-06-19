"""Experiments, their tasks, and the Labguru-ready report."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from core import experiments as expm

from .. import security
from ..deps import current_session, db as db_lock
from ..schemas import ExperimentPayload, TaskCreate, TaskStatus

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.get("")
def list_experiments(sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        exps = expm.list_experiments(conn)
        counts = {
            r[0]: (r[1], r[2])
            for r in conn.execute(
                """
                SELECT experiment_id,
                       count(*) AS total,
                       sum(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done
                FROM experiment_tasks GROUP BY experiment_id
                """
            ).fetchall()
        }
    for e in exps:
        total, done = counts.get(e["id"], (0, 0))
        e["task_total"] = int(total or 0)
        e["task_done"] = int(done or 0)
    return exps


@router.post("")
def create_experiment(
    body: ExperimentPayload, sess: security.Session = Depends(current_session)
):
    with db_lock(sess) as conn:
        try:
            eid = expm.create_experiment(
                conn,
                name=body.name,
                type_id=body.type_id,
                start_date=body.start_date,
                duration_days=body.duration_days,
                protocol_id=body.protocol_id,
                setup_values=body.setup_values,
                description=body.description,
                status=body.status,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc))
    return {"id": eid}


@router.get("/{experiment_id}")
def get_experiment(experiment_id: int, sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        exp = expm.get_experiment(conn, experiment_id)
    if not exp:
        raise HTTPException(404, "Experiment not found.")
    return exp


@router.put("/{experiment_id}")
def update_experiment(
    experiment_id: int,
    body: ExperimentPayload,
    sess: security.Session = Depends(current_session),
):
    with db_lock(sess) as conn:
        if not expm.get_experiment(conn, experiment_id):
            raise HTTPException(404, "Experiment not found.")
        if not body.name.strip():
            raise HTTPException(400, "Experiment name is required.")
        expm.update_experiment(
            conn,
            experiment_id,
            name=body.name,
            type_id=body.type_id,
            start_date=body.start_date,
            duration_days=body.duration_days,
            protocol_id=body.protocol_id,
            setup_values=body.setup_values,
            description=body.description,
            status=body.status,
        )
    return {"ok": True}


@router.delete("/{experiment_id}")
def delete_experiment(experiment_id: int, sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        expm.delete_experiment(conn, experiment_id)
    return {"ok": True}


@router.get("/{experiment_id}/report")
def report(experiment_id: int, sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        return expm.build_experiment_report(conn, experiment_id)


# ── Tasks ─────────────────────────────────────────────────────────────────────
@router.get("/{experiment_id}/tasks")
def list_tasks(experiment_id: int, sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        return expm.list_tasks(conn, experiment_id)


@router.post("/{experiment_id}/tasks")
def add_task(
    experiment_id: int,
    body: TaskCreate,
    sess: security.Session = Depends(current_session),
):
    if not body.task_name.strip():
        raise HTTPException(400, "Task name is required.")
    with db_lock(sess) as conn:
        tid = expm.add_task(
            conn, experiment_id, body.task_name, planned_date=body.planned_date
        )
    return {"id": tid}


@router.put("/tasks/{task_id}/status")
def set_task_status(
    task_id: int, body: TaskStatus, sess: security.Session = Depends(current_session)
):
    with db_lock(sess) as conn:
        expm.set_task_status(conn, task_id, body.status)
    return {"ok": True}


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        conn.execute("DELETE FROM experiment_tasks WHERE id=?", (task_id,))
        conn.commit()
    return {"ok": True}
