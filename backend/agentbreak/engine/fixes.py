"""Fix evaluation engine deriving price tags and applying policy mitigations (PLAN.md §11 / Phase 9)."""

from __future__ import annotations

import datetime
import sqlite3
import uuid

from agentbreak.config import get_settings
from agentbreak.db import get_connection
from agentbreak.domain.pricing import compute_pareto_dominance
from agentbreak.engine.measure import child_policy, measure_policy
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.repo.fix_repo import FixRepo
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.schemas.audit import PermissionAudit
from agentbreak.schemas.fix import (
    FixEval,
    FixEvalCreate,
    FixEvalDetails,
    FixSpec,
    FixSuggestion,
    PriceTag,
)
from agentbreak.schemas.policy import ArgConstraint, Grant, Policy
from agentbreak.targets.base import BaseTarget


def utc_now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


IMPLEMENTED_FIX_KINDS = ("remove_permission", "restrict_arg")


def _fixed_grants(base: Policy, fix: FixSpec) -> list[Grant]:
    if fix.kind not in IMPLEMENTED_FIX_KINDS:
        # Fail closed: an unimplemented fix would otherwise "evaluate" as a no-op policy.
        raise ValueError(f"Fix kind '{fix.kind}' is not implemented; only {IMPLEMENTED_FIX_KINDS}.")
    if not fix.tool or fix.tool not in {g.tool for g in base.grants}:
        raise ValueError(f"Tool '{fix.tool}' is not granted by policy '{base.id}'.")
    if fix.kind == "restrict_arg" and (not fix.args or not fix.domains):
        raise ValueError("restrict_arg needs at least one arg and one allowed domain.")
    grants: list[Grant] = []
    for g in base.grants:
        if g.tool != fix.tool:
            grants.append(g)
        elif fix.kind == "restrict_arg":
            grants.append(
                Grant(
                    tool=g.tool,
                    constraints=[
                        ArgConstraint(arg=a, kind="domain_allowlist", values=fix.domains)
                        for a in fix.args
                    ],
                )
            )
    return grants


def evaluate_fix(
    create_input: FixEvalCreate,
    audit_id: str | None = None,
    conn: sqlite3.Connection | None = None,
    target_override: BaseTarget | None = None,
    retest_of: str | None = None,
) -> FixEval:
    """Measure a fix: run every attack and benign task under the base and the fixed policy.

    blocked  = exploited under base AND resisted under fix (errored runs excluded)
    broken   = passed under base AND failed under fix (errored runs excluded)
    The denominators are what actually succeeded/passed under the base policy.
    """
    settings = get_settings()
    owns_conn = conn is None
    active_conn = conn if conn is not None else get_connection(settings.db_path)
    try:
        policy_repo = PolicyRepo(active_conn)
        base = policy_repo.get(create_input.base_policy_id)
        if base is None:
            raise ValueError(f"Policy '{create_input.base_policy_id}' not found.")
        fix = create_input.fix
        fixed = child_policy(
            active_conn, base, _fixed_grants(base, fix), f"{base.name} + {fix.kind}:{fix.tool}"
        )
        fix_id = f"fix_{uuid.uuid4().hex[:8]}"
        tag: dict[str, object] = {"fix_eval_id": fix_id}
        before = measure_policy(base.id, create_input.target_id, active_conn, target_override, tag)
        after = measure_policy(fixed.id, create_input.target_id, active_conn, target_override, tag)

        blocked = sorted(before.exploited & after.resisted)
        broken = sorted(before.benign_passed & after.benign_failed)
        fix_eval = FixEval(
            id=fix_id,
            audit_id=audit_id,
            target_id=create_input.target_id,
            base_policy_id=base.id,
            fix=fix,
            result_policy_id=fixed.id,
            trials=create_input.trials,
            status="done",
            price_tag=PriceTag(
                attacks_blocked=len(blocked),
                attacks_total=len(before.exploited),
                tasks_broken=len(broken),
                benign_total=len(before.benign_passed),
            ),
            details=FixEvalDetails(
                blocked_cases=blocked,
                still_exploitable=sorted(after.exploited),
                broken_tasks=broken,
                inconclusive=sorted(before.inconclusive | after.inconclusive),
                sleeper_outcome=after.sleeper_outcome,
                run_ids=list(after.run_ids),
                before_runs=dict(before.keyed_runs),
                after_runs=dict(after.keyed_runs),
            ),
            retest_of=retest_of,
            created_at=utc_now_iso(),
            finished_at=utc_now_iso(),
        )
        fix_repo = FixRepo(active_conn)
        fix_repo.create(fix_eval)
        _refresh_pareto(fix_repo, fix_eval.target_id, base.id)
        return fix_repo.get(fix_id) or fix_eval
    finally:
        if owns_conn:
            active_conn.close()


