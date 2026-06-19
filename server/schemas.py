"""Pydantic request bodies. Responses are plain dicts from ``core`` (already
JSON-friendly), so only inputs need explicit schemas here."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class UnlockRequest(BaseModel):
    passphrase: str
    confirm: Optional[str] = None


class ChangePassphraseRequest(BaseModel):
    current: str
    new_passphrase: str
    confirm: str


class EntryCreate(BaseModel):
    text: str
    entry_type: str = "note"
    experiment_id: Optional[int] = None


class ExperimentPayload(BaseModel):
    name: str
    type_id: Optional[int] = None
    start_date: Optional[str] = None
    duration_days: Optional[int] = None
    protocol_id: Optional[int] = None
    setup_values: dict[str, Any] = {}
    description: Optional[str] = None
    status: str = "planned"


class TaskCreate(BaseModel):
    task_name: str
    planned_date: Optional[str] = None


class TaskStatus(BaseModel):
    status: str


class TypeCreate(BaseModel):
    name: str


class TypeFieldsUpdate(BaseModel):
    fields: list[dict[str, Any]]


class VocabTerm(BaseModel):
    category: str
    value: str


class ListDirRequest(BaseModel):
    path: str


class FavoriteRequest(BaseModel):
    path: str


class ProtocolImportFile(BaseModel):
    path: str
    tags: Optional[str] = None


class ExcelParseRequest(BaseModel):
    path: str
    sheet_name: Optional[str] = None


class ExperimentImport(BaseModel):
    name: str
    rows: list[dict[str, Any]]
    mapping: dict[str, Optional[str]]
    description: Optional[str] = None
    source_filename: Optional[str] = None
    planned_date: Optional[str] = None


class SettingsPaths(BaseModel):
    db_path: str
    inbox_dir: str
