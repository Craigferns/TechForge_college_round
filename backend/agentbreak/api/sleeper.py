"""Sleeper mode multi-session endpoints."""

from fastapi import APIRouter, HTTPException, status

from agentbreak.schemas import Page, SleeperRun, SleeperRunCreate

router = APIRouter(prefix="/sleeper-runs", tags=["sleeper"])


@router.post("", response_model=SleeperRun, status_code=status.HTTP_202_ACCEPTED)
def create_sleeper_run(body: SleeperRunCreate) -> SleeperRun:
    """Launch a multi-session sleeper evaluation (Plant -> Gap -> Trigger)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("", response_model=Page[SleeperRun])
def list_sleeper_runs(
    target_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[SleeperRun]:
    """List cross-session sleeper test runs and their outcomes."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/{sleeper_id}", response_model=SleeperRun)
def get_sleeper_run(sleeper_id: str) -> SleeperRun:
    """Retrieve multi-session lifecycle data and persistent memory diffs."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")
