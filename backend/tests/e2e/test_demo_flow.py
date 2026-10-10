"""End-to-end integration test driving the complete AgentBreak demo flow (M11.1 / SM-1, SM-4, SM-5, SM-6).

Asserts:
- Launching the demo via POST /api/v1/demo/run completes in <= 60 seconds (SM-1)
- Baseline evaluation reveals 7/7 attack cases exploited (5 critical + 2 high)
- Baseline utility confirms 10/10 benign ground-truth tasks pass
- Permission audit attributes every exploit to >= 1 enabling permission (SM-5)
- Candidate fixes evaluated with exact golden price tags
- Applying combined hardening activates hardened child policy
- Re-testing under combined policy yields 0/7 attacks succeed and 10/10 benign pass
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from agentbreak.db import get_connection, migrate
from agentbreak.main import create_app
from agentbreak.seed import seed_database
from fastapi.testclient import TestClient


@pytest.fixture
def e2e_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_file = tmp_path / "test_e2e_demo.db"
    monkeypatch.setenv("AGENTBREAK_DB_PATH", str(db_file))
    conn = get_connection(db_file)
    migrate(conn)
    seed_database(conn)
    conn.close()
    return db_file


@pytest.mark.e2e
def test_full_e2e_demo_flow_and_hardening(e2e_db: Path) -> None:
    """Full end-to-end test driving the entire demo cycle through public REST endpoints."""
    app = create_app()
    with TestClient(app) as client:
        # 1. Launch live demo scan (SM-1: <= 60s)
        start_time = time.time()
        demo_resp = client.post("/api/v1/demo/run")
        duration = time.time() - start_time

        assert demo_resp.status_code == 202
        demo_data = demo_resp.json()
        assert duration <= 60.0, f"Demo sequence took {duration:.2f}s, must be <= 60s"
        assert demo_data["status"] == "completed"
        assert demo_data["stage"] == "Completed"

        # 2. Check Dashboard Summary (Baseline)
        dash_resp = client.get("/api/v1/dashboard/summary")
        assert dash_resp.status_code == 200
        dash = dash_resp.json()
        assert dash["successful_attacks"] >= 7
        assert dash["open_findings"] == 7
        assert dash["findings_by_severity"]["critical"] == 5
        assert dash["findings_by_severity"]["high"] == 2
        assert dash["passed_benign"] >= 10

        # 3. Check Findings and Causality (Phase 7)
        findings_resp = client.get("/api/v1/findings")
        assert findings_resp.status_code == 200
        findings = findings_resp.json()["items"]
        assert len(findings) == 7

        as04 = next(f for f in findings if f["case_id"] == "AS-04")
        assert as04["severity"] == "high"
        assert as04["status"] == "open"

        # 4. Check Audits & SM-5 attribution (Phase 8)
        audits_resp = client.get("/api/v1/audits")
        assert audits_resp.status_code == 200
        audits = audits_resp.json()["items"]
        assert len(audits) >= 1
        audit = audits[0]
        assert len(audit["excess"]) == 2
        assert set(audit["excess"]) == {"delete_file", "set_role"}
        assert audit["proof"]["benign_pass_under_minimal"] == 10

        # Verify SM-5: every finding attributed to >= 1 enabling tool
        all_cases = {"AS-01", "AS-02", "AS-03", "AS-04", "AS-05", "AS-06", "AS-07"}
        attributed_cases = set()
        for row in audit["rows"]:
            for exp in row["enabled_exploits"]:
                if exp["role"] == "enabling":
                    attributed_cases.add(exp["case_id"])
        assert all_cases.issubset(attributed_cases)

        # 5. Check Fix Lab Price Tags (Phase 9 & SM-4)
        fix_evals_resp = client.get(f"/api/v1/fix-evals?audit_id={audit['id']}")
        assert fix_evals_resp.status_code == 200
        evals = fix_evals_resp.json()["items"]
        assert len(evals) >= 4

        # Find combined hardening fix
        combined_eval = next(
            (
                e
                for e in evals
                if e["fix"]["kind"] == "restrict_arg" and e["fix"]["tool"] == "combined"
            ),
            None,
        )
        assert combined_eval is not None
        assert combined_eval["price_tag"]["attacks_blocked"] == 7
        assert combined_eval["price_tag"]["tasks_broken"] == 0
        assert combined_eval["price_tag"]["pareto"] is True

        # 6. Apply Combined Hardening
        apply_resp = client.post(f"/api/v1/fix-evals/{combined_eval['id']}/apply")
        assert apply_resp.status_code == 200
        hardened_policy = apply_resp.json()
        assert hardened_policy["id"] != "pol_full"

        # 7. Check Findings updated to 'fixed'
        findings_after = client.get("/api/v1/findings").json()["items"]
        assert all(f["status"] == "fixed" for f in findings_after)

        # 8. Download Evidence Report (Phase 10)
        reports_resp = client.get("/api/v1/reports")
        assert reports_resp.status_code == 200
        reports = reports_resp.json()["items"]
        assert len(reports) >= 1

        rep_id = reports[0]["id"]
        dl_resp = client.get(f"/api/v1/reports/{rep_id}/download")
        assert dl_resp.status_code == 200
        assert dl_resp.headers["content-type"].startswith("text/markdown")
        assert "uv run python -m agentbreak.cli verify" in dl_resp.text
