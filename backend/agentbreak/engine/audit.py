"""Permission audit execution engine (PLAN.md §10 / Phase 8)."""

from __future__ import annotations

import datetime
import sqlite3
import uuid
from typing import Literal

from agentbreak.config import get_settings
from agentbreak.db import get_connection
from agentbreak.domain.attribution import enabling_exploits, observed_exploits
from agentbreak.engine.measure import child_policy, measure_policy, observed_domains, tools_used
from agentbreak.repo.audit_repo import AuditRepo
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.schemas.audit import (
    AuditCreate,
    AuditProof,
    PermissionAudit,
    PermissionRow,
    SuggestedScope,
)
from agentbreak.targets.base import BaseTarget


def utc_now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def execute_permission_audit(
    audit_input: AuditCreate | str,
    conn: sqlite3.Connection | None = None,
    target_override: BaseTarget | None = None,
) -> PermissionAudit:
    """Execute complete permission audit lifecycle:

    1. Derive Granted, Needed, Excess from policy under test and benign ground truth.
    2. Create minimal policy containing exactly Needed tools (child of audited policy).
    3. Proof run: execute all 10 benign tasks under minimal policy, verifying 10/10 pass.
    4. Exploit-to-permission attribution with counterfactual validations.
    5. Derive suggested argument scopes for needed tools enabling exploits.
    """
    settings = get_settings()
    owns_conn = conn is None
    active_conn = conn if conn is not None else get_connection(settings.db_path)

    audit_repo = AuditRepo(active_conn)
    policy_repo = PolicyRepo(active_conn)

    audit_id: str
    target_id: str
    policy_id: str
    verify_counterfactual: bool = True

    if isinstance(audit_input, str):
        audit_id = audit_input
        existing = audit_repo.get(audit_id)
        if not existing:
            if owns_conn:
                active_conn.close()
            raise ValueError(f"Audit '{audit_id}' not found.")
        target_id = existing.target_id
        policy_id = existing.policy_id
        audit = existing
    else:
        audit_id = f"aud_{uuid.uuid4().hex[:12]}"
        target_id = audit_input.target_id
        policy_id = audit_input.policy_id
        verify_counterfactual = audit_input.verify_counterfactual

        audit = PermissionAudit(
            id=audit_id,
            target_id=target_id,
            policy_id=policy_id,
            status="queued",
            stage="initializing",
            created_at=utc_now_iso(),
        )
        audit_repo.create(audit)

    audit.status = "running"
    audit.stage = "deriving_minimal_policy"
    audit_repo.update(audit)

    try:
        # 1. Measure the policy under test: every number below comes from these runs.
        base_policy = policy_repo.get(policy_id)
        if not base_policy:
            raise ValueError(f"Policy '{policy_id}' not found.")
        tag: dict[str, object] = {"audit_id": audit_id}
        base = measure_policy(policy_id, target_id, active_conn, target_override, tag)
        if base.inconclusive:
            raise RuntimeError(
                f"Baseline runs errored for {sorted(base.inconclusive)}; audit would be unsound."
            )

        granted_set = {g.tool for g in base_policy.grants}
        used_by = tools_used(base, base.benign_passed)  # exercised by legitimate work
        needed_set = set(used_by) & granted_set
        excess_set = granted_set - needed_set

        audit.granted = sorted(granted_set)
        audit.needed = sorted(needed_set)
        audit.excess = sorted(excess_set)

        # 2. Minimal policy = base grants (constraints kept) limited to the needed tools.
        min_policy = child_policy(
            active_conn,
            base_policy,
            [g for g in base_policy.grants if g.tool in needed_set],
            f"Minimal policy for {base_policy.name}",
        )
        audit.minimal_policy_id = min_policy.id

        # 3. Proof: re-measure under the minimal policy.
        audit.stage = "verifying_minimal_policy_proof"
        audit_repo.update(audit)
        minimal = measure_policy(min_policy.id, target_id, active_conn, target_override, tag)
        audit.proof = AuditProof(
            benign_total=len(base.benign_passed),
            benign_pass_under_minimal=len(base.benign_passed & minimal.benign_passed),
            run_ids=list(minimal.run_ids),
        )

        # 4. Attribution: one counterfactual measurement per granted tool.
        audit.stage = "attributing_exploits"
        audit_repo.update(audit)
        findings, _ = FindingRepo(active_conn).list_findings(target_id=target_id, limit=200)
        finding_ids = {f.case_id: f.id for f in findings}
        exploit_tools = tools_used(base, base.exploited)

        rows: list[PermissionRow] = []
        for tool in sorted(granted_set):
            if verify_counterfactual:
                cf = measure_policy(
                    child_policy(
                        active_conn,
                        base_policy,
                        [g for g in base_policy.grants if g.tool != tool],
                        f"{base_policy.name} without {tool}",
                    ).id,
                    target_id,
                    active_conn,
                    target_override,
                    tag,
                )
                exploits = enabling_exploits(
                    base.exploited,
                    cf.resisted,
                    len(base.benign_passed & cf.benign_failed),
                    finding_ids,
                )
            else:
                exploits = observed_exploits(set(exploit_tools.get(tool, [])), finding_ids)

            suggested = None
            if tool in needed_set and exploits:
                args, domains = observed_domains(base, tool)
                if args and domains:
                    suggested = SuggestedScope(args=args, domain_allowlist=domains)

            status_val: Literal["needed", "excess"] = "needed" if tool in needed_set else "excess"
            rows.append(
                PermissionRow(
                    tool=tool,
                    status=status_val,
                    used_by_benign=used_by.get(tool, []),
                    enabled_exploits=exploits,
                    suggested_scope=suggested,
                )
            )

        audit.rows = rows
        audit.status = "done"
        audit.stage = "complete"
        audit.finished_at = utc_now_iso()
        audit_repo.update(audit)

    except Exception as exc:
        audit.status = "error"
        audit.stage = f"error: {str(exc)}"
        audit.finished_at = utc_now_iso()
        audit_repo.update(audit)
    finally:
        if owns_conn:
            active_conn.close()

    updated = audit_repo.get(audit_id)
    if not updated:
        raise RuntimeError(f"Audit '{audit_id}' disappeared after run.")
    return updated
