"""Settings — folder paths, database backup, and full notebook export."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from core import db, notebook

from .. import config, security
from ..deps import current_session, db as db_lock
from ..schemas import SettingsPaths

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings(sess: security.Session = Depends(current_session)):
    return {
        "db_path": config.db_path(),
        "inbox_dir": config.inbox_dir(),
        "encryption": db.ENCRYPTION_AVAILABLE,
        "db_exists": os.path.exists(config.db_path()),
    }


@router.put("")
def save_settings(body: SettingsPaths, sess: security.Session = Depends(current_session)):
    cfg = config.load_config()
    cfg["db_path"] = body.db_path
    cfg["inbox_dir"] = body.inbox_dir
    config.save_config(cfg)
    return {"ok": True}


@router.get("/backup")
def backup(sess: security.Session = Depends(current_session)):
    path = config.db_path()
    if not os.path.exists(path):
        raise HTTPException(404, "No database file to back up.")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=os.path.basename(path),
    )


@router.get("/export", response_class=PlainTextResponse)
def export(sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        entries = notebook.list_entries(conn, limit=100000)
    lines = ["# Seshat notebook export\n"]
    for e in reversed(entries):
        exp = f" [{e['experiment_name']}]" if e["experiment_name"] else ""
        lines.append(
            f"- **{e['created_at']}** ({e['entry_type']}{exp}, {e['source']}): {e['text']}"
        )
    return "\n".join(lines)
