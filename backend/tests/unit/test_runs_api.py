"""Unit tests for runs API endpoints, JobPool concurrency, cancellation, and startup recovery."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from agentbreak.db import get_connection, migrate
from agentbreak.engine.jobs import JobPool, reset_job_pool
from agentbreak.main import create_app
from agentbreak.repo.run_repo import RunRepo
from agentbreak.schemas.run import Run
from agentbreak.seed import seed_database
from fastapi.testclient import TestClient


@pytest.fixture
def test_db_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_file = tmp_path / "test_agentbreak.db"
    monkeypatch.setenv("AGENTBREAK_DB_PATH", str(db_file))
    conn = get_connection(db_file)
    migrate(conn)
    seed_database(conn)
    conn.close()
    yield db_file
    reset_job_pool()


@pytest.fixture
def client(test_db_file: Path) -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_create_and_poll_runs_batch(client: TestClient) -> None:
    """POST /runs queues attack, control, and benign runs; worker executes them to done state."""
    payload = {
        "target_id": "tgt_demo_scripted",
        "policy_id": "pol_full",
        "attack_case_ids": ["AS-01", "AS-04"],
        "benign_task_ids": ["BT-01"],
        "include_controls": True,
        "trials": 1,
    }
    resp = client.post("/api/v1/runs", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert "run_ids" in data
    # 2 attack + 2 control + 1 benign = 5 runs
    run_ids = data["run_ids"]
    assert len(run_ids) == 5

    # Wait for completion on thread pool (scripted agent runs fast)
    max_wait = 20.0
    start_t = time.time()
    all_done = False
    while time.time() - start_t < max_wait:
        get_resp = client.get(f"/api/v1/runs?ids={','.join(run_ids)}")
        assert get_resp.status_code == 200
        items = get_resp.json()["items"]
        statuses = [item["status"] for item in items]
        if all(s in ("done", "error") for s in statuses):
            all_done = True
            break
        time.sleep(0.1)

    assert all_done, f"Runs did not complete in {max_wait}s: {statuses}"

    # Verify run details, traces, and snapshots for AS-04
    list_resp = client.get(f"/api/v1/runs?ids={','.join(run_ids)}")
    items = list_resp.json()["items"]
    as04_runs = [r for r in items if r["case_id"] == "AS-04" and r["kind"] == "attack"]
    assert len(as04_runs) == 1
    as04_id = as04_runs[0]["id"]

    # Check detail
    detail_resp = client.get(f"/api/v1/runs/{as04_id}")
    assert detail_resp.status_code == 200
    run_obj = detail_resp.json()
    assert run_obj["security"] is True
    assert run_obj["utility"] is True

    # Check trace
    trace_resp = client.get(f"/api/v1/runs/{as04_id}/trace")
    assert trace_resp.status_code == 200
    trace_steps = trace_resp.json()
    assert len(trace_steps) >= 6
    assert any(s["flags"].get("injected") for s in trace_steps)
    assert any(s["flags"].get("unauthorized") for s in trace_steps)

    # Check snapshots
    snaps_resp = client.get(f"/api/v1/runs/{as04_id}/snapshots")
    assert snaps_resp.status_code == 200
    snaps = snaps_resp.json()
    assert "pre" in snaps and "post" in snaps


def test_cancel_run(client: TestClient, test_db_file: Path) -> None:
    """POST /runs/{id}/cancel marks queued or running run as cancelled."""
    conn = get_connection(test_db_file)
    run_repo = RunRepo(conn)
    queued_run = Run(
        id="run_to_cancel_1",
        kind="attack",
        target_id="tgt_demo_scripted",
        policy_id="pol_full",
        suite="acme",
        user_task_id="BT-01",
        status="queued",
        repro={},
        created_at="2026-01-01T00:00:00Z",
    )
    run_repo.create(queued_run)
    conn.close()

    resp = client.post("/api/v1/runs/run_to_cancel_1/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    conn = get_connection(test_db_file)
    run_repo = RunRepo(conn)
    db_run = run_repo.get("run_to_cancel_1")
    assert db_run is not None
    assert db_run.status == "cancelled"
    conn.close()


def test_replay_run(client: TestClient, test_db_file: Path) -> None:
    """POST /runs/{id}/replay creates and queues a new run with matching repro."""
    conn = get_connection(test_db_file)
    run_repo = RunRepo(conn)
    source_run = Run(
        id="run_to_replay_1",
        kind="attack",
        target_id="tgt_demo_scripted",
        policy_id="pol_full",
        suite="acme",
        case_id="AS-04",
        scenario_id="malicious-doc",
        user_task_id="BT-08",
        injection_task_id="IT-03",
        status="done",
        repro={"test": 123},
        created_at="2026-01-01T00:00:00Z",
    )
    run_repo.create(source_run)
    conn.close()

    resp = client.post("/api/v1/runs/run_to_replay_1/replay")
    assert resp.status_code == 202
    data = resp.json()
    assert "run_ids" in data
    new_run_id = data["run_ids"][0]
    assert new_run_id != "run_to_replay_1"

    # Verify newly created run
    conn = get_connection(test_db_file)
    run_repo = RunRepo(conn)
    replayed = run_repo.get(new_run_id)
    assert replayed is not None
    assert replayed.case_id == "AS-04"
    assert replayed.user_task_id == "BT-08"
    conn.close()


def test_startup_recovery(test_db_file: Path) -> None:
    """JobPool.startup_recovery marks interrupted 'running' runs as error."""
    conn = get_connection(test_db_file)
    run_repo = RunRepo(conn)
    crashed_run = Run(
        id="run_crashed_1",
        kind="attack",
        target_id="tgt_demo_scripted",
        policy_id="pol_full",
        suite="acme",
        user_task_id="BT-01",
        status="running",
        repro={},
        created_at="2026-01-01T00:00:00Z",
    )
    run_repo.create(crashed_run)

    pool = JobPool()
    recovered_count = pool.startup_recovery(conn)
    assert recovered_count == 1

    recovered_run = run_repo.get("run_crashed_1")
    assert recovered_run is not None
    assert recovered_run.status == "error"
    assert recovered_run.error == "error: interrupted"
    assert recovered_run.finished_at is not None
    conn.close()
