"""Attack and benign run execution and replay endpoints."""

from fastapi import APIRouter, HTTPException, Query, status

from agentbreak.schemas import (
    AttackGraph,
    Page,
    Run,
    RunCreate,
    RunSummary,
    SnapshotPair,
    TraceStep,
    Verdict,
)

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_runs(body: RunCreate) -> dict[str, list[str]]:
    """Queue execution of single or batched attack and utility runs."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("", response_model=Page[RunSummary])
def list_runs(
    target_id: str | None = None,
    policy_id: str | None = None,
    kind: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    scenario_id: str | None = None,
    ids: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[RunSummary]:
    """List historical evaluation runs with pagination and filters."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/{run_id}", response_model=Run)
def get_run(run_id: str) -> Run:
    """Retrieve top-level run execution summary, verdict, and metadata."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/{run_id}/trace", response_model=list[TraceStep])
def get_run_trace(run_id: str) -> list[TraceStep]:
    """Retrieve full step-by-step tool invocation trace with highlighted vectors."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/{run_id}/snapshots", response_model=SnapshotPair)
def get_run_snapshots(run_id: str) -> SnapshotPair:
    """Retrieve PRE and POST environment snapshots for state diff verification."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/{run_id}/graph", response_model=AttackGraph)
def get_run_graph(run_id: str) -> AttackGraph:
    """Retrieve causal attack graph connecting attack vector to exploit effect."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.post("/{run_id}/verify", response_model=Verdict)
def verify_run(run_id: str) -> Verdict:
    """Deterministically re-verify environment state diff predicates and canary tokens."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.post("/{run_id}/cancel", response_model=Run)
def cancel_run(run_id: str) -> Run:
    """Cancel an active or queued run."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.post("/{run_id}/replay", status_code=status.HTTP_202_ACCEPTED)
def replay_run(run_id: str) -> dict[str, list[str]]:
    """Queue a deterministic replay of a previous run under identical initial conditions."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")
