"""Target agent endpoints."""

from __future__ import annotations

import datetime
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from agentbreak.api.deps import get_db
from agentbreak.db import new_id
from agentbreak.llm.provider import probe_target
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.schemas.target import Target, TargetCreate, TargetTestResult
from agentbreak.targets.openai_compat import OpenAICompatTarget

router = APIRouter(prefix="/targets", tags=["targets"])
DbDep = Annotated[sqlite3.Connection, Depends(get_db)]


@router.get("", response_model=list[Target])
def list_targets(db: DbDep) -> list[Target]:
    """List all registered agent targets (scripted and OpenAI-compatible)."""
    repo = TargetRepo(db)
    return repo.list()


@router.post("", response_model=Target, status_code=status.HTTP_201_CREATED)
def create_target(body: TargetCreate, db: DbDep) -> Target:
    """Register a new agent target with endpoint configuration."""
    repo = TargetRepo(db)
    now = datetime.datetime.now(datetime.UTC).isoformat()
    new_target = Target(
        id=new_id("tgt"),
        name=body.name,
        kind=body.kind,
        config=body.config,
        active_policy_id=None,
        created_at=now,
    )
    return repo.create(new_target)


@router.get("/{target_id}", response_model=Target)
def get_target(target_id: str, db: DbDep) -> Target:
    """Retrieve details and metadata for a specific agent target."""
    repo = TargetRepo(db)
    target = repo.get(target_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target '{target_id}' not found.",
        )
    return target


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_target(target_id: str, db: DbDep) -> None:
    """Delete a target configuration."""
    repo = TargetRepo(db)
    target = repo.get(target_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target '{target_id}' not found.",
        )

    # Check if any runs reference this target
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM run WHERE target_id = ?;", (target_id,))
    row = cursor.fetchone()
    if row and row["cnt"] > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete target '{target_id}' because {row['cnt']} run(s) reference it.",
        )

    repo.delete(target_id)


@router.post("/{target_id}/test", response_model=TargetTestResult)
def test_target(target_id: str, db: DbDep) -> TargetTestResult:
    """Test connectivity and tool-calling responsiveness for a target agent."""
    repo = TargetRepo(db)
    target = repo.get(target_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target '{target_id}' not found.",
        )

    if target.kind == "scripted":
        return TargetTestResult(
            reachable=True,
            tool_calling=True,
            latency_ms=1,
            notes="Simulated scripted target is operational and deterministically verified.",
        )
    elif target.kind == "openai_compat":
        adapter = OpenAICompatTarget(
            id=target.id,
            name=target.name,
            config=target.config,
        )
        base_url = target.config.get("base_url", "http://localhost:11434/v1")
        model = target.config.get("model", "llama3.1")
        api_key = adapter.resolve_api_key()
        return probe_target(
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout_s=5.0,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported target kind: {target.kind}",
        )
