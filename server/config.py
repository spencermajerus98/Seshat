"""Local, non-secret path configuration (mirrors the old ``ui_common``).

Only filesystem paths and the file-browser favourites live here — never the
passphrase or any decrypted data. Stored as plain JSON under ``data/`` so an
existing Seshat notebook keeps working unchanged after the rewrite.
"""

from __future__ import annotations

import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "seshat_config.json")
FRONTEND_DIST = os.path.join(PROJECT_ROOT, "frontend", "dist")

DEFAULT_DB_PATH = os.path.join(DATA_DIR, "seshat.db")
DEFAULT_INBOX_DIR = os.path.join(PROJECT_ROOT, "inbox")


def load_config() -> dict:
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


# ── File-browser favourites ──────────────────────────────────────────────────
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
    cfg["favorite_folders"] = [p for p in cfg.get("favorite_folders", []) if p != path]
    save_config(cfg)
