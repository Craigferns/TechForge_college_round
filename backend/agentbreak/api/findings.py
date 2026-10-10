"""Findings and aggregate graph endpoints."""

from fastapi import APIRouter, HTTPException, status

from agentbreak.schemas import AttackGraph, Finding, FindingUpdate, Page

router = APIRouter(tags=["findings"])


@router.get("/findings", response_model=Page[Finding])
def list_findings(
    severity: str | None = None,
    status_filter: str | None = None,
    scenario_id: str | None = None,
    target_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[Finding]:
    """List deduplicated vulnerability findings with severity filters."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/findings/{finding_id}", response_model=Finding)
def get_finding(finding_id: str) -> Finding:
    """Retrieve details, carrier traces, and causal attribution for a finding."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.patch("/findings/{finding_id}", response_model=Finding)
def update_finding(finding_id: str, body: FindingUpdate) -> Finding:
    """Update status (open, acknowledged, fixed, dismissed) or notes on a finding."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/graph", response_model=AttackGraph)
def get_aggregate_graph(target_id: str | None = None) -> AttackGraph:
    """Retrieve multi-finding aggregated attack graph across all evaluated scenarios."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")
