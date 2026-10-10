"""Unit tests for targets, suites, and policies API endpoints."""

from __future__ import annotations

import pytest
from agentbreak.api.deps import get_db
from agentbreak.db import get_connection, migrate
from agentbreak.main import app
from agentbreak.seed import seed_database
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: pytest.TempPathFactory) -> TestClient:
    db_file = tmp_path / "test_api.db"
    conn = get_connection(db_file)
    migrate(conn)
    seed_database(conn)
    conn.close()

    def override_get_db():
        test_conn = get_connection(db_file)
        try:
            yield test_conn
        finally:
            test_conn.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def test_list_targets_seeded(client: TestClient) -> None:
    resp = client.get("/api/v1/targets")
    assert resp.status_code == 200
    targets = resp.json()
    assert len(targets) >= 1
    ids = [t["id"] for t in targets]
    assert "tgt_demo_scripted" in ids


def test_create_and_get_target(client: TestClient) -> None:
    payload = {
        "name": "Custom Ollama Target",
        "kind": "openai_compat",
        "config": {
            "base_url": "http://localhost:11434/v1",
            "model": "llama3.1",
        },
    }
    create_resp = client.post("/api/v1/targets", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["id"].startswith("tgt_")
    assert created["name"] == "Custom Ollama Target"

    get_resp = client.get(f"/api/v1/targets/{created['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == created["id"]


def test_test_target_scripted(client: TestClient) -> None:
    resp = client.post("/api/v1/targets/tgt_demo_scripted/test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reachable"] is True
    assert data["tool_calling"] is True
    assert "Scripted" in data["notes"] or "scripted" in data["notes"]


def test_test_target_dead_url_fails_fast(client: TestClient) -> None:
    payload = {
        "name": "Dead Target",
        "kind": "openai_compat",
        "config": {
            "base_url": "http://127.0.0.1:59998/v1",
            "model": "non-existent",
        },
    }
    create_resp = client.post("/api/v1/targets", json=payload)
    target_id = create_resp.json()["id"]

    test_resp = client.post(f"/api/v1/targets/{target_id}/test")
    assert test_resp.status_code == 200
    data = test_resp.json()
    assert data["reachable"] is False
    assert data["tool_calling"] is False


def test_suite_acme_info(client: TestClient) -> None:
    resp = client.get("/api/v1/suites/acme")
    assert resp.status_code == 200
    suite = resp.json()
    assert suite["name"] == "acme"
    assert suite["persona"] == "alex@acme.test"
    assert len(suite["tools"]) == 10
    assert len(suite["benign_tasks"]) == 10
    assert len(suite["injection_tasks"]) == 5
    assert sorted(suite["vectors"]) == ["inj_doc_content", "inj_email_body"]


def test_scenarios_and_attack_cases(client: TestClient) -> None:
    scenarios_resp = client.get("/api/v1/scenarios")
    assert scenarios_resp.status_code == 200
    scenarios = scenarios_resp.json()
    assert len(scenarios) == 4
    scenario_ids = [s["id"] for s in scenarios]
    assert "ipi-exfil" in scenario_ids
    assert "malicious-doc" in scenario_ids
    assert "sleeper-memory" in scenario_ids
    assert "priv-esc" in scenario_ids

    cases_resp = client.get("/api/v1/attack-cases")
    assert cases_resp.status_code == 200
    cases = cases_resp.json()
    assert len(cases) == 7
    case_ids = [c["id"] for c in cases]
    assert case_ids == ["AS-01", "AS-02", "AS-03", "AS-04", "AS-05", "AS-06", "AS-07"]


def test_policies_api_and_diff(client: TestClient) -> None:
    list_resp = client.get("/api/v1/policies")
    assert list_resp.status_code == 200
    policies = list_resp.json()
    p_ids = [p["id"] for p in policies]
    assert "pol_full" in p_ids
    assert "pol_needed" in p_ids

    diff_resp = client.get("/api/v1/policies/pol_needed/diff/pol_full")
    assert diff_resp.status_code == 200
    diff = diff_resp.json()
    assert sorted(diff["added_tools"]) == ["delete_file", "set_role"]
    assert diff["removed_tools"] == []
