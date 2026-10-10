"""Policy management endpoints."""

from __future__ import annotations

import datetime
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from agentbreak.api.deps import get_db
from agentbreak.db import new_id
from agentbreak.domain.policy import compute_policy_hash
from agentbreak.domain.policy import diff_policies as domain_diff_policies
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.schemas import Policy, PolicyCreate, PolicyDiff

router = APIRouter(prefix="/policies", tags=["policies"])
DbDep = Annotated[sqlite3.Connection, Depends(get_db)]


@router.get("", response_model=list[Policy])
def list_policies(db: DbDep) -> list[Policy]:
    """List all immutable permission policies and their grant specifications."""
    repo = PolicyRepo(db)
    return repo.list()


@router.post("", response_model=Policy, status_code=status.HTTP_201_CREATED)
def create_policy(body: PolicyCreate, db: DbDep) -> Policy:
    """Register a new immutable permission policy with SHA-256 canonical hash."""
    repo = PolicyRepo(db)
    now = datetime.datetime.now(datetime.UTC).isoformat()
    policy_hash = compute_policy_hash(body.grants)

    new_policy = Policy(
        id=new_id("pol"),
        name=body.name,
        parent_id=body.parent_id,
        grants=body.grants,
        hash=policy_hash,
        created_at=now,
    )
    return repo.create(new_policy)


@router.get("/{policy_id}", response_model=Policy)
def get_policy(policy_id: str, db: DbDep) -> Policy:
    """Retrieve full grant specification and lineage for a security policy."""
    repo = PolicyRepo(db)
    policy = repo.get(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found.",
        )
    return policy


@router.get("/{policy_a}/diff/{policy_b}", response_model=PolicyDiff)
def diff_policies(policy_a: str, policy_b: str, db: DbDep) -> PolicyDiff:
    """Compute structural grant delta between two security policies."""
    repo = PolicyRepo(db)
    pol_a = repo.get(policy_a)
    if not pol_a:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_a}' not found.",
        )
    pol_b = repo.get(policy_b)
    if not pol_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_b}' not found.",
        )

    return domain_diff_policies(pol_a, pol_b)
