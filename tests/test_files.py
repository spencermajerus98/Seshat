"""Tests for the local file browser and protocol-from-text extraction."""

import os

from core import files, importers


def test_list_dir_filters_and_hides(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "proto.docx").write_text("x")
    (tmp_path / "plan.xlsx").write_text("x")
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "ignore.json").write_text("x")

    listing = files.list_dir(str(tmp_path))
    dir_names = [n for n, _ in listing["dirs"]]
    file_names = {f["name"] for f in listing["files"]}

    assert "sub" in dir_names
    assert ".hidden" not in dir_names
    assert file_names == {"proto.docx", "plan.xlsx", "notes.txt"}
    assert any(f["name"] == "plan.xlsx" and f["is_experiment"] for f in listing["files"])


def test_extract_protocol_from_text():
    text = "My Protocol\n1. Thaw cells\n2. Add media\nSome prose line"
    parsed = importers.extract_protocol_from_text(text, "my.txt")
    assert parsed.title == "My Protocol"
    assert parsed.steps == ["Thaw cells", "Add media"]


def test_import_protocol_file_text(conn, tmp_path):
    p = tmp_path / "wash.md"
    p.write_text("Wash Protocol\n1. PBS rinse\n2. Aspirate", encoding="utf-8")
    pid = files.import_protocol_file(conn, str(p))
    row = conn.execute("SELECT title FROM protocols WHERE id=?", (pid,)).fetchone()
    assert row["title"] == "Wash Protocol"
    steps = conn.execute(
        "SELECT count(*) FROM protocol_steps WHERE protocol_id=?", (pid,)
    ).fetchone()[0]
    assert steps == 2
