"""Unlock / lock / status and passphrase change."""

from __future__ import annotations

import os

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response

from core import crypto, db, sync

from .. import config, security
from ..deps import current_session, db as db_lock
from ..schemas import ChangePassphraseRequest, UnlockRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_cookie(response: Response, token: str) -> None:
    # httponly + strict same-site; no Secure flag because this is plain-http
    # localhost. The cookie is an opaque session id, not the passphrase.
    response.set_cookie(
        security.COOKIE_NAME,
        token,
        httponly=True,
        samesite="strict",
        path="/",
    )


@router.get("/status")
def get_status(seshat_session: str | None = Cookie(default=None)):
    """Whether a notebook exists on disk and whether this session is unlocked."""
    return {
        "unlocked": security.get(seshat_session) is not None,
        "encryption": db.ENCRYPTION_AVAILABLE,
        "db_exists": os.path.exists(config.db_path()),
    }


@router.post("/unlock")
def unlock(body: UnlockRequest, response: Response):
    path = config.db_path()
    existing = os.path.exists(path)
    if not body.passphrase:
        raise HTTPException(400, "A passphrase is required.")
    if not existing and body.confirm is not None and body.passphrase != body.confirm:
        raise HTTPException(400, "Passphrases do not match.")

    try:
        conn = db.connect(path, body.passphrase)
    except db.BadPassphrase:
        raise HTTPException(401, "Incorrect passphrase.")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Could not open the notebook: {exc}")

    token = security.create(conn, path)
    _set_cookie(response, token)

    # Pull in any phone notes waiting in the synced inbox (never block unlock).
    ingested = 0
    try:
        ingested = len(sync.scan_inbox(conn, config.inbox_dir()))
    except Exception:  # noqa: BLE001
        pass

    return {
        "ok": True,
        "created": not existing,
        "encryption": db.ENCRYPTION_AVAILABLE,
        "ingested": ingested,
    }


@router.post("/lock")
def lock(response: Response, seshat_session: str | None = Cookie(default=None)):
    security.destroy(seshat_session)
    response.delete_cookie(security.COOKIE_NAME, path="/")
    return {"ok": True}


@router.post("/passphrase")
def change_passphrase(
    body: ChangePassphraseRequest, sess: security.Session = Depends(current_session)
):
    with db_lock(sess) as conn:
        salt = db.get_meta(conn, "pass_salt")
        verifier = db.get_meta(conn, "pass_verifier")
        if not (salt and verifier and crypto.verify(body.current, salt, verifier)):
            raise HTTPException(400, "Current passphrase is incorrect.")
        if not body.new_passphrase:
            raise HTTPException(400, "New passphrase cannot be empty.")
        if body.new_passphrase != body.confirm:
            raise HTTPException(400, "New passphrases do not match.")
        db.change_passphrase(conn, sess.db_path, body.new_passphrase)
    return {"ok": True}
