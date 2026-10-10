"""Policy management endpoints."""

from fastapi import APIRouter, HTTPException, status

from agentbreak.schemas import Policy, PolicyCreate, PolicyDiff

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=list[Policy])
def list_policies() -> list[Policy]:
    """List all immutable permission policies and their grant specifications."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.post("", response_model=Policy, status_code=status.HTTP_201_CREATED)
def create_policy(body: PolicyCreate) -> Policy:
    """Register a new immutable permission policy with SHA-256 canonical hash."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/{policy_id}", response_model=Policy)
def get_policy(policy_id: str) -> Policy:
    """Retrieve full grant specification and lineage for a security policy."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/{policy_a}/diff/{policy_b}", response_model=PolicyDiff)
def diff_policies(policy_a: str, policy_b: str) -> PolicyDiff:
    """Compute structural grant delta between two security policies."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")
