"""Protocols — list/search, steps, delete."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from .. import security
from ..deps import current_session, db as db_lock

router = APIRouter(prefix="/api/protocols", tags=["protocols"])


@router.get("")
def list_protocols(
    q: Optional[str] = None, sess: security.Session = Depends(current_session)
):
    with db_lock(sess) as conn:
        if q:
            like = f"%{q}%"
            rows = conn.execute(
                "SELECT * FROM protocols WHERE title LIKE ? OR body_text LIKE ? "
                "ORDER BY title COLLATE NOCASE",
                (like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM protocols ORDER BY title COLLATE NOCASE"
            ).fetchall()
        protocols = []
        for p in rows:
            steps = conn.execute(
                "SELECT step_no, text FROM protocol_steps WHERE protocol_id=? "
                "ORDER BY step_no",
                (p["id"],),
            ).fetchall()
            d = dict(p)
            d["steps"] = [dict(s) for s in steps]
            protocols.append(d)
    return protocols


@router.delete("/{protocol_id}")
def delete_protocol(protocol_id: int, sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        conn.execute("DELETE FROM protocols WHERE id=?", (protocol_id,))
        conn.commit()
    return {"ok": True}
