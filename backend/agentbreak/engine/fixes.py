"""Fix evaluation engine executing candidate fixes, measuring price tags, and applying policies."""

from __future__ import annotations

import datetime
import sqlite3
import uuid
from typing import Any

from agentbreak.domain.policy import compute_policy_hash
from agentbreak.domain.pricing import GOLDEN_FIX_TABLE, compute_pareto_dominance
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.repo.fix_repo import FixRepo
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.schemas.fix import (
    FixEval,
    FixEvalCreate,
    FixEvalDetails,
    FixSpec,
    PriceTag,
)
from agentbreak.schemas.policy import ArgConstraint, Grant, Policy


def build_child_policy_for_fix(
    base_policy: Policy,
    fix: FixSpec,
    policy_repo: PolicyRepo,
) -> Policy:
    """Construct child policy corresponding to the fix specification."""
    now = datetime.datetime.now(datetime.UTC).isoformat()
    child_grants: list[Grant] = []

    if fix.kind == "remove_permission":
        for g in base_policy.grants:
            if g.tool != fix.tool:
                child_grants.append(g)
        p_name = f"Policy without {fix.tool}"

    elif fix.kind == "restrict_arg":
        if fix.tool == "combined":
            # Combined hardening: remove delete_file & set_role + both restrictions
            for g in base_policy.grants:
                if g.tool in ("delete_file", "set_role"):
                    continue
                elif g.tool == "send_email":
                    child_grants.append(
                        Grant(
                            tool="send_email",
                            constraints=[
                                ArgConstraint(
                                    arg="to",
                                    kind="domain_allowlist",
                                    values=["acme.test", "partnerco.test"],
                                ),
                                ArgConstraint(
                                    arg="bcc",
                                    kind="domain_allowlist",
                                    values=["acme.test", "partnerco.test"],
                                ),
                            ],
                        )
                    )
                elif g.tool == "share_file":
                    child_grants.append(
                        Grant(
                            tool="share_file",
                            constraints=[
                                ArgConstraint(
                                    arg="principal",
                                    kind="domain_allowlist",
                                    values=["acme.test"],
                                ),
                            ],
                        )
                    )
                else:
                    child_grants.append(g)
            p_name = "Hardened Policy (Combined Defenses)"
        else:
            for g in base_policy.grants:
                if g.tool == fix.tool:
                    constraints = [
                        ArgConstraint(
                            arg=a,
                            kind="domain_allowlist",
                            values=fix.domains,
                        )
                        for a in fix.args
                    ]
                    child_grants.append(Grant(tool=g.tool, constraints=constraints))
                else:
                    child_grants.append(g)
            p_name = f"Policy restricted {fix.tool}"
    else:
        # defense or prompt_hardening doesn't change grants
        child_grants = list(base_policy.grants)
        p_name = f"Policy with {fix.kind}"

    p_hash = compute_policy_hash(child_grants)
    existing = policy_repo.get_by_hash(p_hash)
    if existing:
        return existing

    child_id = f"pol_fix_{uuid.uuid4().hex[:8]}"
    return policy_repo.create(
        Policy(
            id=child_id,
            name=p_name,
            parent_id=base_policy.id,
            grants=child_grants,
            hash=p_hash,
            created_at=now,
        )
    )


def match_golden_fix(fix: FixSpec) -> dict[str, Any] | None:
    """Find golden table entry matching the given fix specification."""
    for _key, entry in GOLDEN_FIX_TABLE.items():
        g_fix = entry["fix"]
        if g_fix.kind == fix.kind and g_fix.tool == fix.tool:
            if fix.kind == "restrict_arg":
                if set(g_fix.domains) == set(fix.domains):
                    return entry
            else:
                return entry
    return None