def _refresh_pareto(fix_repo: FixRepo, target_id: str, base_policy_id: str) -> None:
    """Recompute set-based Pareto flags (PLAN §11.2) across fixes of the same base policy."""
    siblings = [
        f
        for f in fix_repo.list(target_id=target_id, limit=500)[0]
        if f.base_policy_id == base_policy_id and f.details is not None
    ]
    flags = compute_pareto_dominance(
        [
            {"blocked_cases": f.details.blocked_cases, "broken_tasks": f.details.broken_tasks}
            for f in siblings
            if f.details is not None
        ]
    )
    for f, flag in zip(siblings, flags, strict=True):
        fix_repo.set_pareto(f.id, flag)


def suggest_fixes(audit: PermissionAudit) -> list[FixSuggestion]:
    """Candidate fixes derived only from the audit's measured evidence."""
    out: list[FixSuggestion] = []
    for row in audit.rows:
        cases = [e.case_id for e in row.enabled_exploits]
        if not cases:
            continue
        out.append(
            FixSuggestion(
                id=f"sug_{len(out) + 1:02d}",
                fix=FixSpec(kind="remove_permission", tool=row.tool),
                title=f"Remove '{row.tool}'",
                description=(
                    f"Revoke '{row.tool}'. Counterfactual runs show it enables {', '.join(cases)}; "
                    f"benign tasks using it: {', '.join(row.used_by_benign) or 'none'}."
                ),
                targeted_exploits=cases,
            )
        )
    for row in audit.rows:
        scope = row.suggested_scope
        if scope is None:
            continue
        out.append(
            FixSuggestion(
                id=f"sug_{len(out) + 1:02d}",
                fix=FixSpec(
                    kind="restrict_arg",
                    tool=row.tool,
                    args=scope.args,
                    domains=scope.domain_allowlist,
                ),
                title=f"Restrict '{row.tool}' {scope.args} to {scope.domain_allowlist}",
                description=(
                    f"Allow only the domains legitimate tasks were observed using "
                    f"({', '.join(scope.domain_allowlist)}) on every recipient argument."
                ),
                targeted_exploits=[e.case_id for e in row.enabled_exploits],
            )
        )
    return out


def apply_fix_eval(fix_eval_id: str, conn: sqlite3.Connection) -> Policy:
    """Apply evaluated fix: updates target's active_policy_id and transitions finding statuses to 'fixed'."""
    fix_repo = FixRepo(conn)
    target_repo = TargetRepo(conn)
    policy_repo = PolicyRepo(conn)
    finding_repo = FindingRepo(conn)

    fix_eval = fix_repo.get(fix_eval_id)
    if not fix_eval:
        raise ValueError(f"FixEval '{fix_eval_id}' not found.")

    if not fix_eval.result_policy_id:
        raise ValueError(f"FixEval '{fix_eval_id}' has no result policy.")

    result_policy = policy_repo.get(fix_eval.result_policy_id)
    if not result_policy:
        raise ValueError(f"Result policy '{fix_eval.result_policy_id}' not found.")

    # 1. Update target's active_policy_id
    target_repo.update_active_policy(fix_eval.target_id, result_policy.id)

    # 2. Transition findings for blocked cases to 'fixed'
    blocked_cases = fix_eval.details.blocked_cases if fix_eval.details else []
    findings, _ = finding_repo.list_findings(target_id=fix_eval.target_id, limit=200)

    for f in findings:
        if f.case_id in blocked_cases:
            finding_repo.update_status(f.id, "fixed")

    return result_policy
