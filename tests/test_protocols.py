"""Tests for the protocol viewer: file storage, file serving, and rename."""

import pytest
from docx import Document
from fastapi.testclient import TestClient

from core import files


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A TestClient whose config points at a throwaway data dir (unlocked)."""
    import server.config as cfg

    monkeypatch.setattr(cfg, "CONFIG_PATH", str(tmp_path / "cfg.json"))
    monkeypatch.setattr(cfg, "DEFAULT_DB_PATH", str(tmp_path / "seshat.db"))
    monkeypatch.setattr(cfg, "DEFAULT_INBOX_DIR", str(tmp_path / "inbox"))

    from server.main import app

    c = TestClient(app)
    c.post("/api/auth/unlock", json={"passphrase": "test-pass", "confirm": "test-pass"})
    return c


def _make_docx(path):
    doc = Document()
    doc.add_paragraph("Lentiviral Transduction Protocol")
    doc.add_paragraph("Thaw cells", style="List Number")
    doc.add_paragraph("Add polybrene", style="List Number")
    doc.save(path)


def test_import_stores_file_bytes(conn, tmp_path):
    p = tmp_path / "protocol.docx"
    _make_docx(str(p))
    pid = files.import_protocol_file(conn, str(p))
    row = conn.execute(
        "SELECT file_data, file_mime FROM protocols WHERE id=?", (pid,)
    ).fetchone()
    assert row["file_data"] is not None
    assert len(bytes(row["file_data"])) > 0
    assert "wordprocessingml" in row["file_mime"]


def test_pdf_mime_detected(conn, tmp_path):
    # Build a real (if blank) PDF with pypdf's writer so parse_pdf succeeds.
    from pypdf import PdfWriter

    p = tmp_path / "proto.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(p, "wb") as fh:
        writer.write(fh)

    pid = files.import_protocol_file(conn, str(p))
    row = conn.execute(
        "SELECT file_mime, file_data FROM protocols WHERE id=?", (pid,)
    ).fetchone()
    assert row["file_mime"] == "application/pdf"
    assert bytes(row["file_data"]).startswith(b"%PDF")


def test_rename_and_list_via_api(client, tmp_path):
    # Stage + commit a docx through the upload flow so it has stored bytes.
    p = tmp_path / "myproto.docx"
    _make_docx(str(p))
    with open(p, "rb") as fh:
        up = client.post(
            "/api/files/upload",
            files={"file": ("myproto.docx", fh, "application/octet-stream")},
        )
    staged = up.json()["path"]
    commit = client.post(
        "/api/files/protocol/commit",
        json={"path": staged, "title": "Original Title"},
    )
    pid = commit.json()["id"]

    # List reports has_file=True and excludes the BLOB payload.
    protos = client.get("/api/protocols").json()
    target = next(p for p in protos if p["id"] == pid)
    assert target["has_file"] is True
    assert "file_data" not in target

    # Rename works and is reflected in the list.
    assert client.put(f"/api/protocols/{pid}", json={"title": "Renamed Protocol"}).status_code == 200
    protos = client.get("/api/protocols").json()
    assert next(p for p in protos if p["id"] == pid)["title"] == "Renamed Protocol"

    # Empty title rejected.
    assert client.put(f"/api/protocols/{pid}", json={"title": "  "}).status_code == 400


def test_serve_docx_as_html(client, tmp_path):
    p = tmp_path / "viewme.docx"
    _make_docx(str(p))
    with open(p, "rb") as fh:
        up = client.post(
            "/api/files/upload",
            files={"file": ("viewme.docx", fh, "application/octet-stream")},
        )
    staged = up.json()["path"]
    pid = client.post(
        "/api/files/protocol/commit", json={"path": staged, "title": "Viewer"}
    ).json()["id"]

    r = client.get(f"/api/protocols/{pid}/file")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Lentiviral Transduction Protocol" in r.text
    assert "<li>Thaw cells</li>" in r.text


def test_file_404_when_no_bytes(conn, client):
    # A protocol imported without file bytes (legacy) returns 404 on /file.
    from core import importers
    from core.models import ParsedProtocol

    # Reach into the live session's connection to insert a fileless protocol.
    import server.security as security

    sess = next(iter(security._sessions.values()))
    pid = importers.import_protocol(
        sess.conn, ParsedProtocol(title="No File", body_text="x", steps=[])
    )
    assert client.get(f"/api/protocols/{pid}/file").status_code == 404
