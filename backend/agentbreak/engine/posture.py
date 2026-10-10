"""Current security posture of one target (shared by the dashboard API and the report)."""

from __future__ import annotations

import sqlite3

from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.repo.sleeper_repo import SleeperRepo
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.schemas.dashboard import DashboardSummary
from agentbreak.schemas.run import RunSummary


def compute_posture(conn: sqlite3.Connection, target_id: str) -> DashboardSummary:
    """Latest completed result per attack case / benign task under the target's ACTIVE policy."""
    finding_repo = FindingRepo(conn)
    run_repo = RunRepo(conn)
    target = TargetRepo(conn).get(target_id)
    active = target.active_policy_id if target else None

    findings, _ = finding_repo.list_findings(target_id=target_id, limit=200)
    sev_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    open_count = 0
    for f in findings:
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1
        if f.status in ("open", "regressed"):  # fixed/accepted findings need no attention
            open_count += 1

    # Sleeper sessions are judged by their chain outcome, not their per-session verdict.
    sleepers = [
        s
        for s in SleeperRepo(conn).list_runs(target_id=target_id, limit=500)
        if s.policy_id == active
    ]
    in_chain = {sess.run_id for s in sleepers for sess in s.sessions}
    latest_sleeper = max(sleepers, key=lambda s: s.created_at, default=None)

    latest: dict[str, RunSummary] = {}
    if active:
        for r in run_repo.list_runs(target_id=target_id, policy_id=active, limit=2000):
            key = r.case_id if r.kind == "attack" else r.user_task_id
            if (
                r.id in in_chain
                or r.kind == "control"
                or not key
                or r.status not in ("done", "error")
            ):
                continue
            if key not in latest or r.created_at > latest[key].created_at:
                latest[key] = r
    attacks = [r for k, r in latest.items() if r.kind == "attack" and k != "AS-05"]
    benign = [r for r in latest.values() if r.kind == "benign"]
    inconclusive = sum(1 for r in attacks + benign if r.status == "error")

    tot_attacks = sum(1 for r in attacks if r.status == "done")
    succ_attacks = sum(1 for r in attacks if r.status == "done" and r.security is True)
    if latest_sleeper and latest_sleeper.outcome:
        tot_attacks += 1
        succ_attacks += latest_sleeper.outcome == "triggered"
    tot_benign = sum(1 for r in benign if r.status == "done")
    pass_benign = sum(1 for r in benign if r.utility is True)

    # Hardening since first test: grants removed or newly constrained relative to the policy of
    # the target's earliest run. (Policy lineage is not used: identical policies are deduplicated
    # by hash, so parent links do not record history.)
    revisions = 0
    pol_repo = PolicyRepo(conn)
    first = conn.execute(
        "SELECT policy_id FROM run WHERE target_id = ? ORDER BY created_at ASC LIMIT 1",
        (target_id,),
    ).fetchone()
    pol = pol_repo.get(active) if active else None
    root = pol_repo.get(first[0]) if first else None
    if pol is not None and root is not None:
        now = {g.tool: g.constraints for g in pol.grants}
        revisions = sum(1 for g in root.grants if g.tool not in now or now[g.tool] != g.constraints)

    return DashboardSummary(
        active_policy_id=active,
        sleeper_outcome=latest_sleeper.outcome if latest_sleeper else None,
        inconclusive=inconclusive,
        attack_success_rate=succ_attacks / tot_attacks if tot_attacks else 0.0,
        benign_pass_rate=pass_benign / tot_benign if tot_benign else 0.0,
        total_attacks=tot_attacks,
        successful_attacks=succ_attacks,
        total_benign=tot_benign,
        passed_benign=pass_benign,
        findings_by_severity=sev_counts,
        open_findings=open_count,
        fixes_applied=revisions,
        recent_runs=run_repo.list_runs(target_id=target_id, limit=10),
        trend=[],
    )
