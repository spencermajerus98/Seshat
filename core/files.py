"""Local file-system browser and import dispatch.

Seshat acts as a wrapper around the user's own folders: browse directories,
then pull supported files straight into the protocol/experiment database. This
module is pure filesystem + dispatch logic (no Streamlit) so it is testable.
"""

from __future__ import annotations

import os
from typing import Optional

from . import importers
from .db import Connection

# Extensions the browser recognises.
PROTOCOL_EXTENSIONS = {".docx", ".pdf", ".txt", ".md", ".markdown"}
EXPERIMENT_EXTENSIONS = {".xlsx"}
SUPPORTED_EXTENSIONS = PROTOCOL_EXTENSIONS | EXPERIMENT_EXTENSIONS


def default_roots() -> list[tuple[str, str]]:
    """Convenient starting folders. Returns [(label, path)] for existing dirs."""
    home = os.path.expanduser("~")
    candidates = [
        ("Home", home),
        ("Desktop", os.path.join(home, "Desktop")),
        ("Documents", os.path.join(home, "Documents")),
        ("Downloads", os.path.join(home, "Downloads")),
    ]
    if os.name == "nt":  # Windows drive letters
        import string

        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                candidates.append((drive, drive))

    seen, roots = set(), []
    for label, path in candidates:
        if path not in seen and os.path.isdir(path):
            seen.add(path)
            roots.append((label, path))
    return roots


def list_dir(path: str) -> dict:
    """Return subdirectories and supported files within ``path``.

    Shape: ``{"path", "parent", "dirs": [(name, path)], "files": [{...}]}``.
    Hidden entries (leading dot) and unreadable items are skipped.
    """
    path = os.path.abspath(path)
    parent = os.path.dirname(path)
    if parent == path:  # filesystem root
        parent = None

    dirs: list[tuple[str, str]] = []
    files: list[dict] = []
    try:
        entries = sorted(os.listdir(path), key=str.lower)
    except (PermissionError, FileNotFoundError, NotADirectoryError):
        entries = []

    for name in entries:
        if name.startswith("."):
            continue
        full = os.path.join(path, name)
        try:
            if os.path.isdir(full):
                dirs.append((name, full))
            elif os.path.isfile(full):
                ext = os.path.splitext(name)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append(
                        {
                            "name": name,
                            "path": full,
                            "ext": ext,
                            "size": os.path.getsize(full),
                            "is_experiment": ext in EXPERIMENT_EXTENSIONS,
                        }
                    )
        except OSError:
            continue

    return {"path": path, "parent": parent, "dirs": dirs, "files": files}


def import_protocol_file(
    conn: Connection, path: str, *, tags: Optional[str] = None
) -> int:
    """Parse a protocol file (docx/pdf/txt/md) and persist it. Returns its id."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        parsed = importers.parse_word(path)
    elif ext == ".pdf":
        parsed = importers.parse_pdf(path)
    elif ext in {".txt", ".md", ".markdown"}:
        parsed = importers.parse_text(path)
    else:
        raise ValueError(f"Unsupported protocol file type: {ext}")
    parsed.source_filename = os.path.basename(path)
    return importers.import_protocol(conn, parsed, tags=tags)
