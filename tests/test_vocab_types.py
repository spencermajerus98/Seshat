"""Tests for controlled vocabularies and modular experiment types."""

from core import exp_types, vocab


def test_vocab_add_list_delete(conn):
    vocab.add_term(conn, "vector", "Sendai")
    vocab.add_term(conn, "vector", "Sendai")  # duplicate ignored
    terms = vocab.list_terms(conn, "vector")
    assert terms.count("Sendai") == 1
    vocab.delete_term(conn, "vector", "Sendai")
    assert "Sendai" not in vocab.list_terms(conn, "vector")


def test_default_type_seeded(conn):
    t = exp_types.get_type_by_name(conn, "Generic")
    assert t is not None
    keys = {f["key"] for f in t["fields"]}
    assert {"vectors", "cells", "reagents", "protocol"} <= keys


def test_create_type_idempotent_and_update(conn):
    a = exp_types.create_type(conn, "CRISPR knock-in")
    b = exp_types.create_type(conn, "crispr knock-in")  # same name, case-insensitive
    assert a == b
    exp_types.update_type_fields(
        conn, a, [{"key": "guide", "label": "Guide RNA", "kind": "text"}]
    )
    t = exp_types.get_type(conn, a)
    assert t["fields"] == [{"key": "guide", "label": "Guide RNA", "kind": "text"}]


def test_slugify():
    assert exp_types.slugify("Guide RNA!") == "guide_rna"
    assert exp_types.slugify("  ") == "field"
