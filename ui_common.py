"""Shared Streamlit helpers used by app.py and every page.

Keeps the unlock state, database connection and local (non-secret) path
configuration in one place. The passphrase/connection live only in
``st.session_state`` — i.e. in memory — and are never written to disk.
"""

from __future__ import annotations

import json
import os

import streamlit as st

from core import db

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "seshat_config.json")

DEFAULT_DB_PATH = os.path.join(DATA_DIR, "seshat.db")
DEFAULT_INBOX_DIR = os.path.join(PROJECT_ROOT, "inbox")


def load_config() -> dict:
    """Load non-secret local config (paths only)."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)


def db_path() -> str:
    return load_config().get("db_path", DEFAULT_DB_PATH)


def inbox_dir() -> str:
    return load_config().get("inbox_dir", DEFAULT_INBOX_DIR)


def is_unlocked() -> bool:
    return st.session_state.get("conn") is not None


def get_conn() -> "db.Connection":
    """Return the open connection, or stop the page if locked."""
    if not is_unlocked():
        st.warning("🔒 The notebook is locked. Open it from the **Seshat** home page first.")
        st.stop()
    return st.session_state["conn"]


def lock() -> None:
    conn = st.session_state.pop("conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass


def encryption_badge() -> None:
    """Render a sidebar badge reflecting the encryption status."""
    if db.ENCRYPTION_AVAILABLE:
        st.sidebar.success("🔐 Encrypted database (SQLCipher)")
    else:
        st.sidebar.error(
            "⚠️ Encryption backend not installed — data is **NOT** encrypted "
            "at rest. Install `sqlcipher3-binary` (see README)."
        )
