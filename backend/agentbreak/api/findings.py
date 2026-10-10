from fastapi import APIRouter, HTTPException, status

from agentbreak.api.deps import DbDep
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.schemas import AttackGraph, Finding, FindingUpdate, Page

router = APIRouter(tags=["findings"])


@router.get("/findings", response_model=Page[Finding])
def list_findings(
    db: DbDep,
    severity: str | None = None,
    status_filter: str | None = None,
    scenario_id: str | None = None,
    target_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[Finding]:
    """List deduplicated vulnerability findings with severity filters."""
    repo = FindingRepo(db)
    items, total = repo.list_findings(
        severity=severity,
        status_filter=status_filter,
        scenario_id=scenario_id,
        target_id=target_id,
        limit=limit,
        offset=offset,
    )
    return Page[Finding](items=items, total=total, limit=limit, offset=offset)


@router.get("/findings/{finding_id}", response_model=Finding)
def get_finding(finding_id: str, db: DbDep) -> Finding:
    """Retrieve details, carrier traces, and causal attribution for a finding."""
    repo = FindingRepo(db)
    finding = repo.get(finding_id)
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found.",
        )
    return finding


@router.patch("/findings/{finding_id}", response_model=Finding)
def update_finding(finding_id: str, body: FindingUpdate, db: DbDep) -> Finding:
    """Update status (open, acknowledged, fixed, dismissed) or notes on a finding."""
    repo = FindingRepo(db)
    existing = repo.get(finding_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found.",
        )
    updated = repo.update_status(finding_id, body.status)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update finding status.",
        )
    return updated


@router.get("/graph", response_model=AttackGraph)
def get_aggregate_graph(db: DbDep, target_id: str | None = None) -> AttackGraph:
    """Retrieve multi-finding aggregated attack graph across all evaluated scenarios."""
    from agentbreak.domain.graph import build_aggregate_graph

    return build_aggregate_graph(db, target_id=target_id)
