"""Attack and benign run execution, listing, trace inspection, and replay endpoints."""

from __future__ import annotations

import sqlite3
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from agentbreak.api.deps import get_db
from agentbreak.attacks.scenarios import get_attack_case
from agentbreak.attacks.templates import DEFAULT_TEMPLATE_ID, render_payload
from agentbreak.engine.jobs import get_job_pool
from agentbreak.engine.runner import utc_now_iso
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.sandbox.acme.injection_tasks import INJECTION_TASK_MAP
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
DbDep = Annotated[sqlite3.Connection, Depends(get_db)]


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_runs(body: RunCreate, db: DbDep) -> dict[str, list[str]]:
    """Queue execution of single or batched attack and utility runs."""
    target_repo = TargetRepo(db)
    policy_repo = PolicyRepo(db)
    run_repo = RunRepo(db)

    # 1. Validate target and policy presence
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

    created_runs: list[Run] = []
    job_pool = get_job_pool()

    # 2. Enumerate trials
    for trial_idx in range(body.trials):
        seed_val = (body.seed + trial_idx) if body.seed is not None else None

        # A. Attack cases
        for case_id in body.attack_case_ids:
            try:
                case = get_attack_case(case_id)
            except KeyError as err:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown attack case ID: '{case_id}'.",
                ) from err

            inj_cls = INJECTION_TASK_MAP.get(case.injection_task_id)
            goal_text = inj_cls().GOAL if inj_cls else ""
            payload_text, payload_hash = render_payload(
                template_id=DEFAULT_TEMPLATE_ID,
                injection_task_id=case.injection_task_id,
                goal_text=goal_text,
            )

            run_id = f"run_{uuid.uuid4().hex[:12]}"
            attack_run = Run(
                id=run_id,
                kind="attack",
                target_id=body.target_id,
                policy_id=body.policy_id,
                suite="acme",
                case_id=case.id,
                scenario_id=case.scenario_id,
                user_task_id=case.carrier_task_id,
                injection_task_id=case.injection_task_id,
                template_id=DEFAULT_TEMPLATE_ID,
                payload_text=payload_text,
                payload_hash=payload_hash,
                origin="static",
                status="queued",
                repro={
                    "suite_hash": "sha256:acme",
                    "target_id": body.target_id,
                    "policy_id": body.policy_id,
                    "case_id": case.id,
                    "seed": seed_val,
                    "trial": trial_idx,
                },
                created_at=utc_now_iso(),
            )
            run_repo.create(attack_run)
            created_runs.append(attack_run)

            # Optional unpoisoned control run
            if body.include_controls:
                control_id = f"run_{uuid.uuid4().hex[:12]}"
                control_run = Run(
                    id=control_id,
                    kind="control",
                    target_id=body.target_id,
                    policy_id=body.policy_id,
                    suite="acme",
                    case_id=case.id,
                    scenario_id=case.scenario_id,
                    user_task_id=case.carrier_task_id,
                    injection_task_id=None,
                    template_id=None,
                    payload_text=None,
                    payload_hash=None,
                    origin="static",
                    status="queued",
                    repro={
                        "suite_hash": "sha256:acme",
                        "target_id": body.target_id,
                        "policy_id": body.policy_id,
                        "case_id": case.id,
                        "is_control": True,
                        "trial": trial_idx,
                    },
                    created_at=utc_now_iso(),
                )
                run_repo.create(control_run)
                created_runs.append(control_run)

        # B. Benign tasks
        for benign_id in body.benign_task_ids:
            benign_run_id = f"run_{uuid.uuid4().hex[:12]}"
            benign_run = Run(
                id=benign_run_id,
                kind="benign",
                target_id=body.target_id,
                policy_id=body.policy_id,
                suite="acme",
                user_task_id=benign_id,
                status="queued",
                repro={
                    "suite_hash": "sha256:acme",
                    "target_id": body.target_id,
                    "policy_id": body.policy_id,
                    "benign_id": benign_id,
                    "trial": trial_idx,
                },
                created_at=utc_now_iso(),
            )
            run_repo.create(benign_run)
            created_runs.append(benign_run)

    # 3. Submit all queued runs to background job pool
    for r in created_runs:
        job_pool.submit_run(r.id)

    return {"run_ids": [r.id for r in created_runs]}


