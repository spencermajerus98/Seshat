"""API-level tests for the FastAPI layer (auth gating + core flows)."""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A TestClient whose config points at a throwaway data dir."""
    import server.config as cfg

    monkeypatch.setattr(cfg, "CONFIG_PATH", str(tmp_path / "cfg.json"))
    monkeypatch.setattr(cfg, "DEFAULT_DB_PATH", str(tmp_path / "seshat.db"))
    monkeypatch.setattr(cfg, "DEFAULT_INBOX_DIR", str(tmp_path / "inbox"))

    from server.main import app

    return TestClient(app)


def unlock(client, passphrase="test-pass"):
    return client.post(
        "/api/auth/unlock", json={"passphrase": passphrase, "confirm": passphrase}
    )


def test_status_before_unlock(client):
    r = client.get("/api/auth/status")
    assert r.status_code == 200
    body = r.json()
    assert body["unlocked"] is False
    assert body["db_exists"] is False


def test_protected_route_requires_unlock(client):
    assert client.get("/api/dashboard").status_code == 401
    assert client.get("/api/experiments").status_code == 401


def test_unlock_sets_session_and_unlocks(client):
    r = unlock(client)
    assert r.status_code == 200
    assert r.json()["created"] is True
    assert client.get("/api/auth/status").json()["unlocked"] is True
    # Dashboard now reachable.
    assert client.get("/api/dashboard").status_code == 200


def test_wrong_passphrase_rejected(client):
    unlock(client, "right-pass")
    client.post("/api/auth/lock")
    r = client.post("/api/auth/unlock", json={"passphrase": "wrong-pass"})
    assert r.status_code == 401


def test_experiment_create_and_report(client):
    unlock(client)
    r = client.post(
        "/api/experiments",
        json={
            "name": "Lentiviral run",
            "start_date": "2026-06-18",
            "duration_days": 3,
            "setup_values": {},
            "status": "planned",
        },
    )
    assert r.status_code == 200
    eid = r.json()["id"]

    exps = client.get("/api/experiments").json()
    assert any(e["name"] == "Lentiviral run" and e["end_date"] == "2026-06-20" for e in exps)

    report = client.get(f"/api/experiments/{eid}/report").json()
    assert "Lentiviral run" in report["markdown"]
    assert "<h2>" in report["html"]


def test_notebook_entry_flows_into_summary(client):
    unlock(client)
    r = client.post(
        "/api/notebook/entries",
        json={"text": "Observed colony growth", "entry_type": "observation"},
    )
    assert r.status_code == 200
    summary = client.get("/api/summary").json()
    assert "Observed colony growth" in summary["text"]

    entries = client.get("/api/notebook/entries").json()
    assert entries[0]["text"] == "Observed colony growth"


def test_empty_entry_rejected(client):
    unlock(client)
    assert client.post("/api/notebook/entries", json={"text": "   "}).status_code == 400


def test_lock_clears_session(client):
    unlock(client)
    assert client.post("/api/auth/lock").status_code == 200
    assert client.get("/api/dashboard").status_code == 401


def test_meta_and_types_available(client):
    unlock(client)
    meta = client.get("/api/meta").json()
    assert "note" in meta["entry_types"]
    types = client.get("/api/types").json()
    assert any(t["name"] == "Generic" for t in types)  # seeded default
