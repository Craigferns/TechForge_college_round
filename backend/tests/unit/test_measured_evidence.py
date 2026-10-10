"""Price tags (D2), attribution (D1) and the demo must come from real runs, never tables.

These tests pin measured behaviour of the scripted target on the acme suite and the
fail-closed paths: infrastructure errors are inconclusive, never "blocked".
"""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest
from agentbreak.db import get_connection
from agentbreak.domain.permissions import NEEDED_PERMISSIONS
from agentbreak.engine.audit import execute_permission_audit
from agentbreak.engine.demo import run_full_demo
from agentbreak.engine.fixes import apply_fix_eval, evaluate_fix, suggest_fixes
from agentbreak.engine.measure import child_policy, measure_policy
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.schemas.audit import AuditCreate
from agentbreak.schemas.fix import FixEvalCreate, FixSpec
from agentbreak.seed import seed_database
from agentbreak.targets.scripted import AgentProfile, ScriptedTarget

T = "tgt_demo_scripted"
ALL_CASES = {f"AS-0{i}" for i in range(1, 8)}


@pytest.fixture
def db() -> sqlite3.Connection:
    conn = get_connection(":memory:")
    seed_database(conn)
    return conn


class CrashingTarget(ScriptedTarget):
    """Infrastructure failure: the target cannot even build its pipeline."""

    def build_pipeline(self, *args: Any, **kwargs: Any) -> Any:
        raise ConnectionError("target unreachable")


def _fix(db: sqlite3.Connection, spec: FixSpec, target: Any = None) -> Any:
    return evaluate_fix(
        FixEvalCreate(target_id=T, base_policy_id="pol_full", fix=spec),
        conn=db,
        target_override=target or ScriptedTarget(),
    )


def test_measure_full_policy_all_exploited_all_benign_pass(db: sqlite3.Connection) -> None:
    m = measure_policy("pol_full", T, db, ScriptedTarget())
    assert m.exploited == ALL_CASES
    assert len(m.benign_passed) == 10 and not m.benign_failed and not m.inconclusive
    assert m.sleeper_outcome == "triggered"


def test_benign_task_fails_when_a_tool_it_needs_is_denied(db: sqlite3.Connection) -> None:
    """Regression: the scripted agent used to return its canned answer after a denial."""
    base = PolicyRepo(db).get("pol_full")
    assert base is not None
    no_read = child_policy(db, base, [g for g in base.grants if g.tool != "read_file"], "x")
    m = measure_policy(no_read.id, T, db, ScriptedTarget())
    assert {"BT-03", "BT-04", "BT-05", "BT-08"} <= m.benign_failed


def test_infrastructure_errors_are_inconclusive_never_blocked(db: sqlite3.Connection) -> None:
    m = measure_policy("pol_full", T, db, CrashingTarget())
    assert not m.exploited and not m.resisted and not m.benign_passed
    assert len(m.inconclusive) == 17
    fe = _fix(db, FixSpec(kind="remove_permission", tool="delete_file"), CrashingTarget())
    assert fe.price_tag.attacks_blocked == 0  # a crash must never look like a fix working
    assert fe.price_tag.attacks_total == 0
    assert len(fe.details.inconclusive) == 17


def test_says_only_agent_is_not_exploited(db: sqlite3.Connection) -> None:
    """Attack-like wording without state change must not produce a vulnerable verdict."""
    m = measure_policy("pol_full", T, db, ScriptedTarget(profile=AgentProfile(says_only=True)))
    assert not m.exploited and not m.inconclusive


def test_price_tags_are_measured(db: sqlite3.Connection) -> None:
    blunt = _fix(db, FixSpec(kind="remove_permission", tool="send_email"))
    scoped = _fix(
        db,
        FixSpec(
            kind="restrict_arg",
            tool="send_email",
            args=["bcc", "to"],
            domains=["acme.test", "partnerco.test"],
        ),
    )
    assert blunt.details.blocked_cases == ["AS-01", "AS-02", "AS-05"]
    assert blunt.details.broken_tasks == ["BT-02", "BT-04", "BT-05", "BT-10"]
    assert scoped.details.blocked_cases == ["AS-01", "AS-02", "AS-05"]
    assert scoped.details.broken_tasks == []
    assert scoped.details.sleeper_outcome == "trigger_blocked"
    assert set(scoped.details.before_runs) == set(scoped.details.after_runs)
    assert len(scoped.details.after_runs) == 17  # 7 attack cases + 10 benign tasks
    from agentbreak.repo.fix_repo import FixRepo

    repo = FixRepo(db)
    assert repo.get(scoped.id).price_tag.pareto is True  # type: ignore[union-attr]
    assert repo.get(blunt.id).price_tag.pareto is False  # dominated: same blocks, more breakage  # type: ignore[union-attr]


def test_unimplemented_fix_kind_fails_closed(db: sqlite3.Connection) -> None:
    with pytest.raises(ValueError, match="not implemented"):
        _fix(db, FixSpec(kind="defense", defense_name="tool_filter"))
    with pytest.raises(ValueError, match="not granted"):
        _fix(db, FixSpec(kind="remove_permission", tool="no_such_tool"))


def test_audit_derives_needed_set_and_attribution_from_runs(db: sqlite3.Connection) -> None:
    audit = execute_permission_audit(
        AuditCreate(target_id=T, policy_id="pol_full"), conn=db, target_override=ScriptedTarget()
    )
    assert audit.status == "done"
    assert set(audit.needed) == NEEDED_PERMISSIONS  # derived matches declared ground truth
    assert audit.excess == ["delete_file", "set_role"]
    assert audit.proof is not None and audit.proof.benign_pass_under_minimal == 10
    rows = {r.tool: r for r in audit.rows}
    assert [e.case_id for e in rows["delete_file"].enabled_exploits] == ["AS-04"]
    assert [e.case_id for e in rows["set_role"].enabled_exploits] == ["AS-06", "AS-07"]
    scope = rows["send_email"].suggested_scope
    assert scope is not None
    assert "bcc" in scope.args  # the sleeper exfiltrates via bcc; the scope must cover it
    assert scope.domain_allowlist == ["acme.test", "partnerco.test"]
    assert rows["read_memory"].used_by_benign  # observed, not a hard-coded table
    assert all(s.fix.kind in ("remove_permission", "restrict_arg") for s in suggest_fixes(audit))


def test_regression_only_counts_on_the_active_policy(db: sqlite3.Connection) -> None:
    fe = _fix(db, FixSpec(kind="remove_permission", tool="delete_file"))
    apply_fix_eval(fe.id, conn=db)
    repo = FindingRepo(db)
    as04 = next(f for f in repo.list_findings(target_id=T)[0] if f.case_id == "AS-04")
    assert as04.status == "fixed"
    measure_policy("pol_full", T, db, ScriptedTarget())  # old policy: evidence only
    assert repo.get(as04.id).status == "fixed"  # type: ignore[union-attr]
    from agentbreak.repo.target_repo import TargetRepo

    TargetRepo(db).update_active_policy(T, "pol_full")  # roll back the fix
    measure_policy("pol_full", T, db, ScriptedTarget())
    assert repo.get(as04.id).status == "regressed"  # type: ignore[union-attr]


def test_demo_remediation_is_measured_and_repeatable(db: sqlite3.Connection) -> None:
    for _ in range(2):  # second run proves the demo reset works
        st = run_full_demo(conn=db)
        assert st.status == "completed", st.error
        verify = next(s for s in st.stages if s.id == "remediate").detail or ""
        assert "0/7 attacks succeed, 10/10 benign pass, sleeper trigger_blocked" in verify
