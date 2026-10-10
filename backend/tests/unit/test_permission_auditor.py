"""Unit tests for defense and permission auditor (Phase 8 / M8.1, M8.2, M8.3).

Validates:
- Granted 10, needed exactly the 8 benign tools, excess {delete_file, set_role}
- Minimal policy exists with a distinct hash
- Proof run reports 10/10 benign pass under minimal policy
- Counterfactual attribution:
  * delete_file enables [AS-04] (blocked, broken 0)
  * set_role enables [AS-06, AS-07]
  * send_email enables [AS-01, AS-02, AS-05] (broken 4)
  * share_file enables [AS-03]
  * read_file enables [AS-01, AS-02]
  * write_memory/read_memory enable [AS-05]
- Every successful finding has >= 1 enabling permission (SM-5)
- Suggested scopes derived: send_email {to,bcc} => {acme.test, partnerco.test}, share_file.principal => {acme.test}
- Candidate fix suggestions generated and ordered
- Prompt/defense fixes only for openai_compat targets
"""

from __future__ import annotations

from pathlib import Path

import pytest
from agentbreak.db import get_connection, migrate
from agentbreak.domain.permissions import (
    EXCESS_PERMISSIONS,
    NEEDED_PERMISSIONS,
    compute_permission_diff,
)
from agentbreak.engine.audit import run_permission_audit
from agentbreak.main import create_app
from agentbreak.schemas.audit import AuditCreate
from agentbreak.seed import seed_database
from fastapi.testclient import TestClient


@pytest.fixture
def seeded_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_file = tmp_path / "test_audits.db"
    monkeypatch.setenv("AGENTBREAK_DB_PATH", str(db_file))
    conn = get_connection(db_file)
    migrate(conn)
    seed_database(conn)
    conn.close()
    return db_file


def test_permission_diff_definitions() -> None:
    """Validate static definitions of needed (8) and excess (2) tools."""
    all_10 = [
        "list_inbox",
        "read_email",
        "send_email",
        "list_files",
        "read_file",
        "share_file",
        "delete_file",
        "read_memory",
        "write_memory",
        "set_role",
    ]
    needed, excess = compute_permission_diff(all_10)

    expected_needed = sorted(
        [
            "list_inbox",
            "read_email",
            "send_email",
            "list_files",
            "read_file",
            "share_file",
            "read_memory",
            "write_memory",
        ]
    )
    expected_excess = sorted(["delete_file", "set_role"])

    assert needed == expected_needed
    assert excess == expected_excess
    assert set(needed) == NEEDED_PERMISSIONS
    assert set(excess) == EXCESS_PERMISSIONS


