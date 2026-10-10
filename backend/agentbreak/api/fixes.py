"""Fix evaluation and application endpoints."""

from fastapi import APIRouter, HTTPException, status

from agentbreak.schemas import FixEval, FixEvalCreate, Page, Policy

router = APIRouter(prefix="/fix-evals", tags=["fixes"])


@router.post("", response_model=FixEval, status_code=status.HTTP_202_ACCEPTED)
def create_fix_eval(body: FixEvalCreate) -> FixEval:
    """Queue empirical evaluation of a proposed fix across attacks and benign tasks."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("", response_model=Page[FixEval])
def list_fix_evals(
    audit_id: str | None = None,
    target_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[FixEval]:
    """List fix evaluations with two-dimensional price tags and Pareto statuses."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/{fix_eval_id}", response_model=FixEval)
def get_fix_eval(fix_eval_id: str) -> FixEval:
    """Retrieve detailed results, blocked cases, and broken tasks for a fix evaluation."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.post("/{fix_eval_id}/retest", response_model=FixEval, status_code=status.HTTP_202_ACCEPTED)
def retest_fix(fix_eval_id: str) -> FixEval:
    """Trigger a fresh retest of the evaluated mitigation."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.post("/{fix_eval_id}/apply", response_model=Policy)
def apply_fix(fix_eval_id: str) -> Policy:
    """Generate and activate the child hardened security policy derived from this fix."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")
