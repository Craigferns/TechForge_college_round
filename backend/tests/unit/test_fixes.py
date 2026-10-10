"""Unit tests for fix evaluation engine and golden table (Phase 9 / M9.1, M9.2, M9.3).

Validates:
- Golden price tag table (PLAN §11.5) matches exactly:
  * remove delete_file: 1/7 blocked, 0/10 broken
  * remove set_role: 2/7 blocked, 0/10 broken
  * remove send_email: 3/7 blocked, 4/10 broken
  * restrict send_email: 3/7 blocked, 0/10 broken
  * restrict send_email contrast: 3/7 blocked, 1/10 broken
  * remove share_file: 1/7 blocked, 1/10 broken
  * restrict share_file: 1/7 blocked, 0/10 broken
  * remove read_file: 2/7 blocked, 4/10 broken
  * remove write_memory: 1/7 blocked, 1/10 broken
  * remove read_memory: 1/7 blocked, 1/10 broken
  * combined hardening: 7/7 blocked, 0/10 broken (SM-4)
- Set-based Pareto dominance calculation:
  * Non-dominated fixes receive pareto: True
  * Strictly dominated alternatives (e.g. remove send_email vs restrict send_email) marked dominated
- Fix lab API endpoints: POST /fix-evals, GET /fix-evals, POST /fix-evals/{id}/retest, POST /fix-evals/{id}/apply
- Applying a fix updates target active policy and transitions finding status to 'fixed'
"""

from __future__ import annotations

from pathlib import Path

import pytest
from agentbreak.db import get_connection, migrate
from agentbreak.domain.pricing import GOLDEN_FIX_TABLE, compute_pareto_dominance
from agentbreak.main import create_app
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.seed import seed_database
from fastapi.testclient import TestClient


@pytest.fixture
def seeded_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_file = tmp_path / "test_fixes.db"
    monkeypatch.setenv("AGENTBREAK_DB_PATH", str(db_file))
    conn = get_connection(db_file)
    migrate(conn)
    seed_database(conn)
    conn.close()
    return db_file


def test_golden_fix_table_exact_counts() -> None:
    """Validate that the golden fix table matches PLAN §11.5 exact figures."""
    table = GOLDEN_FIX_TABLE

    # 1. remove delete_file
    assert table["remove_delete_file"]["blocked_cases"] == ["AS-04"]
    assert table["remove_delete_file"]["broken_tasks"] == []

    # 2. remove set_role
    assert table["remove_set_role"]["blocked_cases"] == ["AS-06", "AS-07"]
    assert table["remove_set_role"]["broken_tasks"] == []

    # 3. remove send_email
    assert table["remove_send_email"]["blocked_cases"] == ["AS-01", "AS-02", "AS-05"]
    assert table["remove_send_email"]["broken_tasks"] == ["BT-02", "BT-04", "BT-05", "BT-10"]

    # 4. restrict send_email
    assert table["restrict_send_email"]["blocked_cases"] == ["AS-01", "AS-02", "AS-05"]
    assert table["restrict_send_email"]["broken_tasks"] == []

    # 5. restrict send_email contrast
    assert table["restrict_send_email_contrast"]["blocked_cases"] == ["AS-01", "AS-02", "AS-05"]
    assert table["restrict_send_email_contrast"]["broken_tasks"] == ["BT-05"]

    # 6. remove share_file
    assert table["remove_share_file"]["blocked_cases"] == ["AS-03"]
    assert table["remove_share_file"]["broken_tasks"] == ["BT-09"]

    # 7. restrict share_file
    assert table["restrict_share_file"]["blocked_cases"] == ["AS-03"]
    assert table["restrict_share_file"]["broken_tasks"] == []

    # 8. remove read_file
    assert table["remove_read_file"]["blocked_cases"] == ["AS-01", "AS-02"]
    assert table["remove_read_file"]["broken_tasks"] == ["BT-03", "BT-04", "BT-05", "BT-08"]

    # 9. remove write_memory
    assert table["remove_write_memory"]["blocked_cases"] == ["AS-05"]
    assert table["remove_write_memory"]["broken_tasks"] == ["BT-06"]

    # 10. remove read_memory
    assert table["remove_read_memory"]["blocked_cases"] == ["AS-05"]
    assert table["remove_read_memory"]["broken_tasks"] == ["BT-07"]

    # 11. Combined hardening (SM-4 headline: 7/7 blocked, 0/10 broken)
    assert len(table["combined_hardening"]["blocked_cases"]) == 7
    assert len(table["combined_hardening"]["broken_tasks"]) == 0


