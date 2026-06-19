"""Database layer for Seshat.

Primary backend is **SQLCipher** (encrypted-at-rest) via the ``sqlcipher3``
module. If that module is unavailable, Seshat transparently falls back to the
standard-library ``sqlite3`` driver with **no encryption** and exposes
``ENCRYPTION_AVAILABLE = False`` so the UI can warn the user.

Either way a passphrase is required to open the notebook: in encrypted mode the
passphrase is the SQLCipher key; in fallback mode it is checked against a
PBKDF2 verifier stored in the ``meta`` table.
"""

from __future__ import annotations

import os
from typing import Optional

from . import crypto

# ── Backend selection ──────────────────────────────────────────────────────
try:  # pragma: no cover - import path depends on environment
    from sqlcipher3 import dbapi2 as _backend  # type: ignore

    ENCRYPTION_AVAILABLE = True
except Exception:  # noqa: BLE001 - any import failure -> fallback
    import sqlite3 as _backend  # type: ignore

    ENCRYPTION_AVAILABLE = False

Connection = _backend.Connection
Row = _backend.Row
DatabaseError = _backend.DatabaseError


class BadPassphrase(Exception):
    """Raised when the supplied passphrase cannot open the database."""


# ── Schema ──────────────────────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS protocols (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    source_filename TEXT,
    version         TEXT,
    imported_at     TEXT NOT NULL,
    body_text       TEXT,
    tags            TEXT
);

CREATE TABLE IF NOT EXISTS protocol_steps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_id INTEGER NOT NULL REFERENCES protocols(id) ON DELETE CASCADE,
    step_no     INTEGER NOT NULL,
    text        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    description     TEXT,
    planned_date    TEXT,
    status          TEXT DEFAULT 'planned',
    source_filename TEXT,
    imported_at     TEXT NOT NULL,
    metadata_json   TEXT
);

CREATE TABLE IF NOT EXISTS experiment_tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    task_name     TEXT NOT NULL,
    planned_date  TEXT,
    sample        TEXT,
    reagent       TEXT,
    notes         TEXT,
    status        TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS notebook_entries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    entry_type    TEXT NOT NULL DEFAULT 'note',
    source        TEXT NOT NULL DEFAULT 'app',
    experiment_id INTEGER REFERENCES experiments(id) ON DELETE SET NULL,
    protocol_id   INTEGER REFERENCES protocols(id) ON DELETE SET NULL,
    text          TEXT NOT NULL,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS experiment_types (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    fields_json TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vocab_terms (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    value    TEXT NOT NULL,
    UNIQUE(category, value)
);

CREATE INDEX IF NOT EXISTS idx_entries_created ON notebook_entries(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_date ON experiment_tasks(planned_date);
CREATE INDEX IF NOT EXISTS idx_vocab_category ON vocab_terms(category);
"""

# Columns added to `experiments` after the original MVP schema. Applied
# idempotently by _run_migrations() so existing notebooks upgrade in place.
_EXPERIMENT_COLUMNS_V2 = {
    "type_id": "INTEGER",
    "start_date": "TEXT",
    "end_date": "TEXT",
    "duration_days": "INTEGER",
    "protocol_id": "INTEGER",
    "setup_json": "TEXT",
}

# Columns added to `protocols` to store the original file bytes for the viewer.
_PROTOCOL_COLUMNS_V2 = {
    "file_data": "BLOB",
    "file_mime": "TEXT",
}


def _apply_key(conn: Connection, passphrase: str) -> None:
    """Set the SQLCipher key on a freshly opened encrypted connection."""
    escaped = passphrase.replace("'", "''")
    conn.execute(f"PRAGMA key = '{escaped}'")
    # Sensible, modern SQLCipher defaults; explicit for reproducibility.
    conn.execute("PRAGMA cipher_page_size = 4096")
    conn.execute("PRAGMA kdf_iter = 256000")


def _probe(conn: Connection) -> None:
    """Touch the database; raises if the key/passphrase is wrong."""
    conn.execute("SELECT count(*) FROM sqlite_master").fetchone()


def get_meta(conn: Connection, key: str) -> Optional[str]:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def set_meta(conn: Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


def _column_names(conn: Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _run_migrations(conn: Connection) -> None:
    """Apply additive schema changes to an existing database, idempotently."""
    existing_exp = _column_names(conn, "experiments")
    for col, decl in _EXPERIMENT_COLUMNS_V2.items():
        if col not in existing_exp:
            conn.execute(f"ALTER TABLE experiments ADD COLUMN {col} {decl}")

    existing_proto = _column_names(conn, "protocols")
    for col, decl in _PROTOCOL_COLUMNS_V2.items():
        if col not in existing_proto:
            conn.execute(f"ALTER TABLE protocols ADD COLUMN {col} {decl}")

    conn.commit()


def _ensure_verifier(conn: Connection, passphrase: str) -> None:
    """Create or check the passphrase verifier stored inside the DB."""
    salt = get_meta(conn, "pass_salt")
    stored = get_meta(conn, "pass_verifier")
    if salt is None or stored is None:
        salt = crypto.new_salt()
        set_meta(conn, "pass_salt", salt)
        set_meta(conn, "pass_verifier", crypto.derive_verifier(passphrase, salt))
        return
    if not crypto.verify(passphrase, salt, stored):
        raise BadPassphrase("Incorrect passphrase.")


def connect(db_path: str, passphrase: str) -> Connection:
    """Open (creating if needed) the encrypted notebook database.

    Raises :class:`BadPassphrase` if the passphrase does not match an
    existing database.
    """
    if not passphrase:
        raise BadPassphrase("A passphrase is required.")

    parent = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(parent, exist_ok=True)

    conn = _backend.connect(db_path, check_same_thread=False)
    conn.row_factory = Row

    if ENCRYPTION_AVAILABLE:
        _apply_key(conn, passphrase)
        try:
            _probe(conn)
        except DatabaseError as exc:  # wrong key on an existing encrypted file
            conn.close()
            raise BadPassphrase("Incorrect passphrase.") from exc

    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    _run_migrations(conn)

    _ensure_verifier(conn, passphrase)

    # Seed default experiment type + controlled-vocabulary terms on first use.
    # Lazy import avoids a circular dependency (seed -> vocab/exp_types -> db).
    from . import seed

    seed.seed_defaults(conn)
    return conn


def change_passphrase(conn: Connection, db_path: str, new_passphrase: str) -> None:
    """Re-key the database (encrypted mode) and refresh the verifier."""
    if not new_passphrase:
        raise BadPassphrase("A passphrase is required.")
    if ENCRYPTION_AVAILABLE:
        escaped = new_passphrase.replace("'", "''")
        conn.execute(f"PRAGMA rekey = '{escaped}'")
    salt = crypto.new_salt()
    set_meta(conn, "pass_salt", salt)
    set_meta(conn, "pass_verifier", crypto.derive_verifier(new_passphrase, salt))
