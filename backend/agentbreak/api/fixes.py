from fastapi import APIRouter, HTTPException, status

from agentbreak.api.deps import DbDep
from agentbreak.engine.fixes import apply_fix_eval, evaluate_fix
from agentbreak.repo.fix_repo import FixRepo
from agentbreak.schemas import FixEval, FixEvalCreate, Page, Policy

router = APIRouter(prefix="/fix-evals", tags=["fixes"])


@router.post("", response_model=FixEval, status_code=status.HTTP_202_ACCEPTED)
def create_fix_eval(body: FixEvalCreate, db: DbDep) -> FixEval:
    """Queue empirical evaluation of a proposed fix across attacks and benign tasks."""
    return evaluate_fix(body, conn=db)


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
    items, total = repo.list(audit_id=audit_id, target_id=target_id, limit=limit, offset=offset)
    return Page[FixEval](items=items, total=total, limit=limit, offset=offset)


@router.get("/{fix_eval_id}", response_model=FixEval)
def get_fix_eval(fix_eval_id: str, db: DbDep) -> FixEval:
    """Retrieve detailed results, blocked cases, and broken tasks for a fix evaluation."""
    repo = FixRepo(db)
    eval_res = repo.get(fix_eval_id)
    if not eval_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fix evaluation '{fix_eval_id}' not found.",
        )
    return eval_res


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
    create_input = FixEvalCreate(
        target_id=existing.target_id,
        base_policy_id=existing.base_policy_id,
        fix=existing.fix,
        trials=existing.trials,
    )
    return evaluate_fix(create_input, audit_id=existing.audit_id, conn=db, retest_of=existing.id)


@router.post("/{fix_eval_id}/apply", response_model=Policy)
def apply_fix(fix_eval_id: str, db: DbDep) -> Policy:
    """Generate and activate the child hardened security policy derived from this fix."""
    try:
        return apply_fix_eval(fix_eval_id, conn=db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