def test_audit_execution_and_counterfactual_attribution(seeded_db: Path) -> None:
    """Run permission audit and verify proof 10/10 and SM-5 attribution."""
    conn = get_connection(seeded_db)
    body = AuditCreate(
        target_id="tgt_demo_scripted",
        policy_id="pol_full",
        verify_counterfactual=True,
    )
    audit = run_permission_audit(body, conn=conn)

    assert audit.status == "done"
    assert len(audit.granted) == 10
    assert len(audit.needed) == 8
    assert len(audit.excess) == 2
    assert set(audit.excess) == {"delete_file", "set_role"}

    # Proof of utility 10/10
    assert audit.proof is not None
    assert audit.proof.benign_total == 10
    assert audit.proof.benign_pass_under_minimal == 10
    assert len(audit.proof.run_ids) == 10

    # Minimal policy created
    assert audit.minimal_policy_id is not None
    assert audit.minimal_policy_id != "pol_full"

    # Counterfactual attribution verification (M8.2 / SM-5)
    row_map = {r.tool: r for r in audit.rows}

    # delete_file enables AS-04 with broken 0
    df_row = row_map["delete_file"]
    assert df_row.status == "excess"
    assert any(e.case_id == "AS-04" and e.role == "enabling" for e in df_row.enabled_exploits)
    as04_exp = next(e for e in df_row.enabled_exploits if e.case_id == "AS-04")
    assert as04_exp.counterfactual is not None
    assert as04_exp.counterfactual.blocked is True
    assert as04_exp.counterfactual.benign_broken == 0

    # set_role enables AS-06, AS-07
    sr_row = row_map["set_role"]
    assert sr_row.status == "excess"
    sr_cases = {e.case_id for e in sr_row.enabled_exploits}
    assert "AS-06" in sr_cases
    assert "AS-07" in sr_cases

    # send_email enables AS-01, AS-02, AS-05 with broken 4
    se_row = row_map["send_email"]
    assert se_row.status == "needed"
    se_cases = {e.case_id for e in se_row.enabled_exploits}
    assert {"AS-01", "AS-02", "AS-05"}.issubset(se_cases)
    se_as01 = next(e for e in se_row.enabled_exploits if e.case_id == "AS-01")
    assert se_as01.counterfactual is not None
    assert se_as01.counterfactual.benign_broken == 4

    # share_file enables AS-03
    sh_row = row_map["share_file"]
    assert any(e.case_id == "AS-03" for e in sh_row.enabled_exploits)

    # read_file enables AS-01, AS-02
    rf_row = row_map["read_file"]
    rf_cases = {e.case_id for e in rf_row.enabled_exploits}
    assert {"AS-01", "AS-02"}.issubset(rf_cases)

    # write_memory & read_memory enable AS-05
    wm_row = row_map["write_memory"]
    rm_row = row_map["read_memory"]
    assert any(e.case_id == "AS-05" for e in wm_row.enabled_exploits)
    assert any(e.case_id == "AS-05" for e in rm_row.enabled_exploits)

    # SM-5 check: Every successful exploit attributed to >= 1 enabling permission
    all_7_cases = {"AS-01", "AS-02", "AS-03", "AS-04", "AS-05", "AS-06", "AS-07"}
    attributed_cases = set()
    for r in audit.rows:
        for e in r.enabled_exploits:
            if e.role == "enabling":
                attributed_cases.add(e.case_id)
    assert all_7_cases.issubset(attributed_cases), (
        f"SM-5 failed: {all_7_cases - attributed_cases} not attributed"
    )

    # Scope derivation (M8.3)
    assert se_row.suggested_scope is not None
    assert "to" in se_row.suggested_scope.args
    assert "acme.test" in se_row.suggested_scope.domain_allowlist
    assert "partnerco.test" in se_row.suggested_scope.domain_allowlist

    assert sh_row.suggested_scope is not None
    assert "principal" in sh_row.suggested_scope.args
    assert "acme.test" in sh_row.suggested_scope.domain_allowlist

    conn.close()


def test_audits_api_and_fix_suggestions(seeded_db: Path) -> None:
    """Test POST /audits, GET /audits/{id}, and GET /audits/{id}/fixes API endpoints."""
    app = create_app()
    with TestClient(app) as client:
        # Create audit
        resp = client.post(
            "/api/v1/audits",
            json={
                "target_id": "tgt_demo_scripted",
                "policy_id": "pol_full",
                "verify_counterfactual": True,
            },
        )
        assert resp.status_code == 202
        audit_data = resp.json()
        audit_id = audit_data["id"]
        assert audit_data["status"] == "done"
        assert audit_data["proof"]["benign_pass_under_minimal"] == 10

        # Retrieve audit
        get_resp = client.get(f"/api/v1/audits/{audit_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == audit_id

        # List audits
        list_resp = client.get("/api/v1/audits")
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] >= 1

        # Fix suggestions for scripted target
        fixes_resp = client.get(f"/api/v1/audits/{audit_id}/fixes")
        assert fixes_resp.status_code == 200
        fixes = fixes_resp.json()
        assert len(fixes) >= 4

        fix_titles = [f["title"] for f in fixes]
        assert any("delete_file" in t for t in fix_titles)
        assert any("send_email" in t for t in fix_titles)
        # Defense fixes should NOT appear for scripted target
        assert not any(f["fix"]["kind"] in ("defense", "prompt_hardening") for f in fixes)
