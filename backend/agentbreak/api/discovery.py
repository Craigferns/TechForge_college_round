"""Autonomous discovery campaign endpoints."""

from fastapi import APIRouter, HTTPException, status

from agentbreak.schemas import DiscoveryCampaign, DiscoveryCreate, Page

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post("", response_model=DiscoveryCampaign, status_code=status.HTTP_202_ACCEPTED)
def start_discovery(body: DiscoveryCreate) -> DiscoveryCampaign:
    """Launch an autonomous mutation campaign to discover novel exploit variants."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("", response_model=Page[DiscoveryCampaign])
def list_discovery_campaigns(limit: int = 50, offset: int = 0) -> Page[DiscoveryCampaign]:
    """List autonomous discovery campaigns."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/{campaign_id}", response_model=DiscoveryCampaign)
def get_discovery_campaign(campaign_id: str) -> DiscoveryCampaign:
    """Retrieve discovery campaign progress, mutations tried, and breakthroughs."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")
