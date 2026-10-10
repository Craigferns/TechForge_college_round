"""Target agent endpoints."""

from fastapi import APIRouter, HTTPException, status

from agentbreak.schemas import Target, TargetCreate, TargetTestResult

router = APIRouter(prefix="/targets", tags=["targets"])


@router.get("", response_model=list[Target])
def list_targets() -> list[Target]:
    """List all registered agent targets (scripted and OpenAI-compatible)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.post("", response_model=Target, status_code=status.HTTP_201_CREATED)
def create_target(body: TargetCreate) -> Target:
    """Register a new agent target with endpoint configuration."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/{target_id}", response_model=Target)
def get_target(target_id: str) -> Target:
    """Retrieve details and metadata for a specific agent target."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_target(target_id: str) -> None:
    """Delete a target configuration."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.post("/{target_id}/test", response_model=TargetTestResult)
def test_target(target_id: str) -> TargetTestResult:
    """Test connectivity and tool-calling responsiveness for a target agent."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")
