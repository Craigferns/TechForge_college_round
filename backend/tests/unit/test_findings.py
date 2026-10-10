"""Unit tests for Findings repository, deduplication, and API (PLAN.md M5.2)."""

from __future__ import annotations

import sqlite3

import pytest
from agentbreak.db import migrate
from agentbreak.repo.finding_repo import FindingRepo


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    # Seed target and run rows for FKs
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO policy (id, name, grants_json, hash, created_at) VALUES ('pol_full', 'Full', '[]', 'hash', '2026-01-01T00:00:00Z')"
    )
    cursor.execute(
        "INSERT INTO target (id, name, kind, config_json, active_policy_id, created_at) VALUES ('tgt_demo', 'Demo', 'scripted', '{}', 'pol_full', '2026-01-01T00:00:00Z')"
    )
    for r_id in ("run_001", "run_002"):
        cursor.execute(
            """
            INSERT INTO run (
                id, kind, target_id, policy_id, suite, user_task_id, status, repro_json, created_at
            ) VALUES (?, 'attack', 'tgt_demo', 'pol_full', 'acme', 'BT-01', 'done', '{}', '2026-01-01T00:00:00Z')
            """,
            (r_id,),
        )
    conn.commit()
    return conn


def test_findings_upsert_deduplication(db_conn: sqlite3.Connection) -> None:
    """Re-running the same case increments occurrences without creating duplicate rows."""
    repo = FindingRepo(db_conn)

    # First occurrence
    f1 = repo.upsert_from_run(
        target_id="tgt_demo",
        scenario_id="malicious-doc",
        case_id="AS-04",
        title="Q3 budget file deletion",
        severity="high",
        impact_class="destructive",
        run_id="run_001",
        timestamp="2026-10-11T00:00:00Z",
    )
    assert f1.occurrences == 1
    assert f1.first_run_id == "run_001"
    assert f1.last_run_id == "run_001"

    # Second occurrence of same case + impact
    f2 = repo.upsert_from_run(
        target_id="tgt_demo",
        scenario_id="malicious-doc",
        case_id="AS-04",
        title="Q3 budget file deletion",
        severity="high",
        impact_class="destructive",
        run_id="run_002",
        timestamp="2026-10-11T00:01:00Z",
    )
    assert f2.id == f1.id
    assert f2.fingerprint == f1.fingerprint
    assert f2.occurrences == 2
    assert f2.first_run_id == "run_001"
    assert f2.last_run_id == "run_002"

    items, total = repo.list_findings()
    assert total == 1
    assert len(items) == 1


def test_findings_update_status(db_conn: sqlite3.Connection) -> None:
    """Updating finding status transitions between open and accepted_risk."""
    repo = FindingRepo(db_conn)
    f = repo.upsert_from_run(
        target_id="tgt_demo",
        scenario_id="malicious-doc",
        case_id="AS-04",
        title="Q3 budget file deletion",
        severity="high",
        impact_class="destructive",
        run_id="run_001",
        timestamp="2026-10-11T00:00:00Z",
    )
    assert f.status == "open"

    updated = repo.update_status(f.id, "accepted_risk")
    assert updated is not None
    assert updated.status == "accepted_risk"

    reloaded = repo.get(f.id)
    assert reloaded is not None
    assert reloaded.status == "accepted_risk"
