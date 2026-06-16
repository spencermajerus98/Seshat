"""Lightweight value objects and shared constants.

The data layer mostly returns ``sqlite3.Row`` objects (dict-like). These
dataclasses are used where a typed, explicit shape aids readability/tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Notebook entry kinds. Kept small and stable; surfaced in the UI.
ENTRY_TYPES = ["note", "task_done", "observation", "result", "deviation"]
ENTRY_TYPE_LABELS = {
    "note": "📝 Note",
    "task_done": "✅ Task done",
    "observation": "🔬 Observation",
    "result": "📊 Result",
    "deviation": "⚠️ Deviation",
}

SOURCES = ["app", "phone"]


@dataclass
class NotebookEntry:
    id: Optional[int]
    created_at: str
    entry_type: str
    source: str
    text: str
    experiment_id: Optional[int] = None
    protocol_id: Optional[int] = None
    metadata_json: Optional[str] = None


@dataclass
class ParsedProtocol:
    title: str
    body_text: str
    steps: list[str] = field(default_factory=list)
    source_filename: Optional[str] = None
    version: Optional[str] = None
