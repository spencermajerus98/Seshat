"""Folder browsing, favourites, and import (from local path or upload)."""

from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from core import files, importers
from core.models import ParsedProtocol

from .. import config, security
from ..deps import current_session, db as db_lock
from ..schemas import (
    ExcelParseRequest,
    ExperimentImport,
    FavoriteRequest,
    ListDirRequest,
    ProtocolImportFile,
)

router = APIRouter(prefix="/api/files", tags=["files"])

# Uploaded files are staged here so the same path-based preview/mapping flow
# serves both "browse local folder" and "upload". Cleared on process restart.
_UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "seshat_uploads")


def _parse_protocol(path: str) -> ParsedProtocol:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return importers.parse_word(path)
    if ext == ".pdf":
        return importers.parse_pdf(path)
    if ext in {".txt", ".md", ".markdown"}:
        return importers.parse_text(path)
    raise HTTPException(400, f"Unsupported protocol file type: {ext}")


# ── Browse ────────────────────────────────────────────────────────────────────
@router.get("/roots")
def roots(sess: security.Session = Depends(current_session)):
    return {
        "roots": [{"label": l, "path": p} for l, p in files.default_roots()],
        "favorites": config.favorites(),
    }


@router.post("/list")
def list_dir(body: ListDirRequest, sess: security.Session = Depends(current_session)):
    listing = files.list_dir(body.path)
    return {
        "path": listing["path"],
        "parent": listing["parent"],
        "dirs": [{"name": n, "path": p} for n, p in listing["dirs"]],
        "files": listing["files"],
    }


@router.post("/favorites")
def add_favorite(body: FavoriteRequest, sess: security.Session = Depends(current_session)):
    config.add_favorite(body.path)
    return {"favorites": config.favorites()}


@router.delete("/favorites")
def remove_favorite(path: str, sess: security.Session = Depends(current_session)):
    config.remove_favorite(path)
    return {"favorites": config.favorites()}


# ── Upload staging ──────────────────────────────────────────────────────────
@router.post("/upload")
def upload(
    file: UploadFile = File(...), sess: security.Session = Depends(current_session)
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in files.SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext or '(none)'}")
    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    dest = tempfile.mkdtemp(dir=_UPLOAD_DIR)
    path = os.path.join(dest, os.path.basename(file.filename or f"upload{ext}"))
    with open(path, "wb") as fh:
        fh.write(file.file.read())
    return {
        "path": path,
        "name": os.path.basename(path),
        "ext": ext,
        "is_experiment": ext in files.EXPERIMENT_EXTENSIONS,
    }


# ── Protocol import ───────────────────────────────────────────────────────────
@router.post("/protocol/from-path")
def import_protocol_from_path(
    body: ProtocolImportFile, sess: security.Session = Depends(current_session)
):
    """Direct import (the folder-browser one-click path)."""
    with db_lock(sess) as conn:
        try:
            pid = files.import_protocol_file(conn, body.path, tags=body.tags)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"Could not import: {exc}")
    return {"id": pid}


class ProtocolPreviewRequest(BaseModel):
    path: str


class ProtocolCommitRequest(BaseModel):
    path: str
    title: str
    version: str | None = None
    tags: str | None = None


@router.post("/protocol/preview")
def protocol_preview(
    body: ProtocolPreviewRequest, sess: security.Session = Depends(current_session)
):
    parsed = _parse_protocol(body.path)
    return {
        "title": parsed.title,
        "steps": parsed.steps,
        "step_count": len(parsed.steps),
        "source_filename": parsed.source_filename,
    }


@router.post("/protocol/commit")
def protocol_commit(
    body: ProtocolCommitRequest, sess: security.Session = Depends(current_session)
):
    parsed = _parse_protocol(body.path)
    parsed.source_filename = os.path.basename(body.path)
    parsed.title = body.title or parsed.title
    parsed.version = body.version or None
    ext = os.path.splitext(body.path)[1].lower()
    with open(body.path, "rb") as fh:
        parsed.file_data = fh.read()
    parsed.file_mime = files._MIME_BY_EXT.get(ext, "application/octet-stream")
    with db_lock(sess) as conn:
        pid = importers.import_protocol(conn, parsed, tags=body.tags or None)
    return {"id": pid, "title": parsed.title}


# ── Excel / experiment import ─────────────────────────────────────────────────
@router.post("/excel/parse")
def excel_parse(
    body: ExcelParseRequest, sess: security.Session = Depends(current_session)
):
    try:
        return importers.parse_excel(body.path, sheet_name=body.sheet_name)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Could not read spreadsheet: {exc}")


@router.get("/task-fields")
def task_fields(sess: security.Session = Depends(current_session)):
    return importers.TASK_FIELDS


@router.post("/experiment/import")
def experiment_import(
    body: ExperimentImport, sess: security.Session = Depends(current_session)
):
    with db_lock(sess) as conn:
        xid = importers.import_experiment(
            conn,
            body.name,
            body.rows,
            body.mapping,
            description=body.description,
            planned_date=body.planned_date,
            source_filename=body.source_filename,
        )
    return {"id": xid, "rows": len(body.rows)}
