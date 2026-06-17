"""Tests for in-app experiment creation, editing, scheduling and reporting."""

import datetime as dt

from core import exp_types, experiments as expm


def _generic_type_id(conn):
    return exp_types.get_type_by_name(conn, "Generic")["id"]


def test_compute_end_date_inclusive():
    assert expm.compute_end_date("2026-06-16", 5) == "2026-06-20"
    assert expm.compute_end_date("2026-06-16", 1) == "2026-06-16"
    assert expm.compute_end_date(None, 5) is None


def test_create_and_get_experiment(conn):
    pid = conn.execute(
        "INSERT INTO protocols (title, imported_at) VALUES ('Transduction', 'x')"
    ).lastrowid
    conn.commit()
    xid = expm.create_experiment(
        conn,
        name="Lenti prep A",
        type_id=_generic_type_id(conn),
        start_date="2026-06-16",
        duration_days=5,
        protocol_id=pid,
        setup_values={"vectors": ["Lentiviral"], "cells": ["HEK293T"], "protocol": pid},
    )
    exp = expm.get_experiment(conn, xid)
    assert exp["name"] == "Lenti prep A"
    assert exp["end_date"] == "2026-06-20"
    assert exp["setup"]["vectors"] == ["Lentiviral"]
    # Creation is auto-logged to the notebook.
    logged = conn.execute(
        "SELECT count(*) FROM notebook_entries WHERE experiment_id=?", (xid,)
    ).fetchone()[0]
    assert logged == 1


def test_update_experiment(conn):
    xid = expm.create_experiment(conn, name="X", start_date="2026-06-01", duration_days=2)
    expm.update_experiment(
        conn, xid, name="X2", type_id=None, start_date="2026-06-01",
        duration_days=4, protocol_id=None, setup_values={"note": "hi"},
        description="d", status="active",
    )
    exp = expm.get_experiment(conn, xid)
    assert exp["name"] == "X2"
    assert exp["status"] == "active"
    assert exp["end_date"] == "2026-06-04"


def test_experiments_active_on(conn):
    expm.create_experiment(conn, name="Spanning", start_date="2026-06-16", duration_days=5)
    active = expm.experiments_active_on(conn, dt.date(2026, 6, 18))
    assert any(e["name"] == "Spanning" for e in active)
    assert not expm.experiments_active_on(conn, dt.date(2026, 6, 25))


def test_build_experiment_report(conn):
    xid = expm.create_experiment(
        conn,
        name="Report exp",
        type_id=_generic_type_id(conn),
        start_date="2026-06-16",
        duration_days=3,
        setup_values={"vectors": ["AAV"], "cells": ["iPSC"]},
    )
    rep = expm.build_experiment_report(conn, xid)
    assert "Report exp" in rep["text"]
    assert "Vectors used" in rep["markdown"]
    assert "AAV" in rep["html"]
    assert "<h2>" in rep["html"]
