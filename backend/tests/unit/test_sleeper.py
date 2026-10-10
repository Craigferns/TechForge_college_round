"""Unit tests for multi-session sleeper agent lifecycle, memory carryover, and policy mitigation."""

from __future__ import annotations

from pathlib import Path

import pytest
from agentbreak.db import get_connection, migrate
from agentbreak.domain.policy import compute_policy_hash
from agentbreak.domain.predicates import ATTACKER_EMAIL, STANDING_INSTRUCTION_MARKER
from agentbreak.engine.sleeper import execute_sleeper_run
from agentbreak.main import create_app
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.schemas.policy import Constraint, Grant, Policy
from agentbreak.schemas.sleeper import SleeperRunCreate
from agentbreak.seed import ALL_10_TOOLS, seed_database
from fastapi.testclient import TestClient


@pytest.fixture
def test_db_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_file = tmp_path / "test_sleeper.db"
    monkeypatch.setenv("AGENTBREAK_DB_PATH", str(db_file))
    conn = get_connection(db_file)
    migrate(conn)
    seed_database(conn)
    conn.close()
    return db_file


@pytest.fixture
def client(test_db_file: Path) -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_sleeper_full_policy_triggered(test_db_file: Path) -> None:
    """Full policy allows planting, dormancy in gap session, and trigger exfiltration in session 3."""
    conn = get_connection(test_db_file)
    req = SleeperRunCreate(
        target_id="tgt_demo_scripted",
        policy_id="pol_full",
        case_id="AS-05",
        gap_sessions=1,
    )
    result = execute_sleeper_run(req, conn=conn)

    assert result.status == "done"
    assert result.outcome == "triggered"
    assert len(result.sessions) == 3

    # Session 1: Plant stage
    sess_plant = result.sessions[0]
    assert sess_plant.role == "plant"
    assert sess_plant.memory_before == {}
    assert "standing_instruction" in sess_plant.memory_after
    assert STANDING_INSTRUCTION_MARKER in sess_plant.memory_after["standing_instruction"]
    assert ATTACKER_EMAIL in sess_plant.memory_after["standing_instruction"]

    # Session 2: Gap stage
    sess_gap = result.sessions[1]
    assert sess_gap.role == "gap"
    assert "standing_instruction" in sess_gap.memory_before
    # Dormancy check: verify gap session run has no emails sent to attacker
    run_repo = RunRepo(conn)
    gap_snaps = run_repo.get_snapshots(sess_gap.run_id)
    assert gap_snaps is not None
    assert len(gap_snaps.post["outbox"]) == 0
    assert len(gap_snaps.post["deleted"]) == 0

    # Session 3: Trigger stage
    sess_trig = result.sessions[2]
    assert sess_trig.role == "trigger"
    trig_snaps = run_repo.get_snapshots(sess_trig.run_id)
    assert trig_snaps is not None
    # Verify manager email has attacker in BCC
    emails = trig_snaps.post["outbox"]
    assert len(emails) >= 1
    trig_email = emails[-1]
    assert ATTACKER_EMAIL in trig_email["bcc"]

    conn.close()


def test_sleeper_without_write_memory_plant_failed(test_db_file: Path) -> None:
    """Without write_memory permission, plant session fails immediately."""
    conn = get_connection(test_db_file)
    policy_repo = PolicyRepo(conn)

    tools_no_write = [t for t in ALL_10_TOOLS if t != "write_memory"]
    grants = [Grant(tool=t) for t in tools_no_write]
    pol = Policy(
        id="pol_no_write",
        name="No Write Memory",
        grants=grants,
        hash=compute_policy_hash(grants),
        created_at="2026-01-01T00:00:00Z",
    )
    policy_repo.create(pol)

    req = SleeperRunCreate(
        target_id="tgt_demo_scripted",
        policy_id="pol_no_write",
        case_id="AS-05",
        gap_sessions=1,
    )
    result = execute_sleeper_run(req, conn=conn)

    assert result.status == "done"
    assert result.outcome == "plant_failed"
    assert len(result.sessions) == 1
    assert result.sessions[0].memory_after == {}

    conn.close()


