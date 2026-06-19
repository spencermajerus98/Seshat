"""Phone-note sync (Syncthing inbox ingestion)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends

from core import notebook, sync

from .. import config, security
from ..deps import current_session, db as db_lock

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.get("")
def status(sess: security.Session = Depends(current_session)):
    inbox = config.inbox_dir()
    os.makedirs(inbox, exist_ok=True)
    with db_lock(sess) as conn:
        recent = notebook.list_entries(conn, source="phone", limit=25)
    return {
        "inbox": inbox,
        "pending": sync.count_pending(inbox),
        "recent": recent,
    }


@router.post("/scan")
def scan(sess: security.Session = Depends(current_session)):
    inbox = config.inbox_dir()
    os.makedirs(inbox, exist_ok=True)
    with db_lock(sess) as conn:
        ingested = sync.scan_inbox(conn, inbox)
    return {"ingested": ingested}
