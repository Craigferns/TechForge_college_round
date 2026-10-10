"""End-to-end integration test driving the complete demo flow via API (PLAN.md M11.1 / SM-1, SM-6, SM-8)."""

from __future__ import annotations

import time

import pytest
from agentbreak.main import create_app
from fastapi.testclient import TestClient


@pytest.mark.e2e
def test_full_demo_flow_e2e() -> None:
    """E2E flow: POST /demo/run -> GET /demo/{id} -> GET /dashboard/summary -> GET /audits/{id} -> Fixlab."""
    with TestClient(create_app()) as client:
        _flow(client)


def _flow(client: TestClient) -> None:
    # 1. Health check
    h_resp = client.get("/api/v1/health")
    assert h_resp.status_code == 200
    assert h_resp.json()["status"] == "ok"

    # 2. Trigger demo run
    demo_resp = client.post("/api/v1/demo/run")
    assert demo_resp.status_code == 202
    demo_id = demo_resp.json()["id"]
    deadline = time.monotonic() + 120
    while (demo_data := client.get(f"/api/v1/demo/{demo_id}").json())["status"] in (
        "queued",
        "running",
    ):
        assert time.monotonic() < deadline, "demo did not finish"
        time.sleep(0.2)
    assert demo_data["status"] == "completed", demo_data.get("error")
    assert len(demo_data["stages"]) == 7
    links = demo_data["links"]
    assert client.get("/api/v1" + links["run"]).status_code == 200

    # 3. Dashboard = measured posture under the remediated active policy
    dash = client.get("/api/v1/dashboard/summary").json()
    assert dash["active_policy_id"] != "pol_full"
    assert (dash["successful_attacks"], dash["total_attacks"]) == (0, 7)
    assert (dash["passed_benign"], dash["total_benign"]) == (10, 10)
    assert dash["sleeper_outcome"] == "trigger_blocked"
    assert dash["fixes_applied"] == 4
    assert dash["open_findings"] == 0
    assert dash["findings_by_severity"]["critical"] == 5
    assert dash["findings_by_severity"]["high"] == 2

    # 4. Verify findings list
    findings_resp = client.get("/api/v1/findings")
    assert findings_resp.status_code == 200
    findings_data = findings_resp.json()
    assert findings_data["total"] == 7

    # 5. Verify aggregate graph
    graph_resp = client.get("/api/v1/graph")
    assert graph_resp.status_code == 200
    graph_data = graph_resp.json()
    assert len(graph_data["nodes"]) >= 3
    assert len(graph_data["edges"]) >= 2
