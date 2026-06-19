"""Experiment types, their field templates, and controlled vocabularies."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from core import exp_types, vocab
from core.exp_types import VALID_KINDS
from core.models import ENTRY_TYPE_LABELS, ENTRY_TYPES

from .. import security
from ..deps import current_session, db as db_lock
from ..schemas import TypeCreate, TypeFieldsUpdate, VocabTerm

router = APIRouter(prefix="/api", tags=["exp_meta"])

STATUSES = ["planned", "active", "done", "abandoned"]


@router.get("/meta")
def meta():
    """Static UI constants, so the frontend stays in sync with ``core``."""
    return {
        "entry_types": ENTRY_TYPES,
        "entry_type_labels": ENTRY_TYPE_LABELS,
        "statuses": STATUSES,
        "field_kinds": VALID_KINDS,
        "vocab_categories": vocab.CATEGORIES,
        "vocab_category_labels": vocab.CATEGORY_LABELS,
    }


# ── Experiment types ──────────────────────────────────────────────────────────
@router.get("/types")
def list_types(sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        return exp_types.list_types(conn)


@router.post("/types")
def create_type(body: TypeCreate, sess: security.Session = Depends(current_session)):
    if not body.name.strip():
        raise HTTPException(400, "Type name is required.")
    with db_lock(sess) as conn:
        tid = exp_types.create_type(conn, body.name.strip())
    return {"id": tid}


@router.put("/types/{type_id}/fields")
def update_type_fields(
    type_id: int,
    body: TypeFieldsUpdate,
    sess: security.Session = Depends(current_session),
):
    # Normalise like the old data-editor save: drop blank-label rows, auto-key.
    fields = []
    for row in body.fields:
        label = (row.get("label") or "").strip()
        if not label:
            continue
        key = (row.get("key") or "").strip() or exp_types.slugify(label)
        f = {"key": key, "label": label, "kind": row.get("kind") or "text"}
        if row.get("vocab"):
            f["vocab"] = row["vocab"]
        fields.append(f)
    with db_lock(sess) as conn:
        exp_types.update_type_fields(conn, type_id, fields)
    return {"ok": True, "fields": fields}


# ── Controlled vocabularies ───────────────────────────────────────────────────
@router.get("/vocab/{category}")
def list_terms(category: str, sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        return vocab.list_terms(conn, category)


@router.post("/vocab")
def add_term(body: VocabTerm, sess: security.Session = Depends(current_session)):
    with db_lock(sess) as conn:
        vocab.add_term(conn, body.category, body.value)
    return {"ok": True}


@router.delete("/vocab")
def delete_term(
    category: str, value: str, sess: security.Session = Depends(current_session)
):
    with db_lock(sess) as conn:
        vocab.delete_term(conn, category, value)
    return {"ok": True}
