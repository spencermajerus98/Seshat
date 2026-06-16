"""Tests for phone-note inbox ingestion."""

import os

from core import notebook, sync


def _write(inbox, name, content):
    with open(os.path.join(inbox, name), "w", encoding="utf-8") as fh:
        fh.write(content)


def test_scan_ingests_and_moves(tmp_path, conn):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _write(str(inbox), "note1.txt", "Observed 80% confluence in flask 2")

    ingested = sync.scan_inbox(conn, str(inbox))
    assert len(ingested) == 1

    entries = notebook.list_entries(conn, source="phone")
    assert entries[0]["text"] == "Observed 80% confluence in flask 2"
    # File moved into processed/ so a second scan ingests nothing.
    assert os.path.exists(str(inbox / "processed" / "note1.txt"))
    assert sync.scan_inbox(conn, str(inbox)) == []


def test_markers_parsed(tmp_path, conn):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    # An experiment to link against.
    conn.execute(
        "INSERT INTO experiments (name, imported_at) VALUES ('CRISPR knock-in', 'x')"
    )
    conn.commit()
    _write(
        str(inbox),
        "dictated.md",
        "[ts: 2026-06-16T14:30]\n#exp: CRISPR knock-in\n#type: observation\n"
        "Cells looked healthy after electroporation.",
    )

    sync.scan_inbox(conn, str(inbox))
    e = notebook.list_entries(conn, source="phone")[0]
    assert e["created_at"] == "2026-06-16T14:30:00"
    assert e["entry_type"] == "observation"
    assert e["experiment_name"] == "CRISPR knock-in"
    assert e["text"] == "Cells looked healthy after electroporation."


def test_count_pending(tmp_path, conn):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _write(str(inbox), "a.txt", "one")
    _write(str(inbox), "b.md", "two")
    _write(str(inbox), "ignore.json", "{}")
    assert sync.count_pending(str(inbox)) == 2
