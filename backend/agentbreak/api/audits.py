"""Permission audit and attribution endpoints."""

from fastapi import APIRouter, HTTPException, status

from agentbreak.schemas import AuditCreate, FixSuggestion, Page, PermissionAudit

router = APIRouter(prefix="/audits", tags=["audits"])


@router.post("", response_model=PermissionAudit, status_code=status.HTTP_202_ACCEPTED)
def create_audit(body: AuditCreate) -> PermissionAudit:
    """Trigger a permission attribution audit comparing granted vs needed tools."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("", response_model=Page[PermissionAudit])
def list_audits(
    target_id: str | None = None, limit: int = 50, offset: int = 0
) -> Page[PermissionAudit]:
    """List permission attribution audit jobs."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/{audit_id}", response_model=PermissionAudit)
def get_audit(audit_id: str) -> PermissionAudit:
    """Retrieve full attribution breakdown, excess tools, and proof of utility."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/{audit_id}/fixes", response_model=list[FixSuggestion])
def list_fix_suggestions(audit_id: str) -> list[FixSuggestion]:
    """List candidate policy fixes suggested by the audit findings."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.post("/{audit_id}/fixes/evaluate-all", status_code=status.HTTP_202_ACCEPTED)
def evaluate_all_fixes(audit_id: str) -> dict[str, list[str]]:
    """Queue parallel price tag evaluation for all suggested fixes."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")
