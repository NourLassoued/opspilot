"""Tests de l'API HTTP de l'agent (sans cluster ni LLM)."""
from fastapi.testclient import TestClient

from opspilot_agent import actions, api

client = TestClient(api.app)
BODY = {"remediation": {"action": "git_revert", "commit_sha": "7117d0b", "explanation": "test"}}


def test_remediate_refuses_missing_or_wrong_token(monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "secret-du-backend")
    assert client.post("/remediate", json=BODY).status_code == 401
    assert client.post("/remediate", json=BODY, headers={"Authorization": "Bearer faux"}).status_code == 401


def test_remediate_refuses_when_no_token_configured(monkeypatch):
    monkeypatch.delenv("AGENT_API_TOKEN", raising=False)
    assert client.post("/remediate", json=BODY, headers={"Authorization": "Bearer "}).status_code == 401


def test_remediate_executes_with_valid_token(monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "secret-du-backend")
    monkeypatch.setattr(actions, "execute", lambda r: f"revert {r.commit_sha} ok")
    resp = client.post("/remediate", json=BODY, headers={"Authorization": "Bearer secret-du-backend"})
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "message": "revert 7117d0b ok"}


def test_remediate_reports_failure_without_crashing(monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "secret-du-backend")

    def boom(r):
        raise RuntimeError("push refusé")

    monkeypatch.setattr(actions, "execute", boom)
    resp = client.post("/remediate", json=BODY, headers={"Authorization": "Bearer secret-du-backend"})
    assert resp.json() == {"success": False, "message": "push refusé"}