@router.get("", response_model=Page[RunSummary])
def list_runs(
    db: DbDep,
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
    repo = RunRepo(db)
    id_list = [i.strip() for i in ids.split(",") if i.strip()] if ids else None

    items = repo.list_runs(
        target_id=target_id,
        policy_id=policy_id,
        kind=kind,
        status=status_filter,
        scenario_id=scenario_id,
        ids=id_list,
        limit=limit,
        offset=offset,
    )
    total = repo.count_runs(
        target_id=target_id,
        policy_id=policy_id,
        kind=kind,
        status=status_filter,
        scenario_id=scenario_id,
        ids=id_list,
    )

    return Page[RunSummary](
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}", response_model=Run)
def get_run(run_id: str, db: DbDep) -> Run:
    """Retrieve top-level run execution summary, verdict, and metadata."""
    repo = RunRepo(db)
    run = repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )
    return run


@router.get("/{run_id}/trace", response_model=list[TraceStep])
def get_run_trace(run_id: str, db: DbDep) -> list[TraceStep]:
    """Retrieve full step-by-step tool invocation trace with highlighted vectors."""
    repo = RunRepo(db)
    run = repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )
    return repo.get_trace(run_id)


@router.get("/{run_id}/snapshots", response_model=SnapshotPair)
def get_run_snapshots(run_id: str, db: DbDep) -> SnapshotPair:
    """Retrieve PRE and POST environment snapshots for state diff verification."""
    repo = RunRepo(db)
    run = repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )
    snapshots = repo.get_snapshots(run_id)
    if not snapshots:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshots for run '{run_id}' not found.",
        )
    return snapshots


@router.get("/{run_id}/graph", response_model=AttackGraph)
def get_run_graph(run_id: str, db: DbDep) -> AttackGraph:
    """Retrieve causal attack graph connecting attack vector to exploit effect."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.post("/{run_id}/verify", response_model=Verdict)
def verify_run(run_id: str, db: DbDep) -> Verdict:
    """Deterministically re-verify environment state diff predicates and canary tokens."""
    repo = RunRepo(db)
    run = repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )
    verdict = repo.get_verdict(run_id)
    if not verdict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verdict for run '{run_id}' not found.",
        )
    return verdict


@router.post("/{run_id}/cancel", response_model=Run)
def cancel_run(run_id: str, db: DbDep) -> Run:
    """Cancel an active or queued run."""
    repo = RunRepo(db)
    run = repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )

    job_pool = get_job_pool()
    job_pool.cancel_run(run_id, conn=db)

    updated = repo.get(run_id)
    return updated or run


@router.post("/{run_id}/replay", status_code=status.HTTP_202_ACCEPTED)
def replay_run(run_id: str, db: DbDep) -> dict[str, list[str]]:
    """Queue a deterministic replay of a previous run under identical initial conditions."""
    repo = RunRepo(db)
    source_run = repo.get(run_id)
    if not source_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source run '{run_id}' not found for replay.",
        )

    new_run_id = f"run_{uuid.uuid4().hex[:12]}"
    replay_run = Run(
        id=new_run_id,
        kind=source_run.kind,
        target_id=source_run.target_id,
        policy_id=source_run.policy_id,
        suite=source_run.suite,
        case_id=source_run.case_id,
        scenario_id=source_run.scenario_id,
        user_task_id=source_run.user_task_id,
        injection_task_id=source_run.injection_task_id,
        template_id=source_run.template_id,
        payload_text=source_run.payload_text,
        payload_hash=source_run.payload_hash,
        origin=source_run.origin,
        status="queued",
        repro=dict(source_run.repro),
        created_at=utc_now_iso(),
    )
    repo.create(replay_run)

    job_pool = get_job_pool()
    job_pool.submit_run(new_run_id)

    return {"run_ids": [new_run_id]}
