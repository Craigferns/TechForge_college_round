"""Autonomous discovery campaign endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from agentbreak.api.deps import DbDep
from agentbreak.engine.discovery import run_discovery_campaign
from agentbreak.repo.discovery_repo import DiscoveryRepo
from agentbreak.schemas import DiscoveryCampaign, DiscoveryCreate, Page

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post("", response_model=DiscoveryCampaign, status_code=status.HTTP_202_ACCEPTED)
def start_discovery(body: DiscoveryCreate, db: DbDep) -> DiscoveryCampaign:
    """Launch an autonomous mutation campaign to discover novel exploit variants."""
    campaign = run_discovery_campaign(body, conn=db)
    return campaign


@router.get("", response_model=Page[DiscoveryCampaign])
def list_discovery_campaigns(
    db: DbDep, limit: int = 50, offset: int = 0
) -> Page[DiscoveryCampaign]:
    """List autonomous discovery campaigns."""
    repo = DiscoveryRepo(db)
    items = repo.list_campaigns(limit=limit, offset=offset)
    total = repo.count_campaigns()
    return Page[DiscoveryCampaign](
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{campaign_id}", response_model=DiscoveryCampaign)
def get_discovery_campaign(campaign_id: str, db: DbDep) -> DiscoveryCampaign:
    """Retrieve discovery campaign progress, mutations tried, and breakthroughs."""
    repo = DiscoveryRepo(db)
    campaign = repo.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery campaign '{campaign_id}' not found.",
        )
    return campaign
