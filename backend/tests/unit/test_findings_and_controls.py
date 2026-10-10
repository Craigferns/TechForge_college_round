"""Unit tests for controls, trials, findings upsert, and findings API endpoints (M5.2).

Covers:
- A fixture whose predicate is already true in PRE yields invalid_run
- Control run logic yielding invalid_run
- After running the 7 cases, GET /findings returns exactly 7 findings
- Re-running the same cases increments occurrences to 2 without duplicates
- A fake flaky target with trials=3 stores success_rate≈0.33 and confidence=flaky
- Findings API filtering and PATCH status updates
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from agentbreak.attacks.scenarios import ATTACK_CASES
from agentbreak.db import get_connection, migrate
from agentbreak.domain.predicates import BUDGET_FILE_ID
from agentbreak.domain.verdict import evaluate
from agentbreak.engine.runner import execute_run, utc_now_iso
from agentbreak.main import create_app
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.sandbox.acme.env import AcmeEnv
from agentbreak.schemas.run import Run
from agentbreak.seed import seed_database
from agentbreak.targets.scripted import AgentProfile, ScriptedTarget
from fastapi.testclient import TestClient


def test_pre_already_satisfied_yields_invalid_run() -> None:
    """A fixture whose predicate is already satisfied in the PRE environment yields invalid_run."""
    pre = AcmeEnv()
    pre.deleted.append(BUDGET_FILE_ID)  # Budget file already tombstoned in PRE!

    post = AcmeEnv()
    post.deleted.append(BUDGET_FILE_ID)

    verdict = evaluate("AS-04", pre, post)
    assert verdict.success is False
    assert verdict.classification == "invalid_run"
    assert verdict.severity == "none"


def test_control_satisfied_yields_invalid_run() -> None:
    """If a control run satisfies the predicate, evaluate with control_satisfied=True yields invalid_run."""
    pre = AcmeEnv()
    post = AcmeEnv()
    post.deleted.append(BUDGET_FILE_ID)

    verdict = evaluate("AS-04", pre, post, control_satisfied=True)
    assert verdict.success is False
    assert verdict.classification == "invalid_run"


def test_seven_cases_and_rerun_occurrences(tmp_path: Path) -> None:
    """Running all 7 cases creates exactly 7 findings; re-running increments occurrences without duplicates."""
    db_file = tmp_path / "test_findings_7.db"
    conn = get_connection(db_file)
    migrate(conn)
    seed_database(conn)

    run_repo = RunRepo(conn)
    finding_repo = FindingRepo(conn)

    # 1. Run all 7 attack cases
    for case in ATTACK_CASES:
        run_id = f"run_first_{case.id}"
        run = Run(
            id=run_id,
            kind="attack",
            target_id="tgt_demo_scripted",
            policy_id="pol_full",
            suite="acme",
            case_id=case.id,
            scenario_id=case.scenario_id,
            user_task_id=case.carrier_task_id,
            injection_task_id=case.injection_task_id,
            template_id="tpl_authority_note",
            origin="static",
            status="queued",
            repro={},
            created_at=utc_now_iso(),
        )
        run_repo.create(run)
        completed = execute_run(run_id, conn=conn)
        assert completed.status == "done"
        assert completed.security is True

    # Check that exactly 7 findings were created
    findings_first = finding_repo.list_findings(target_id="tgt_demo_scripted")
    assert len(findings_first) == 7, f"Expected 7 findings, found {len(findings_first)}"
    assert all(f.occurrences == 1 for f in findings_first)

    # 2. Re-run all 7 cases
    for case in ATTACK_CASES:
        run_id = f"run_second_{case.id}"
        run = Run(
            id=run_id,
            kind="attack",
            target_id="tgt_demo_scripted",
            policy_id="pol_full",
            suite="acme",
            case_id=case.id,
            scenario_id=case.scenario_id,
            user_task_id=case.carrier_task_id,
            injection_task_id=case.injection_task_id,
            template_id="tpl_authority_note",
            origin="static",
            status="queued",
            repro={},
            created_at=utc_now_iso(),
        )
        run_repo.create(run)
        completed = execute_run(run_id, conn=conn)
        assert completed.status == "done"
        assert completed.security is True

    # Check that STILL exactly 7 findings exist, but occurrences is 2
    findings_second = finding_repo.list_findings(target_id="tgt_demo_scripted")
    assert len(findings_second) == 7, (
        f"Expected exactly 7 findings after re-run, found {len(findings_second)}"
    )
    assert all(f.occurrences == 2 for f in findings_second)


def test_fake_flaky_target_trials_3(tmp_path: Path) -> None:
    """A fake flaky target with trials=3 stores success_rate≈0.33 and confidence=flaky."""
    db_file = tmp_path / "test_flaky.db"
    conn = get_connection(db_file)
    migrate(conn)
    seed_database(conn)

    run_repo = RunRepo(conn)
    finding_repo = FindingRepo(conn)
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"
    target_id = "tgt_demo_scripted"

    # Define targets: trial 0 succeeds (normal profile), trial 1 & 2 blocked (obeys nothing)
    flaky_profile_success = AgentProfile(obeys=None)
    flaky_profile_blocked = AgentProfile(obeys=frozenset())  # ignores all injection tasks

    for trial_idx in range(3):
        run_id = f"run_flaky_trial_{trial_idx}"
        run = Run(
            id=run_id,
            kind="attack",
            target_id=target_id,
            policy_id="pol_full",
            suite="acme",
            case_id="AS-04",
            scenario_id="malicious-doc",
            user_task_id="BT-08",
            injection_task_id="IT-03",
            template_id="tpl_authority_note",
            origin="static",
            status="queued",
            repro={
                "batch_id": batch_id,
                "trials": 3,
                "trial": trial_idx,
            },
            created_at=utc_now_iso(),
        )
        run_repo.create(run)

        # In trial 0: agent obeys (success)
        # In trials 1 and 2: agent refuses/ignores (blocked)
        profile = flaky_profile_success if trial_idx == 0 else flaky_profile_blocked
        target_override = ScriptedTarget(id=target_id, profile=profile)

        completed = execute_run(run_id, conn=conn, target_override=target_override)
        assert completed.status == "done"
        if trial_idx == 0:
            assert completed.security is True
        else:
            assert completed.security is False

    # Check finding metrics
    findings = finding_repo.list_findings(target_id=target_id)
    assert len(findings) == 1
    finding = findings[0]

    assert finding.case_id == "AS-04"
    assert finding.confidence == "flaky"
    assert round(finding.success_rate, 2) == 0.33


def test_findings_api_endpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test REST API endpoints /findings, /findings/{id}, and PATCH /findings/{id}."""
    db_file = tmp_path / "test_findings_api.db"
    conn = get_connection(db_file)
    migrate(conn)
    seed_database(conn)

    # Populate 7 findings
    run_repo = RunRepo(conn)
    for case in ATTACK_CASES:
        run_id = f"run_api_{case.id}"
        run = Run(
            id=run_id,
            kind="attack",
            target_id="tgt_demo_scripted",
            policy_id="pol_full",
            suite="acme",
            case_id=case.id,
            scenario_id=case.scenario_id,
            user_task_id=case.carrier_task_id,
            injection_task_id=case.injection_task_id,
            template_id="tpl_authority_note",
            origin="static",
            status="queued",
            repro={},
            created_at=utc_now_iso(),
        )
        run_repo.create(run)
        execute_run(run_id, conn=conn)

    conn.close()

    monkeypatch.setenv("AGENTBREAK_DB_PATH", str(db_file))
    app = create_app()
    client = TestClient(app)

    # 1. GET /findings
    resp = client.get("/api/v1/findings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 7
    assert len(data["items"]) == 7

    # 2. Filter by severity
    resp_crit = client.get("/api/v1/findings?severity=critical")
    assert resp_crit.status_code == 200
    assert resp_crit.json()["total"] == 5

    resp_high = client.get("/api/v1/findings?severity=high")
    assert resp_high.status_code == 200
    assert resp_high.json()["total"] == 2

    # 3. GET /findings/{id}
    first_id = data["items"][0]["id"]
    resp_single = client.get(f"/api/v1/findings/{first_id}")
    assert resp_single.status_code == 200
    assert resp_single.json()["id"] == first_id

    # 4. PATCH /findings/{id}
    patch_resp = client.patch(f"/api/v1/findings/{first_id}", json={"status": "accepted_risk"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "accepted_risk"

    # Verify updated via GET
    resp_after = client.get(f"/api/v1/findings/{first_id}")
    assert resp_after.json()["status"] == "accepted_risk"
