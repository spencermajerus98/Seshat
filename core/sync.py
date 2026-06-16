"""Phone-note ingestion from a Syncthing-synced inbox folder.

You dictate (Wispr Flow / native dictation) or type a note on your phone and
save it as a ``.txt`` / ``.md`` file inside a folder that Syncthing keeps in
sync with the lab PC, peer-to-peer and end-to-end encrypted — no cloud.
:func:`scan_inbox` reads each new file, creates a timestamped notebook entry
(``source='phone'``) and moves the file into ``processed/`` so it is never
ingested twice.

Optional first-line markers a note may begin with (any order, each on its own
line at the very top):

    [ts: 2026-06-16T14:30:00]   explicit timestamp (else the file's mtime is used)
    #exp: CRISPR knock-in        link the note to an experiment by name
    #type: observation           entry type (note/observation/result/deviation/task_done)
"""

from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from typing import Optional

from .db import Connection
from .models import ENTRY_TYPES
from .notebook import TS_FMT, add_entry

TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
PROCESSED_DIRNAME = "processed"

_TS_MARKER = re.compile(r"^\s*\[ts:\s*(.+?)\s*\]\s*$", re.IGNORECASE)
_EXP_MARKER = re.compile(r"^\s*#exp:\s*(.+?)\s*$", re.IGNORECASE)
_TYPE_MARKER = re.compile(r"^\s*#type:\s*(\w+)\s*$", re.IGNORECASE)


def _parse_ts(raw: str) -> Optional[str]:
    """Normalise a user-supplied timestamp to the stored format, or None."""
    raw = raw.strip().replace("Z", "")
    for fmt in (TS_FMT, "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime(TS_FMT)
        except ValueError:
            continue
    return None


def _parse_note(text: str) -> tuple[str, Optional[str], Optional[str], str]:
    """Split leading markers from body. Returns (body, ts, exp_name, entry_type)."""
    ts: Optional[str] = None
    exp_name: Optional[str] = None
    entry_type = "note"

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() and i == 0:
            i += 1
            continue
        if m := _TS_MARKER.match(line):
            ts = _parse_ts(m.group(1))
        elif m := _EXP_MARKER.match(line):
            exp_name = m.group(1).strip()
        elif m := _TYPE_MARKER.match(line):
            t = m.group(1).lower()
            entry_type = t if t in ENTRY_TYPES else "note"
        else:
            break
        i += 1

    body = "\n".join(lines[i:]).strip()
    return body, ts, exp_name, entry_type


def _lookup_experiment(conn: Connection, name: str) -> Optional[int]:
    row = conn.execute(
        "SELECT id FROM experiments WHERE lower(name) = lower(?) ORDER BY id DESC LIMIT 1",
        (name,),
    ).fetchone()
    return int(row[0]) if row else None


def scan_inbox(conn: Connection, inbox_dir: str) -> list[dict]:
    """Ingest all new text notes from ``inbox_dir``.

    Returns a list of dicts describing what was ingested:
    ``{"file": name, "entry_id": int, "created_at": ts}``.
    """
    if not inbox_dir or not os.path.isdir(inbox_dir):
        return []

    processed_dir = os.path.join(inbox_dir, PROCESSED_DIRNAME)
    os.makedirs(processed_dir, exist_ok=True)

    ingested: list[dict] = []
    for name in sorted(os.listdir(inbox_dir)):
        path = os.path.join(inbox_dir, name)
        if not os.path.isfile(path):
            continue
        if os.path.splitext(name)[1].lower() not in TEXT_EXTENSIONS:
            continue

        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()

        body, ts, exp_name, entry_type = _parse_note(raw)
        if not body:
            # Nothing usable; still move it aside so it isn't rescanned forever.
            shutil.move(path, _unique_dest(processed_dir, name))
            continue

        created_at = ts or datetime.fromtimestamp(os.path.getmtime(path)).strftime(TS_FMT)
        experiment_id = _lookup_experiment(conn, exp_name) if exp_name else None

        entry_id = add_entry(
            conn,
            body,
            entry_type=entry_type,
            source="phone",
            experiment_id=experiment_id,
            created_at=created_at,
            metadata={"source_file": name, "exp_marker": exp_name},
        )
        shutil.move(path, _unique_dest(processed_dir, name))
        ingested.append({"file": name, "entry_id": entry_id, "created_at": created_at})

    return ingested


def _unique_dest(directory: str, name: str) -> str:
    """Avoid clobbering when a filename repeats."""
    dest = os.path.join(directory, name)
    if not os.path.exists(dest):
        return dest
    stem, ext = os.path.splitext(name)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return os.path.join(directory, f"{stem}_{stamp}{ext}")


def count_pending(inbox_dir: str) -> int:
    """How many unprocessed note files are waiting in the inbox."""
    if not inbox_dir or not os.path.isdir(inbox_dir):
        return 0
    return sum(
        1
        for n in os.listdir(inbox_dir)
        if os.path.isfile(os.path.join(inbox_dir, n))
        and os.path.splitext(n)[1].lower() in TEXT_EXTENSIONS
    )
