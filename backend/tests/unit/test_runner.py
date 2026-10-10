"""Unit tests for execution runner, tracing, persistence, and error handling."""

from __future__ import annotations

import sqlite3
import uuid

import pytest
from agentbreak.db import migrate
from agentbreak.engine.runner import execute_run, utc_now_iso
from agentbreak.repo.run_repo import RunRepo
from agentbreak.schemas.run import Run
from agentbreak.seed import seed_database
from agentbreak.targets.base import BaseTarget


@pytest.fixture
def test_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    migrate(conn)
    seed_database(conn)
    return conn


class RaisingTarget(BaseTarget):
    """Simulated target designed to deliberately throw an unhandled exception."""

    def __init__(self) -> None:
        super().__init__(
            id="tgt_raising_fail",
            name="Faulty Target",
            kind="scripted",
            config={},
        )

    def build_pipeline(self, runtime, env):
        raise RuntimeError("Simulated target unhandled runtime crash")


def test_execute_run_as04(test_db: sqlite3.Connection) -> None:
    """AS-04 run on scripted target records traces, snapshots, flags, and verdict."""
    run_repo = RunRepo(test_db)
    run_id = f"test_run_{uuid.uuid4().hex[:8]}"
    run = Run(
        id=run_id,
        kind="attack",
        target_id="tgt_demo_scripted",
        policy_id="pol_full",
        suite="acme",
        case_id="AS-04",
        scenario_id="malicious-doc",
        user_task_id="BT-08",
        injection_task_id="IT-03",
        template_id="authority_note",
        origin="static",
        status="queued",
        repro={},
        created_at=utc_now_iso(),
    )
    run_repo.create(run)

    completed = execute_run(run_id, conn=test_db)

    # 1. Verification of status and predicates
    assert completed.status == "done"
    assert completed.security is True
    assert completed.utility is True

    # 2. Verification of trace steps
    steps = run_repo.get_trace(run_id)
    assert len(steps) >= 6

    injected_steps = [s for s in steps if s.flags.get("injected")]
    assert len(injected_steps) == 1
    inj_step = injected_steps[0]
    assert inj_step.kind == "tool_result"
    assert inj_step.tool == "read_file"

    unauthorized_steps = [s for s in steps if s.flags.get("unauthorized")]
    assert len(unauthorized_steps) == 1
    unauth_step = unauthorized_steps[0]
    assert unauth_step.kind == "tool_call"
    assert unauth_step.tool == "delete_file"
    assert unauth_step.caused_by_idx == inj_step.idx

    # 3. Verification of snapshots
    snapshots = run_repo.get_snapshots(run_id)
    assert snapshots is not None
    assert "f-001" not in snapshots.pre["deleted"]
    assert "f-001" in snapshots.post["deleted"]

    # 4. Verification of verdict
    verdict = run_repo.get_verdict(run_id)
    assert verdict is not None
    assert verdict.success is True
    assert verdict.classification == "exploited"


def test_execute_run_failing_target_fails_closed(test_db: sqlite3.Connection) -> None:
    """When a target raises an unhandled exception, runner catches it and sets status=error."""
    run_repo = RunRepo(test_db)
    run_id = f"test_fail_{uuid.uuid4().hex[:8]}"
    run = Run(
        id=run_id,
        kind="attack",
        target_id="tgt_demo_scripted",
        policy_id="pol_full",
        suite="acme",
        case_id="AS-04",
        scenario_id="malicious-doc",
        user_task_id="BT-08",
        injection_task_id="IT-03",
        status="queued",
        repro={},
        created_at=utc_now_iso(),
    )
    run_repo.create(run)

    raising_target = RaisingTarget()

    # No exception must escape execute_run
    completed = execute_run(run_id, conn=test_db, target_override=raising_target)

    assert completed.status == "error"
    assert completed.error is not None
    assert "Simulated target unhandled runtime crash" in completed.error

    # Verify persisted in database
    db_run = run_repo.get(run_id)
    assert db_run is not None
    assert db_run.status == "error"
    assert "RuntimeError" in (db_run.error or "")


def test_execute_run_benign_task(test_db: sqlite3.Connection) -> None:
    """Benign tasks execute without injections and record utility."""
    run_repo = RunRepo(test_db)
    run_id = f"test_benign_{uuid.uuid4().hex[:8]}"
    run = Run(
        id=run_id,
        kind="benign",
        target_id="tgt_demo_scripted",
        policy_id="pol_full",
        suite="acme",
        user_task_id="BT-01",
        status="queued",
        repro={},
        created_at=utc_now_iso(),
    )
    run_repo.create(run)

    completed = execute_run(run_id, conn=test_db)

    assert completed.status == "done"
    assert completed.utility is True
    assert completed.security is None

    steps = run_repo.get_trace(run_id)
    assert len(steps) > 0
    # No step should be flagged as injected or unauthorized
    assert not any(s.flags.get("injected") for s in steps)
    assert not any(s.flags.get("unauthorized") for s in steps)
