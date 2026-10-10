"""Permission audit and attribution endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from agentbreak.api.deps import DbDep
from agentbreak.domain.candidate_fixes import generate_candidate_fixes
from agentbreak.engine.audit import run_permission_audit
from agentbreak.repo.audit_repo import AuditRepo
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.schemas import AuditCreate, FixSuggestion, Page, PermissionAudit

router = APIRouter(prefix="/audits", tags=["audits"])


@router.post("", response_model=PermissionAudit, status_code=status.HTTP_202_ACCEPTED)
def create_audit(body: AuditCreate, db: DbDep) -> PermissionAudit:
    """Trigger a permission attribution audit comparing granted vs needed tools."""
    target_repo = TargetRepo(db)
    policy_repo = PolicyRepo(db)

    target = target_repo.get(body.target_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target '{body.target_id}' not found.",
        )

    policy = policy_repo.get(body.policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{body.policy_id}' not found.",
        )

    return run_permission_audit(body, conn=db)


@router.get("", response_model=Page[PermissionAudit])
def list_audits(
    db: DbDep,
    target_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[PermissionAudit]:
    """List permission attribution audit jobs."""
    repo = AuditRepo(db)
    items = repo.list_audits(target_id=target_id, limit=limit, offset=offset)
    total = repo.count_audits(target_id=target_id)
    return Page[PermissionAudit](
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{audit_id}", response_model=PermissionAudit)
def get_audit(audit_id: str, db: DbDep) -> PermissionAudit:
    """Retrieve full attribution breakdown, excess tools, and proof of utility."""
    repo = AuditRepo(db)
    audit = repo.get(audit_id)
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit '{audit_id}' not found.",
        )
    return audit


@router.get("/{audit_id}/fixes", response_model=list[FixSuggestion])
def list_fix_suggestions(audit_id: str, db: DbDep) -> list[FixSuggestion]:
    """List candidate policy fixes suggested by the audit findings."""
    audit_repo = AuditRepo(db)
    target_repo = TargetRepo(db)

    audit = audit_repo.get(audit_id)
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit '{audit_id}' not found.",
        )

    target = target_repo.get(audit.target_id)
    target_kind = target.kind if target else "scripted"

    return generate_candidate_fixes(audit, target_kind=target_kind)


@router.post("/{audit_id}/fixes/evaluate-all", status_code=status.HTTP_202_ACCEPTED)
def evaluate_all_fixes(audit_id: str, db: DbDep) -> dict[str, list[str]]:
    """Queue parallel price tag evaluation for all suggested fixes."""
    from agentbreak.engine.fixes import evaluate_all_suggestions

    evals = evaluate_all_suggestions(audit_id, conn=db)
    return {"eval_ids": [ev.id for ev in evals]}