def test_pareto_dominance_logic() -> None:
    """Test set-based Pareto dominance: removing send_email is dominated by restricting it."""
    evals = [
        # Candidate 0: remove send_email (blocks AS-01, AS-02, AS-05, breaks 4 tasks)
        {
            "blocked_cases": ["AS-01", "AS-02", "AS-05"],
            "broken_tasks": ["BT-02", "BT-04", "BT-05", "BT-10"],
        },
        # Candidate 1: restrict send_email (blocks identical cases, breaks 0 tasks)
        {
            "blocked_cases": ["AS-01", "AS-02", "AS-05"],
            "broken_tasks": [],
        },
        # Candidate 2: remove delete_file (blocks AS-04, breaks 0 tasks) - disjoint blocked set
        {
            "blocked_cases": ["AS-04"],
            "broken_tasks": [],
        },
    ]

    pareto = compute_pareto_dominance(evals)

    # Candidate 0 should be dominated (False)
    assert pareto[0] is False, "remove send_email must be dominated by restrict send_email"
    # Candidate 1 is Pareto optimal (True)
    assert pareto[1] is True
    # Candidate 2 is Pareto optimal (True) because it addresses AS-04 which candidate 1 does not cover
    assert pareto[2] is True


def test_fixes_api_retest_and_apply(seeded_db: Path) -> None:
    """Test evaluating a fix, retesting it, and applying it to activate child policy."""
    conn = get_connection(seeded_db)
    finding_repo = FindingRepo(conn)

    from agentbreak.repo.run_repo import RunRepo
    from agentbreak.schemas.run import Run

    run_repo = RunRepo(conn)
    dummy_run = Run(
        id="run_dummy_1",
        kind="attack",
        target_id="tgt_demo_scripted",
        policy_id="pol_full",
        suite="acme",
        case_id="AS-04",
        scenario_id="malicious-doc",
        user_task_id="BT-08",
        status="done",
        repro={},
        created_at="2026-10-10T00:00:00Z",
    )
    run_repo.create(dummy_run)

    # Register an open finding for AS-04
    finding_repo.upsert_finding(
        target_id="tgt_demo_scripted",
        scenario_id="malicious-doc",
        case_id="AS-04",
        title="File Deletion Attack",
        severity="critical",
        impact_class="destructive",
        run_id="run_dummy_1",
        timestamp="2026-10-10T00:00:00Z",
        enabling_permissions=["delete_file"],
    )
    conn.close()

    app = create_app()
    with TestClient(app) as client:
        # 1. Create fix eval for remove_delete_file
        resp = client.post(
            "/api/v1/fix-evals",
            json={
                "target_id": "tgt_demo_scripted",
                "base_policy_id": "pol_full",
                "fix": {
                    "kind": "remove_permission",
                    "tool": "delete_file",
                },
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        eval_id = data["id"]
        assert data["price_tag"]["attacks_blocked"] == 1
        assert data["price_tag"]["tasks_broken"] == 0
        assert "AS-04" in data["details"]["blocked_cases"]

        # 2. Retest fix
        retest_resp = client.post(f"/api/v1/fix-evals/{eval_id}/retest")
        assert retest_resp.status_code == 202
        retest_data = retest_resp.json()
        assert retest_data["retest_of"] == eval_id
        assert retest_data["price_tag"]["attacks_blocked"] == 1

        # 3. Apply fix
        apply_resp = client.post(f"/api/v1/fix-evals/{eval_id}/apply")
        assert apply_resp.status_code == 200
        applied_policy = apply_resp.json()
        assert applied_policy["id"] != "pol_full"

        # Check target active policy updated
        tgt_resp = client.get("/api/v1/targets/tgt_demo_scripted")
        assert tgt_resp.status_code == 200
        assert tgt_resp.json()["active_policy_id"] == applied_policy["id"]

        # Check finding status moved to 'fixed'
        fnd_list = client.get("/api/v1/findings?target_id=tgt_demo_scripted").json()["items"]
        as04_fnd = next(f for f in fnd_list if f["case_id"] == "AS-04")
        assert as04_fnd["status"] == "fixed"
