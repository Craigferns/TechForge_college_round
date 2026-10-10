from fastapi import APIRouter, HTTPException, status

from agentbreak.api.deps import DbDep
from agentbreak.engine.audit import execute_permission_audit
from agentbreak.engine.fixes import suggest_fixes
from agentbreak.repo.audit_repo import AuditRepo
from agentbreak.schemas import AuditCreate, FixSuggestion, Page, PermissionAudit

router = APIRouter(prefix="/audits", tags=["audits"])


@router.post("", response_model=PermissionAudit, status_code=status.HTTP_202_ACCEPTED)
def create_audit(body: AuditCreate, db: DbDep) -> PermissionAudit:
    """Trigger a permission attribution audit comparing granted vs needed tools."""
    return execute_permission_audit(body, conn=db)


@router.get("", response_model=Page[PermissionAudit])
def list_audits(
    db: DbDep,
    target_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[PermissionAudit]:
    """List permission attribution audit jobs."""
    repo = AuditRepo(db)
    items, total = repo.list(target_id=target_id, limit=limit, offset=offset)
    return Page[PermissionAudit](items=items, total=total, limit=limit, offset=offset)


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
    """List candidate policy fixes suggested deterministically by the audit findings."""
    audit = AuditRepo(db).get(audit_id)
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit '{audit_id}' not found.",
        )
    return suggest_fixes(audit)


@router.post("/{audit_id}/fixes/evaluate-all", status_code=status.HTTP_202_ACCEPTED)
def evaluate_all_fixes(audit_id: str, db: DbDep) -> dict[str, list[str]]:
    """Queue parallel price tag evaluation for all suggested fixes."""
    suggestions = list_fix_suggestions(audit_id, db)
    audit = get_audit(audit_id, db)

    from agentbreak.engine.fixes import evaluate_fix
    from agentbreak.schemas.fix import FixEvalCreate

    eval_ids: list[str] = []
    for sug in suggestions:
        eval_res = evaluate_fix(
            FixEvalCreate(
                target_id=audit.target_id,
                base_policy_id=audit.policy_id,
                fix=sug.fix,
            ),
            audit_id=audit_id,
            conn=db,
        )
        eval_ids.append(eval_res.id)

    return {"fix_eval_ids": eval_ids}
