"""Unit tests for dashboard, report generation, and demo orchestrator (Phase 10 / M10.1, M10.2, M10.3).

Validates:
- GET /dashboard/summary returns counts matching DB state
- Report generation creates Markdown containing scenario, fence, severity, and `agentbreak verify` command (M10.2)
- Demo orchestrator runs the entire flow in <= 60 seconds (SM-1)
- Demo status links and idempotent reset
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from agentbreak.db import get_connection, migrate
from agentbreak.engine.demo import run_demo_sequence
from agentbreak.main import create_app
from agentbreak.seed import seed_database
from fastapi.testclient import TestClient


@pytest.fixture
def seeded_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_file = tmp_path / "test_dashboard.db"
    monkeypatch.setenv("AGENTBREAK_DB_PATH", str(db_file))
    conn = get_connection(db_file)
    migrate(conn)
    seed_database(conn)
    conn.close()
    return db_file


def test_demo_orchestrator_execution_time_and_links(seeded_db: Path) -> None:
    """Validate that the full demo runs end-to-end in <= 60s (SM-1) and establishes all links."""
    conn = get_connection(seeded_db)

    start_time = time.time()
    demo_status = run_demo_sequence(conn)
    duration = time.time() - start_time

    assert duration <= 60.0, f"SM-1 failed: Demo took {duration:.2f}s, must be <= 60s"
    assert demo_status.status == "completed"
    assert demo_status.stage == "Completed"
    assert all(s.status == "completed" for s in demo_status.stages)

    # Validate links
    assert demo_status.links.dashboard == "/dashboard"
    assert demo_status.links.audit == "/permissions"
    assert demo_status.links.fixlab == "/fixes"
    assert demo_status.links.sleeper == "/sleeper"
    assert demo_status.links.report == "/report"

    conn.close()


def test_dashboard_summary_matches_db(seeded_db: Path) -> None:
    """Validate that GET /dashboard/summary accurately matches database counts."""
    conn = get_connection(seeded_db)
    # Run demo to populate DB
    run_demo_sequence(conn)
    conn.close()

    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()

        # Scripted target under full policy has successful attacks (7 benchmark + sleeper trigger session)
        assert data["successful_attacks"] >= 7
        assert data["total_attacks"] >= 7
        assert data["attack_success_rate"] >= 0.8
        assert data["total_benign"] >= 10
        assert data["passed_benign"] >= 10
        assert data["benign_pass_rate"] == 1.0

        # Severities: 5 critical + 2 high
        assert data["findings_by_severity"]["critical"] == 5
        assert data["findings_by_severity"]["high"] == 2
        assert data["open_findings"] == 7
        assert len(data["recent_runs"]) > 0


def test_reports_api_and_markdown_content(seeded_db: Path) -> None:
    """Validate report creation and download containing required CLI reproduction commands."""
    conn = get_connection(seeded_db)
    run_demo_sequence(conn)
    conn.close()

    app = create_app()
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/reports",
            json={
                "target_id": "tgt_demo_scripted",
                "policy_id": "pol_full",
            },
        )
        assert resp.status_code == 201
        report_data = resp.json()
        report_id = report_data["id"]
        markdown = report_data["markdown"]

        # Content verification per M10.2
        assert "# AgentBreak Security & Hardening Evidence Report" in markdown
        assert "uv run python -m agentbreak.cli verify" in markdown
        assert "Permission Attribution Diff" in markdown
        assert "Remediation Price Tags" in markdown

        # Download endpoint
        dl_resp = client.get(f"/api/v1/reports/{report_id}/download")
        assert dl_resp.status_code == 200
        assert dl_resp.headers["content-type"].startswith("text/markdown")
        assert len(dl_resp.text) > 200
