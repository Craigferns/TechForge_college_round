"""Fix evaluation and application endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from agentbreak.api.deps import DbDep
from agentbreak.engine.fixes import (
    apply_fix_evaluation,
    evaluate_single_fix,
)
from agentbreak.repo.fix_repo import FixRepo
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.schemas import FixEval, FixEvalCreate, Page, Policy

router = APIRouter(prefix="/fix-evals", tags=["fixes"])


@router.post("", response_model=FixEval, status_code=status.HTTP_202_ACCEPTED)
def create_fix_eval(body: FixEvalCreate, db: DbDep) -> FixEval:
    """Queue empirical evaluation of a proposed fix across attacks and benign tasks."""
    target_repo = TargetRepo(db)
    policy_repo = PolicyRepo(db)

    target = target_repo.get(body.target_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target '{body.target_id}' not found.",
        )

    policy = policy_repo.get(body.base_policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Base policy '{body.base_policy_id}' not found.",
        )

    return evaluate_single_fix(body, conn=db)


@router.get("", response_model=Page[FixEval])
def list_fix_evals(
    db: DbDep,
    audit_id: str | None = None,
    target_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[FixEval]:
    """List fix evaluations with two-dimensional price tags and Pareto statuses."""
    repo = FixRepo(db)
    items = repo.list_evals(target_id=target_id, audit_id=audit_id, limit=limit, offset=offset)
    total = repo.count_evals(target_id=target_id, audit_id=audit_id)
    return Page[FixEval](
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{fix_eval_id}", response_model=FixEval)
def get_fix_eval(fix_eval_id: str, db: DbDep) -> FixEval:
    """Retrieve detailed results, blocked cases, and broken tasks for a fix evaluation."""
    repo = FixRepo(db)
    fix_eval = repo.get(fix_eval_id)
    if not fix_eval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fix evaluation '{fix_eval_id}' not found.",
        )
    return fix_eval


@router.post("/{fix_eval_id}/retest", response_model=FixEval, status_code=status.HTTP_202_ACCEPTED)
def retest_fix(fix_eval_id: str, db: DbDep) -> FixEval:
    """Trigger a fresh retest of the evaluated mitigation."""
    repo = FixRepo(db)
    existing = repo.get(fix_eval_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fix evaluation '{fix_eval_id}' not found.",
        )

    create_body = FixEvalCreate(
        target_id=existing.target_id,
        base_policy_id=existing.base_policy_id,
        fix=existing.fix,
        trials=existing.trials,
    )
    return evaluate_single_fix(
        create_body,
        conn=db,
        audit_id=existing.audit_id,
        retest_of=existing.id,
    )


@router.post("/{fix_eval_id}/apply", response_model=Policy)
def apply_fix(fix_eval_id: str, db: DbDep) -> Policy:
    """Generate and activate the child hardened security policy derived from this fix."""
    repo = FixRepo(db)
    policy_repo = PolicyRepo(db)

    existing = repo.get(fix_eval_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fix evaluation '{fix_eval_id}' not found.",
        )

    result = apply_fix_evaluation(fix_eval_id, conn=db)
    activated_policy = policy_repo.get(result["active_policy_id"])
    if not activated_policy:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve applied child policy.",
        )
    return activated_policy
