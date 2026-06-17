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
            "at rest. Install `sqlcipher3-wheels` (see README)."
        )


# ── Favorite folders (for the file browser) ──────────────────────────────────
def favorites() -> list[str]:
    return load_config().get("favorite_folders", [])


def add_favorite(path: str) -> None:
    cfg = load_config()
    favs = cfg.get("favorite_folders", [])
    if path and path not in favs:
        favs.append(path)
        cfg["favorite_folders"] = favs
        save_config(cfg)


def remove_favorite(path: str) -> None:
    cfg = load_config()
    favs = [p for p in cfg.get("favorite_folders", []) if p != path]
    cfg["favorite_folders"] = favs
    save_config(cfg)


# ── Reusable controlled-vocabulary multiselect with inline "add" ─────────────
def vocab_multiselect(conn, category: str, label: str, *, default=None, key: str):
    """Render a multiselect backed by a vocab category, with an add-new box.

    Returns the list of currently selected values.
    """
    from core import vocab

    options = vocab.list_terms(conn, category)
    default = [d for d in (default or []) if d in options]
    selected = st.multiselect(label, options, default=default, key=f"ms_{key}")

    cols = st.columns([0.75, 0.25])
    new_val = cols[0].text_input(
        f"Add to {label.lower()}", key=f"add_{key}", label_visibility="collapsed",
        placeholder=f"Add new {label.lower()}…",
    )
    if cols[1].button("➕ Add", key=f"addbtn_{key}") and new_val.strip():
        vocab.add_term(conn, category, new_val.strip())
        st.rerun()
    return selected
