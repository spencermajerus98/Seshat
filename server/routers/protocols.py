"""Protocols — list/search, rename, delete, and original-file viewer."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from core import docx_pdf

from .. import security
from ..deps import current_session, db as db_lock

router = APIRouter(prefix="/api/protocols", tags=["protocols"])

# Columns that are safe to return in list responses (excludes the BLOB).
_LIST_COLS = (
    "id, title, source_filename, version, imported_at, body_text, tags, file_mime, "
    "(file_data IS NOT NULL) AS has_file"
)


@router.get("")
def list_protocols(
    q: Optional[str] = None, sess: security.Session = Depends(current_session)
):
    with db_lock(sess) as conn:
        if q:
            like = f"%{q}%"
            rows = conn.execute(
                f"SELECT {_LIST_COLS} FROM protocols "
                "WHERE title LIKE ? OR body_text LIKE ? "
                "ORDER BY title COLLATE NOCASE",
                (like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {_LIST_COLS} FROM protocols ORDER BY title COLLATE NOCASE"
            ).fetchall()

        protocols = []
        for p in rows:
            steps = conn.execute(
                "SELECT step_no, text FROM protocol_steps WHERE protocol_id=? "
                "ORDER BY step_no",
                (p["id"],),
            ).fetchall()
            d = dict(p)
            d["has_file"] = bool(d.get("has_file", False))
            d["steps"] = [dict(s) for s in steps]
            protocols.append(d)
    return protocols


class ProtocolRename(BaseModel):
    title: str


@router.put("/{protocol_id}")
def rename_protocol(
    protocol_id: int,
    body: ProtocolRename,
    sess: security.Session = Depends(current_session),
):
    if not body.title.strip():
        raise HTTPException(400, "Title is required.")
    with db_lock(sess) as conn:
        conn.execute(
            "UPDATE protocols SET title=? WHERE id=?",
            (body.title.strip(), protocol_id),
        )
        conn.commit()
    return {"ok": True}


class StepsUpdate(BaseModel):
    steps: list[str]


@router.put("/{protocol_id}/steps")
def update_steps(
    protocol_id: int,
    body: StepsUpdate,
    sess: security.Session = Depends(current_session),
):
    """Replace a protocol's steps with the supplied list (edit/add/delete/reorder).

    Blank entries are dropped and the remaining steps are renumbered 1..N.
    """
    cleaned = [s.strip() for s in body.steps if s and s.strip()]
    with db_lock(sess) as conn:
        exists = conn.execute(
            "SELECT 1 FROM protocols WHERE id=?", (protocol_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(404, "Protocol not found.")
        conn.execute("DELETE FROM protocol_steps WHERE protocol_id=?", (protocol_id,))
        for i, text in enumerate(cleaned, start=1):
            conn.execute(
                "INSERT INTO protocol_steps (protocol_id, step_no, text) VALUES (?, ?, ?)",
                (protocol_id, i, text),
            )
        conn.commit()
    return {"ok": True, "count": len(cleaned)}


@router.get("/{protocol_id}/file")
def get_protocol_file(
    protocol_id: int, sess: security.Session = Depends(current_session)
):
    """Return the original file bytes stored at import time.

    Served as-is with the stored MIME type. The frontend chooses how to render:
    PDFs/plain text go in an iframe; DOCX is rendered client-side by docx-preview.
    """
    with db_lock(sess) as conn:
        row = conn.execute(
            "SELECT file_data, file_mime, title FROM protocols WHERE id=?",
            (protocol_id,),
        ).fetchone()

    if not row or not row["file_data"]:
        raise HTTPException(404, "No original file stored for this protocol.")

    data: bytes = bytes(row["file_data"])
    mime: str = row["file_mime"] or "application/octet-stream"
    return Response(content=data, media_type=mime)


@router.get("/{protocol_id}/file.pdf")
def get_protocol_pdf(
    protocol_id: int, sess: security.Session = Depends(current_session)
):
    """Return a PDF rendering of the protocol's document, for high-fidelity viewing.

    Already-PDF protocols are returned directly. DOCX protocols are converted with
    a real layout engine (Word/LibreOffice) on first view and the result is cached
    in ``pdf_render``. Returns 503 when no converter is available so the frontend
    can fall back to the client-side docx-preview renderer.
    """
    with db_lock(sess) as conn:
        row = conn.execute(
            "SELECT pdf_render, file_data, file_mime FROM protocols WHERE id=?",
            (protocol_id,),
        ).fetchone()

    if not row or not row["file_data"]:
        raise HTTPException(404, "No original file stored for this protocol.")

    if row["pdf_render"]:
        return Response(content=bytes(row["pdf_render"]), media_type="application/pdf")

    mime: str = row["file_mime"] or ""
    if "pdf" in mime:
        return Response(content=bytes(row["file_data"]), media_type="application/pdf")

    if "wordprocessingml" not in mime:
        raise HTTPException(415, "No PDF rendering available for this file type.")

    if not docx_pdf.converter_available():
        raise HTTPException(503, "No DOCX→PDF converter is available on this machine.")

    # Convert outside the DB lock — Word/LibreOffice can take several seconds and
    # the shared connection lock would otherwise stall every other request.
    pdf = docx_pdf.convert_docx_to_pdf(bytes(row["file_data"]))
    if not pdf:
        raise HTTPException(500, "Failed to convert the document to PDF.")

    with db_lock(sess) as conn:
        conn.execute(
            "UPDATE protocols SET pdf_render=? WHERE id=?", (pdf, protocol_id)
        )
        conn.commit()
    return Response(content=pdf, media_type="application/pdf")


@router.delete("/{protocol_id}")
def delete_protocol(protocol_id: int, sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        conn.execute("DELETE FROM protocols WHERE id=?", (protocol_id,))
        conn.commit()
    return {"ok": True}
