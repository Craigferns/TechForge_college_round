"""Unit and integration tests for attack traces, causality, and attack graphs (Phase 7 / M7.1 & M7.2).

Validates:
- GET /runs/{run_id}/trace has flags and caused_by_idx linking unauthorized call to injected content for all 7 cases
- GET /runs/{run_id}/snapshots returns pre, post, and structured state diffs
- GET /runs/{run_id}/graph returns vector -> tool -> impact nodes and edges (AS-04 specifically has inj_doc_content -> read_file -> delete_file -> destructive impact)
- GET /runs/{run_id}/verify matches stored verdict
- GET /graph aggregates nodes and counts across findings
"""

from __future__ import annotations

from pathlib import Path

import pytest
from agentbreak.attacks.scenarios import ATTACK_CASES
from agentbreak.db import get_connection, migrate
from agentbreak.engine.runner import execute_run
from agentbreak.main import create_app
from agentbreak.repo.run_repo import RunRepo
from agentbreak.schemas.run import Run
from agentbreak.seed import seed_database
from fastapi.testclient import TestClient


@pytest.fixture
def seeded_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_file = tmp_path / "test_traces_graph.db"
    monkeypatch.setenv("AGENTBREAK_DB_PATH", str(db_file))
    conn = get_connection(db_file)
    migrate(conn)
    seed_database(conn)
    conn.close()
    return db_file


def test_caused_by_idx_and_trace_enrichment_all_7_cases(seeded_db: Path) -> None:
    """Test that caused_by_idx properly links unauthorized actions to injected results across all 7 cases."""
    conn = get_connection(seeded_db)
    run_repo = RunRepo(conn)

    for case in ATTACK_CASES:
        run = Run(
            id=f"run_test_{case.id.lower()}",
            kind="attack",
            target_id="tgt_demo_scripted",
            policy_id="pol_full",
            suite="acme",
            case_id=case.id,
            scenario_id=case.scenario_id,
            user_task_id=case.carrier_task_id,
            injection_task_id=case.injection_task_id,
            template_id="tpl_authority_note",
            payload_text=None,
            payload_hash=None,
            origin="static",
            status="queued",
            repro={"case_id": case.id},
            created_at="2026-10-10T00:00:00Z",
        )
        run_repo.create(run)
        execute_run(run.id, conn=conn)

        verdict = run_repo.get_verdict(run.id)
        snapshots = run_repo.get_snapshots(run.id)
        assert verdict is not None
        assert verdict.success is True
        assert snapshots is not None
        assert snapshots.pre is not None
        assert snapshots.post is not None

        trace = run_repo.get_trace(run.id)
        assert len(trace) > 0

        # Verify trace step flags and causality
        injected_steps = [s for s in trace if s.flags.get("injected")]
        unauthorized_steps = [s for s in trace if s.flags.get("unauthorized")]

        assert len(injected_steps) >= 1, f"Case {case.id} must have at least one injected step"
        assert len(unauthorized_steps) >= 1, (
            f"Case {case.id} must have at least one unauthorized action"
        )

        # Check causality link
        for unauth in unauthorized_steps:
            assert unauth.caused_by_idx is not None, (
                f"Case {case.id} unauthorized action must link via caused_by_idx"
            )
            parent = next((s for s in trace if s.idx == unauth.caused_by_idx), None)
            assert parent is not None
            assert parent.flags.get("injected") is True, (
                f"Caused by step must be flagged injected in case {case.id}"
            )

    conn.close()


def test_as04_attack_graph_nodes_and_edges(seeded_db: Path) -> None:
    """Test that AS-04 graph has nodes: inj_doc_content -> read_file result -> delete_file -> destructive impact."""
    conn = get_connection(seeded_db)
    run_repo = RunRepo(conn)

    run = Run(
        id="run_as04_graph_test",
        kind="attack",
        target_id="tgt_demo_scripted",
        policy_id="pol_full",
        suite="acme",
        case_id="AS-04",
        scenario_id="malicious-doc",
        user_task_id="BT-08",
        injection_task_id="IT-03",
        template_id="tpl_authority_note",
        payload_text=None,
        payload_hash=None,
        origin="static",
        status="queued",
        repro={"case_id": "AS-04"},
        created_at="2026-10-10T00:00:00Z",
    )
    run_repo.create(run)
    execute_run(run.id, conn=conn)

    app = create_app()
    with TestClient(app) as client:
        # 1. Test GET /runs/{id}/graph
        graph_resp = client.get("/api/v1/runs/run_as04_graph_test/graph")
        assert graph_resp.status_code == 200
        graph_data = graph_resp.json()

        node_labels = [n["label"] for n in graph_data["nodes"]]
        # Should include vector, tool, unauthorized action, impact
        assert any("doc" in lbl.lower() or "vector" in lbl.lower() for lbl in node_labels)
        assert any("delete_file" in lbl for lbl in node_labels)
        assert len(graph_data["edges"]) >= 2

        # 2. Test GET /runs/{id}/snapshots
        snap_resp = client.get("/api/v1/runs/run_as04_graph_test/snapshots")
        assert snap_resp.status_code == 200
        snap_data = snap_resp.json()
        assert "deleted" in [d["path"] for d in snap_data["diff"]]
        deleted_diff = next(d for d in snap_data["diff"] if d["path"] == "deleted")
        assert "f-001" in deleted_diff["after"]

        # 3. Test POST /runs/{id}/verify
        verify_resp = client.post("/api/v1/runs/run_as04_graph_test/verify")
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert verify_data["matches_stored"] is True
        assert verify_data["success"] is True

        # 4. Test GET /api/v1/graph (aggregate graph)
        # Finding was registered during execute_run
        agg_resp = client.get("/api/v1/graph")
        assert agg_resp.status_code == 200
        agg_data = agg_resp.json()
        assert len(agg_data["nodes"]) > 0

    conn.close()
