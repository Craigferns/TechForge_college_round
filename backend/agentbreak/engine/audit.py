"""Permission audit engine executing minimal policy generation, counterfactual attribution, and proof verification."""

from __future__ import annotations

import datetime
import sqlite3
import uuid

from agentbreak.domain.attribution import (
    attribute_exploits_to_tool,
    get_suggested_scope,
)
from agentbreak.domain.permissions import (
    NEEDED_PERMISSIONS,
    compute_permission_diff,
    get_tasks_using_tool,
)
from agentbreak.domain.policy import compute_policy_hash
from agentbreak.engine.runner import execute_run
from agentbreak.repo.audit_repo import AuditRepo
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.schemas.audit import (
    AuditCreate,
    AuditProof,
    PermissionAudit,
    PermissionRow,
)
from agentbreak.schemas.policy import Grant, Policy
from agentbreak.schemas.run import Run


def run_permission_audit(
    body: AuditCreate,
    conn: sqlite3.Connection,
) -> PermissionAudit:
    """Run an end-to-end permission audit for a target and policy."""
    audit_repo = AuditRepo(conn)
    policy_repo = PolicyRepo(conn)
    finding_repo = FindingRepo(conn)
    run_repo = RunRepo(conn)

    now = datetime.datetime.now(datetime.UTC).isoformat()
    audit_id = f"aud_{uuid.uuid4().hex[:8]}"

    # Fetch base policy
    base_policy = policy_repo.get(body.policy_id)
    if not base_policy:
        raise ValueError(f"Base policy '{body.policy_id}' not found.")

    granted_tools = [g.tool for g in base_policy.grants]
    needed_tools, excess_tools = compute_permission_diff(granted_tools)

    # Initial audit record in running state
    audit = PermissionAudit(
        id=audit_id,
        target_id=body.target_id,
        policy_id=body.policy_id,
        status="running",
        stage="Computing minimal policy",
        granted=granted_tools,
        needed=needed_tools,
        excess=excess_tools,
        rows=[],
        minimal_policy_id=None,
        proof=None,
        created_at=now,
    )
    audit_repo.create(audit)

    # 1. Ensure / create minimal policy (exact 8 needed tools)
    min_grants = [Grant(tool=t) for t in sorted(NEEDED_PERMISSIONS)]
    min_hash = compute_policy_hash(min_grants)
    minimal_policy = policy_repo.get_by_hash(min_hash)

    if not minimal_policy:
        minimal_policy_id = f"pol_min_{uuid.uuid4().hex[:6]}"
        minimal_policy = policy_repo.create(
            Policy(
                id=minimal_policy_id,
                name="Minimal Needed Policy",
                parent_id=base_policy.id,
                grants=min_grants,
                hash=min_hash,
                created_at=now,
            )
        )
    audit.minimal_policy_id = minimal_policy.id
    minimal_policy_id = minimal_policy.id

    # 2. Gather successful attack findings for target to evaluate attribution
    audit.stage = "Attributing exploits to permissions"
    audit_repo.update(audit)

    findings = finding_repo.list_findings(target_id=body.target_id, limit=100)
    # If no findings in DB yet, default to all 7 benchmark cases
    successful_cases = (
        [f.case_id for f in findings]
        if findings
        else ["AS-01", "AS-02", "AS-03", "AS-04", "AS-05", "AS-06", "AS-07"]
    )

    # 3. Build PermissionRow for all granted tools
    rows: list[PermissionRow] = []
    for tool in granted_tools:
        is_needed = tool in NEEDED_PERMISSIONS
        used_by = get_tasks_using_tool(tool)
        enabled_exploits = attribute_exploits_to_tool(tool, successful_cases)
        suggested_scope = get_suggested_scope(tool)

        rows.append(
            PermissionRow(
                tool=tool,
                status="needed" if is_needed else "excess",
                used_by_benign=used_by,
                enabled_exploits=enabled_exploits,
                suggested_scope=suggested_scope,
            )
        )
    audit.rows = rows

    # 4. Proof Run: Execute all 10 benign tasks under minimal policy
    audit.stage = "Verifying benign utility under minimal policy"
    audit_repo.update(audit)

    benign_task_ids = [f"BT-{i:02d}" for i in range(1, 11)]
    proof_run_ids: list[str] = []
    pass_count = 0

    for bt_id in benign_task_ids:
        p_run_id = f"run_proof_{uuid.uuid4().hex[:8]}"
        proof_run = Run(
            id=p_run_id,
            kind="benign",
            target_id=body.target_id,
            policy_id=minimal_policy_id,
            suite="acme",
            user_task_id=bt_id,
            status="queued",
            repro={"task_id": bt_id, "policy_id": minimal_policy_id},
            created_at=now,
        )
        run_repo.create(proof_run)
        completed = execute_run(p_run_id, conn=conn)
        proof_run_ids.append(completed.id)
        if completed.utility is True:
            pass_count += 1

    audit.proof = AuditProof(
        benign_total=len(benign_task_ids),
        benign_pass_under_minimal=pass_count,
        run_ids=proof_run_ids,
    )

    # 5. Mark Done
    finish_now = datetime.datetime.now(datetime.UTC).isoformat()
    audit.status = "done"
    audit.stage = "Complete"
    audit.finished_at = finish_now
    audit_repo.update(audit)

    return audit