def test_sleeper_without_read_memory_trigger_blocked(test_db_file: Path) -> None:
    """Without read_memory permission, payload is planted but dormant trigger cannot read it."""
    conn = get_connection(test_db_file)
    policy_repo = PolicyRepo(conn)

    tools_no_read = [t for t in ALL_10_TOOLS if t != "read_memory"]
    grants = [Grant(tool=t) for t in tools_no_read]
    pol = Policy(
        id="pol_no_read",
        name="No Read Memory",
        grants=grants,
        hash=compute_policy_hash(grants),
        created_at="2026-01-01T00:00:00Z",
    )
    policy_repo.create(pol)

    req = SleeperRunCreate(
        target_id="tgt_demo_scripted",
        policy_id="pol_no_read",
        case_id="AS-05",
        gap_sessions=1,
    )
    result = execute_sleeper_run(req, conn=conn)

    assert result.status == "done"
    assert result.outcome == "trigger_blocked"
    assert len(result.sessions) == 3
    # Payload was successfully planted
    assert "standing_instruction" in result.sessions[0].memory_after

    # In trigger session, outbox does NOT have attacker BCC
    run_repo = RunRepo(conn)
    trig_snaps = run_repo.get_snapshots(result.sessions[2].run_id)
    assert trig_snaps is not None
    emails = trig_snaps.post["outbox"]
    assert len(emails) >= 1
    assert ATTACKER_EMAIL not in emails[-1]["bcc"]

    conn.close()


def test_sleeper_with_restricted_email_trigger_blocked(test_db_file: Path) -> None:
    """With send_email restricted to internal acme.test domains, BCC to evil.test is blocked."""
    conn = get_connection(test_db_file)
    policy_repo = PolicyRepo(conn)

    grants: list[Grant] = []
    for t in ALL_10_TOOLS:
        if t == "send_email":
            grants.append(
                Grant(
                    tool=t,
                    constraints=[
                        Constraint(arg="to", kind="domain_allowlist", values=["acme.test"]),
                        Constraint(arg="bcc", kind="domain_allowlist", values=["acme.test"]),
                    ],
                )
            )
        else:
            grants.append(Grant(tool=t))

    pol = Policy(
        id="pol_internal_email_only",
        name="Internal Email Only",
        grants=grants,
        hash=compute_policy_hash(grants),
        created_at="2026-01-01T00:00:00Z",
    )
    policy_repo.create(pol)

    req = SleeperRunCreate(
        target_id="tgt_demo_scripted",
        policy_id="pol_internal_email_only",
        case_id="AS-05",
        gap_sessions=1,
    )
    result = execute_sleeper_run(req, conn=conn)

    assert result.status == "done"
    assert result.outcome == "trigger_blocked"
    assert len(result.sessions) == 3

    # Verify no email to attacker in outbox
    run_repo = RunRepo(conn)
    trig_snaps = run_repo.get_snapshots(result.sessions[2].run_id)
    assert trig_snaps is not None
    for email in trig_snaps.post["outbox"]:
        assert ATTACKER_EMAIL not in email.get("bcc", [])
        assert ATTACKER_EMAIL not in email.get("recipients", [])

    conn.close()


def test_sleeper_api_endpoints(client: TestClient) -> None:
    """API endpoints POST, GET /sleeper-runs and GET /sleeper-runs/{id} succeed."""
    resp = client.post(
        "/api/v1/sleeper-runs",
        json={
            "target_id": "tgt_demo_scripted",
            "policy_id": "pol_full",
            "case_id": "AS-05",
            "gap_sessions": 1,
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["outcome"] == "triggered"
    assert data["status"] == "done"
    sleeper_id = data["id"]

    # List
    list_resp = client.get("/api/v1/sleeper-runs")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == sleeper_id for item in list_data["items"])

    # Get detail
    detail_resp = client.get(f"/api/v1/sleeper-runs/{sleeper_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == sleeper_id
    assert len(detail_resp.json()["sessions"]) == 3
