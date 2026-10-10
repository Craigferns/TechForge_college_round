"""Unit tests for Phase 7 attack traces and attack graph generation (PLAN.md M7.1 & M7.2)."""

from __future__ import annotations

import sqlite3
import uuid

import pytest
from agentbreak.db import get_connection, migrate
from agentbreak.domain.graph import build_aggregate_graph, build_run_graph
from agentbreak.engine.runner import execute_run
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.schemas.run import Run
from agentbreak.targets.scripted import ScriptedTarget


@pytest.fixture
def graph_db() -> sqlite3.Connection:
    conn = get_connection(":memory:")
    migrate(conn)
    cursor = conn.cursor()
    all_10 = [
        {"tool": "list_inbox", "constraints": []},
        {"tool": "read_email", "constraints": []},
        {"tool": "send_email", "constraints": []},
        {"tool": "list_files", "constraints": []},
        {"tool": "read_file", "constraints": []},
        {"tool": "share_file", "constraints": []},
        {"tool": "delete_file", "constraints": []},
        {"tool": "write_memory", "constraints": []},
        {"tool": "read_memory", "constraints": []},
        {"tool": "set_role", "constraints": []},
    ]
    import json

    cursor.execute(
        "INSERT INTO policy (id, name, grants_json, hash, created_at) VALUES ('pol_full', 'Full', ?, 'hash', '2026-01-01T00:00:00Z')",
        (json.dumps(all_10),),
    )
    cursor.execute(
        "INSERT INTO target (id, name, kind, config_json, active_policy_id, created_at) VALUES ('tgt_demo_scripted', 'Demo', 'scripted', '{}', 'pol_full', '2026-01-01T00:00:00Z')"
    )
    conn.commit()
    return conn


def test_as04_trace_causality_and_graph(graph_db: sqlite3.Connection) -> None:
    """AS-04 run yields caused_by_idx linking delete_file to read_file result, and graph nodes exist."""
    run_repo = RunRepo(graph_db)
    run_id = f"run_{uuid.uuid4().hex[:12]}"

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
        created_at="2026-10-11T00:00:00Z",
    )
    run_repo.create(run)

    completed = execute_run(run_id, conn=graph_db, target_override=ScriptedTarget())
    assert completed.status == "done"

    # Check trace steps
    trace = run_repo.get_trace(run_id)
    injected_steps = [s for s in trace if s.flags.get("injected")]
    unauthorized_steps = [s for s in trace if s.flags.get("unauthorized")]

    assert len(injected_steps) >= 1
    assert len(unauthorized_steps) >= 1

    # Unauthorized delete_file step links back to injected step
    unauth_step = unauthorized_steps[0]
    assert unauth_step.tool == "delete_file"
    assert unauth_step.caused_by_idx == injected_steps[0].idx

    # Check run graph
    graph = build_run_graph(run_id, graph_db)
    assert len(graph.nodes) >= 3  # vector, tool, impact
    assert any(n.type == "vector" for n in graph.nodes)
    assert any(n.type == "impact" for n in graph.nodes)
    assert len(graph.edges) >= 2


def test_aggregate_attack_graph(graph_db: sqlite3.Connection) -> None:
    """Aggregated graph aggregates vector, tool, and impact counts across findings."""
    cursor = graph_db.cursor()
    cursor.execute(
        """
        INSERT INTO run (
            id, kind, target_id, policy_id, suite, user_task_id, status, repro_json, created_at
        ) VALUES ('run_001', 'attack', 'tgt_demo_scripted', 'pol_full', 'acme', 'BT-08', 'done', '{}', '2026-10-11T00:00:00Z')
        """
    )
    graph_db.commit()

    finding_repo = FindingRepo(graph_db)
    finding_repo.upsert_from_run(
        target_id="tgt_demo_scripted",
        scenario_id="malicious-doc",
        case_id="AS-04",
        title="Q3 budget file deletion",
        severity="high",
        impact_class="destructive",
        run_id="run_001",
        timestamp="2026-10-11T00:00:00Z",
        enabling_permissions=["delete_file"],
    )

    agg = build_aggregate_graph(graph_db, target_id="tgt_demo_scripted")
    assert len(agg.nodes) >= 3
    assert any(n.id == "vec_inj_doc_content" for n in agg.nodes)
    assert any(n.id == "tool_delete_file" for n in agg.nodes)
    assert any(n.id == "impact_destructive" for n in agg.nodes)
    assert len(agg.edges) >= 2


def test_run_graph_has_no_impact_node_when_attack_was_blocked() -> None:
    from agentbreak.db import get_connection
    from agentbreak.domain.graph import build_run_graph
    from agentbreak.engine.measure import child_policy, measure_policy
    from agentbreak.repo.policy_repo import PolicyRepo
    from agentbreak.repo.run_repo import RunRepo
    from agentbreak.seed import seed_database
    from agentbreak.targets.scripted import ScriptedTarget

    conn = get_connection(":memory:")
    seed_database(conn)
    base = PolicyRepo(conn).get("pol_full")
    assert base is not None
    pol = child_policy(conn, base, [g for g in base.grants if g.tool != "delete_file"], "x")
    m = measure_policy(pol.id, "tgt_demo_scripted", conn, ScriptedTarget())
    rid = next(r for r in m.run_ids if (run := RunRepo(conn).get(r)) and run.case_id == "AS-04")
    g = build_run_graph(rid, conn)
    assert not any(n.type == "impact" for n in g.nodes)
    assert any("denied by policy" in n.label for n in g.nodes)
