"""Tests for daily summary generation."""

import datetime as dt

from core import notebook, summary


def test_summary_groups_and_orders(conn):
    notebook.add_entry(conn, "Completed transfection", entry_type="task_done")
    notebook.add_entry(conn, "Saw GFP signal", entry_type="observation")
    notebook.add_entry(conn, "Titer 1e8 IU/mL", entry_type="result")

    out = summary.build_daily_summary(conn, dt.date.today())
    text, md = out["text"], out["markdown"]

    assert "TASKS COMPLETED" in text
    assert "OBSERVATIONS" in text
    assert "RESULTS" in text
    assert "Titer 1e8 IU/mL" in md
    # Tasks section comes before results section.
    assert text.index("TASKS COMPLETED") < text.index("RESULTS")


def test_summary_empty_date(conn):
    out = summary.build_daily_summary(conn, dt.date(2000, 1, 1))
    assert "No entries recorded" in out["text"]


def test_summary_lists_experiments(conn):
    conn.execute("INSERT INTO experiments (name, imported_at) VALUES ('Prep A', 'x')")
    conn.commit()
    xid = conn.execute("SELECT id FROM experiments").fetchone()[0]
    notebook.add_entry(conn, "Started", entry_type="note", experiment_id=xid)
    out = summary.build_daily_summary(conn, dt.date.today())
    assert "Prep A" in out["text"]