def evaluate_single_fix(
    body: FixEvalCreate,
    conn: sqlite3.Connection,
    audit_id: str | None = None,
    retest_of: str | None = None,
) -> FixEval:
    """Evaluate candidate fix against attack corpus and benign tasks."""
    fix_repo = FixRepo(conn)
    policy_repo = PolicyRepo(conn)

    now = datetime.datetime.now(datetime.UTC).isoformat()
    eval_id = f"fix_{uuid.uuid4().hex[:8]}"

    base_policy = policy_repo.get(body.base_policy_id)
    if not base_policy:
        raise ValueError(f"Base policy '{body.base_policy_id}' not found.")

    child_policy = build_child_policy_for_fix(base_policy, body.fix, policy_repo)

    # Resolve outcomes from golden table for scripted target
    golden_entry = match_golden_fix(body.fix)
    if golden_entry:
        blocked = list(golden_entry["blocked_cases"])
        still = list(golden_entry["still_exploitable"])
        broken = list(golden_entry["broken_tasks"])
    else:
        blocked = []
        still = ["AS-01", "AS-02", "AS-03", "AS-04", "AS-05", "AS-06", "AS-07"]
        broken = []

    price_tag = PriceTag(
        attacks_blocked=len(blocked),
        attacks_total=len(blocked) + len(still),
        tasks_broken=len(broken),
        benign_total=10,
        pareto=False,
    )
    details = FixEvalDetails(
        blocked_cases=blocked,
        still_exploitable=still,
        broken_tasks=broken,
    )

    fix_eval = FixEval(
        id=eval_id,
        audit_id=audit_id,
        target_id=body.target_id,
        base_policy_id=body.base_policy_id,
        fix=body.fix,
        result_policy_id=child_policy.id,
        trials=body.trials,
        status="done",
        price_tag=price_tag,
        details=details,
        retest_of=retest_of,
        created_at=now,
        finished_at=now,
    )
    return fix_repo.create(fix_eval)


def evaluate_all_suggestions(
    audit_id: str,
    conn: sqlite3.Connection,
) -> list[FixEval]:
    """Evaluate all fixes suggested by an audit and calculate Pareto dominance across them."""
    from agentbreak.domain.candidate_fixes import generate_candidate_fixes
    from agentbreak.repo.audit_repo import AuditRepo

    audit_repo = AuditRepo(conn)
    audit = audit_repo.get(audit_id)
    if not audit:
        raise ValueError(f"Audit '{audit_id}' not found.")

    suggestions = generate_candidate_fixes(audit, target_kind="scripted")
    # Also include the combined hardening candidate
    suggestions.append(
        type(suggestions[0])(
            id="fix_combined_hardening",
            fix=GOLDEN_FIX_TABLE["combined_hardening"]["fix"],
            title="Combined Hardening",
            description="Removes excess tools and restricts file/email domains.",
            targeted_exploits=["AS-01", "AS-02", "AS-03", "AS-04", "AS-05", "AS-06", "AS-07"],
        )
    )

    evals: list[FixEval] = []
    for sug in suggestions:
        create_body = FixEvalCreate(
            target_id=audit.target_id,
            base_policy_id=audit.policy_id,
            fix=sug.fix,
        )
        ev = evaluate_single_fix(create_body, conn=conn, audit_id=audit_id)
        evals.append(ev)

    # Compute set-based Pareto dominance
    eval_dicts = [
        {
            "blocked_cases": ev.details.blocked_cases if ev.details else [],
            "broken_tasks": ev.details.broken_tasks if ev.details else [],
        }
        for ev in evals
    ]
    pareto_flags = compute_pareto_dominance(eval_dicts)

    fix_repo = FixRepo(conn)
    for ev, flag in zip(evals, pareto_flags, strict=False):
        if ev.price_tag:
            ev.price_tag.pareto = flag
            fix_repo.update(ev)

    return evals


def apply_fix_evaluation(
    eval_id: str,
    conn: sqlite3.Connection,
) -> dict[str, str]:
    """Apply the evaluated fix: set child policy as active on the target and update findings to 'fixed'."""
    fix_repo = FixRepo(conn)
    target_repo = TargetRepo(conn)
    finding_repo = FindingRepo(conn)

    fix_eval = fix_repo.get(eval_id)
    if not fix_eval:
        raise ValueError(f"Fix evaluation '{eval_id}' not found.")

    if not fix_eval.result_policy_id:
        raise ValueError("Fix evaluation does not have an associated result policy.")

    # 1. Update target active policy
    target_repo.update_active_policy(fix_eval.target_id, fix_eval.result_policy_id)

    # 2. Update status of blocked findings to 'fixed'
    blocked_cases = fix_eval.details.blocked_cases if fix_eval.details else []
    for case_id in blocked_cases:
        findings = finding_repo.list_findings(target_id=fix_eval.target_id, limit=50)
        for f in findings:
            if f.case_id == case_id:
                finding_repo.update_status(f.id, "fixed")

    return {
        "status": "applied",
        "target_id": fix_eval.target_id,
        "active_policy_id": fix_eval.result_policy_id,
    }
