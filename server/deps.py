"""Request dependencies — resolve the unlocked session from the cookie."""

from __future__ import annotations

from contextlib import contextmanager

from fastapi import Cookie, HTTPException, status

from . import security


def current_session(
    seshat_session: str | None = Cookie(default=None),
) -> security.Session:
    """FastAPI dependency: the live session, or 401 if locked/expired."""
    sess = security.get(seshat_session)
    if sess is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Notebook is locked."
        )
    return sess


@contextmanager
def db(sess: security.Session):
    """Serialise access to the session's shared SQLCipher connection."""
    with sess.lock:
        yield sess.conn
