"""Tests for the database layer and notebook entries."""

import datetime as dt

import pytest

from core import crypto, db, notebook


def test_entry_gets_automatic_timestamp(conn):
    entry_id = notebook.add_entry(conn, "Seeded HEK293T cells", entry_type="task_done")
    rows = notebook.list_entries(conn)
    assert len(rows) == 1
    assert rows[0]["id"] == entry_id
    # created_at is a parseable ISO timestamp set automatically.
    dt.datetime.strptime(rows[0]["created_at"], notebook.TS_FMT)


def test_empty_entry_rejected(conn):
    with pytest.raises(ValueError):
        notebook.add_entry(conn, "   ")


def test_filter_by_date_and_source(conn):
    notebook.add_entry(conn, "today app note")
    notebook.add_entry(
        conn, "old phone note", source="phone", created_at="2000-01-01T08:00:00"
    )
    today = notebook.list_entries(conn, on_date=dt.date.today())
    assert len(today) == 1 and today[0]["source"] == "app"
    phone = notebook.list_entries(conn, source="phone")
    assert len(phone) == 1 and phone[0]["text"] == "old phone note"


def test_unknown_entry_type_defaults_to_note(conn):
    notebook.add_entry(conn, "x", entry_type="bogus")
    assert notebook.list_entries(conn)[0]["entry_type"] == "note"


def test_wrong_passphrase_rejected(tmp_path):
    path = str(tmp_path / "secure.db")
    c = db.connect(path, "correct-horse")
    c.close()
    with pytest.raises(db.BadPassphrase):
        db.connect(path, "wrong-horse")


def test_verifier_roundtrip():
    salt = crypto.new_salt()
    v = crypto.derive_verifier("hunter2", salt)
    assert crypto.verify("hunter2", salt, v)
    assert not crypto.verify("hunter3", salt, v)
