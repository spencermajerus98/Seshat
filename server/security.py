"""In-memory session registry — the passphrase/connection never touch disk.

On unlock we open the encrypted database via :func:`core.db.connect` and keep
the live connection in a process-local dict keyed by a random opaque token. The
token is handed to the browser as an httponly, same-site cookie; subsequent
requests resolve their connection from it. Locking (or an idle timeout) closes
the connection and forgets the token. This mirrors the original Streamlit
posture where the key lived only in ``st.session_state`` (memory).

Single-user/localhost, so a plain dict guarded by a lock is sufficient. Each
session also owns a lock that handlers hold around DB work, since one SQLCipher
connection is shared across uvicorn's worker threads.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field

from core.db import Connection

COOKIE_NAME = "seshat_session"
# Auto-lock an idle notebook. Matches the "walk away from the lab PC" threat.
IDLE_TIMEOUT_SECONDS = 60 * 60


@dataclass
class Session:
    token: str
    conn: Connection
    db_path: str
    last_active: float = field(default_factory=time.monotonic)
    lock: threading.Lock = field(default_factory=threading.Lock)


_sessions: dict[str, Session] = {}
_registry_lock = threading.Lock()


def create(conn: Connection, db_path: str) -> str:
    token = secrets.token_urlsafe(32)
    with _registry_lock:
        _sessions[token] = Session(token=token, conn=conn, db_path=db_path)
    return token


def get(token: str | None) -> Session | None:
    """Return the live session for a token, or None if missing/expired."""
    if not token:
        return None
    with _registry_lock:
        sess = _sessions.get(token)
        if sess is None:
            return None
        if time.monotonic() - sess.last_active > IDLE_TIMEOUT_SECONDS:
            _drop_locked(token)
            return None
        sess.last_active = time.monotonic()
        return sess


def destroy(token: str | None) -> None:
    if not token:
        return
    with _registry_lock:
        _drop_locked(token)


def _drop_locked(token: str) -> None:
    """Remove and close a session. Caller holds ``_registry_lock``."""
    sess = _sessions.pop(token, None)
    if sess is not None:
        try:
            sess.conn.close()
        except Exception:  # noqa: BLE001 - closing is best-effort
            pass
