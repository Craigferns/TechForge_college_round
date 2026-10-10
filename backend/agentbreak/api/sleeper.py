"""Sleeper mode multi-session endpoints for cross-session attack evaluations."""

from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from agentbreak.api.deps import get_db
from agentbreak.engine.sleeper import execute_sleeper_run
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.sleeper_repo import SleeperRepo
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.schemas import Page, SleeperRun, SleeperRunCreate

router = APIRouter(prefix="/sleeper-runs", tags=["sleeper"])
DbDep = Annotated[sqlite3.Connection, Depends(get_db)]


@router.post("", response_model=SleeperRun, status_code=status.HTTP_202_ACCEPTED)
def create_sleeper_run(body: SleeperRunCreate, db: DbDep) -> SleeperRun:
    """Launch a multi-session sleeper evaluation (Plant -> Gap -> Trigger)."""
    target_repo = TargetRepo(db)
    policy_repo = PolicyRepo(db)

    target = target_repo.get(body.target_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target '{body.target_id}' not found.",
        )

    policy = policy_repo.get(body.policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{body.policy_id}' not found.",
        )

    return execute_sleeper_run(body, conn=db)


@router.get("", response_model=Page[SleeperRun])
def list_sleeper_runs(
    db: DbDep,
    target_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[SleeperRun]:
    """List cross-session sleeper test runs and their outcomes."""
    repo = SleeperRepo(db)
    items = repo.list_runs(target_id=target_id, limit=limit, offset=offset)
    total = repo.count_runs(target_id=target_id)

    return Page[SleeperRun](
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{sleeper_id}", response_model=SleeperRun)
def get_sleeper_run(sleeper_id: str, db: DbDep) -> SleeperRun:
    """Retrieve multi-session lifecycle data and persistent memory diffs."""
    repo = SleeperRepo(db)
    run = repo.get(sleeper_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sleeper run '{sleeper_id}' not found.",
        )
    return run
