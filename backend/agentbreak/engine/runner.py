"""Run execution runner orchestrating sandbox isolation, tracing, and persistence."""

from __future__ import annotations

import datetime
import hashlib
import sqlite3
from typing import Any

from agentbreak.attacks.scenarios import CASE_VECTOR_MAP, get_attack_case, get_scenario
from agentbreak.attacks.templates import DEFAULT_TEMPLATE_ID, render_payload
from agentbreak.config import get_settings
from agentbreak.db import get_connection
from agentbreak.engine.loop import run_once
from agentbreak.engine.tracing import messages_to_trace_steps
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.sandbox.acme.injection_tasks import INJECTION_TASK_MAP
from agentbreak.sandbox.acme.user_tasks import (
    BT01_SummarizeNewestEmail,
    BT02_ReplyToSam,
    BT03_FindBudgetTotal,
    BT04_EmailBudgetToManager,
    BT05_SendProjectUpdateToPartner,
    BT06_RememberManagerPreference,
    BT07_RecallMeetingPreference,
    BT08_ReadVendorOnboardingSteps,
    BT09_ShareRoadmapWithKim,
    BT10_EmailSummaryToSam,
)
from agentbreak.schemas.run import Run, Verdict
from agentbreak.targets.base import BaseTarget
from agentbreak.targets.factory import create_target

BENIGN_TASK_CLS_MAP: dict[str, Any] = {
    "BT-01": BT01_SummarizeNewestEmail,
    "BT-02": BT02_ReplyToSam,
    "BT-03": BT03_FindBudgetTotal,
    "BT-04": BT04_EmailBudgetToManager,
    "BT-05": BT05_SendProjectUpdateToPartner,
    "BT-06": BT06_RememberManagerPreference,
    "BT-07": BT07_RecallMeetingPreference,
    "BT-08": BT08_ReadVendorOnboardingSteps,
    "BT-09": BT09_ShareRoadmapWithKim,
    "BT-10": BT10_EmailSummaryToSam,
}


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.datetime.now(datetime.UTC).isoformat()


def execute_run(
    run_id: str,
    conn: sqlite3.Connection | None = None,
    target_override: BaseTarget | None = None,
    memory_in: dict[str, str] | None = None,
) -> Run:
    """Execute a single evaluation run with deterministic tracing and persistence.

    Guarantees:
    - Never raises unexpected exceptions: catches any failure and records status='error'
    - Fully records trace steps, PRE/POST snapshots, and deterministic verdict
    """
    settings = get_settings()
    owns_conn = conn is None
    active_conn = conn if conn is not None else get_connection(settings.db_path)

    run_repo = RunRepo(active_conn)
    target_repo = TargetRepo(active_conn)
    policy_repo = PolicyRepo(active_conn)

    run = run_repo.get(run_id)
    if run is None:
        if owns_conn:
            active_conn.close()
        raise ValueError(f"Run record '{run_id}' not found in database.")

    if run.status == "cancelled":
        if owns_conn:
            active_conn.close()
        return run

    started_at = utc_now_iso()
    run_repo.update_status(run_id=run.id, status="running", started_at=started_at)

    try:
        # 1. Resolve Target
        target: BaseTarget
        if target_override is not None:
            target = target_override
        else:
            target_model = target_repo.get(run.target_id)
            if target_model is None:
                # Fallback: check matching by name or id prefix
                for t in target_repo.list():
                    if t.id == run.target_id or t.name == run.target_id or run.target_id in t.id:
                        target_model = t
                        break
            if target_model is None:
                raise ValueError(f"Target '{run.target_id}' could not be resolved.")
            target = create_target(target_model)

        # 2. Resolve Policy
        policy = policy_repo.get(run.policy_id)
        if policy is None:
            raise ValueError(f"Policy '{run.policy_id}' could not be resolved.")

        # 3. Resolve User / Carrier Task
        if run.user_task_id not in BENIGN_TASK_CLS_MAP:
            raise ValueError(f"Unsupported user/carrier task ID: '{run.user_task_id}'.")
        user_task = BENIGN_TASK_CLS_MAP[run.user_task_id]()

        # 4. Resolve Injections and Injection Task
        inj_task = None
        injections: dict[str, str] = {}
        payload_text = run.payload_text
        payload_hash = run.payload_hash

        if run.kind == "attack":
            if run.injection_task_id:
                inj_cls = INJECTION_TASK_MAP.get(run.injection_task_id)
                if inj_cls:
                    inj_task = inj_cls()

            vector = "inj_email_body"
            if run.case_id:
                try:
                    case = get_attack_case(run.case_id)
                    vector = CASE_VECTOR_MAP.get(case.id, vector)
                except KeyError:
                    pass

            if payload_text is None and inj_task is not None:
                rendered, r_hash = render_payload(
                    template_id=run.template_id or DEFAULT_TEMPLATE_ID,
                    injection_task_id=run.injection_task_id or "IT-01",
                    goal_text=inj_task.GOAL,
                )
                payload_text = rendered
                payload_hash = r_hash

            if payload_text:
                injections[vector] = payload_text

        # Memory input for sleeper sessions if provided in repro or call arg
        eff_memory_in = memory_in
        if eff_memory_in is None and run.repro and "memory_in" in run.repro:
            eff_memory_in = run.repro["memory_in"]

        # 5. Execute sandbox loop
        outcome = run_once(
            target=target,
            policy=policy,
            user_task=user_task,
            injection_task=inj_task,
            injections=injections,
            memory_in=eff_memory_in,
        )

        # 6. Convert messages to trace steps with taint heuristics
        trace_steps = messages_to_trace_steps(
            messages=outcome.messages,
            payload_text=payload_text,
            payload_hash=payload_hash,
            injection_task_id=run.injection_task_id,
        )

        for step in trace_steps:
            run_repo.add_trace_step(run.id, step)

        # 7. Persist PRE and POST snapshots
        run_repo.save_snapshot(run.id, "pre", outcome.pre.model_dump())
        run_repo.save_snapshot(run.id, "post", outcome.post.model_dump())

        # 8. Compute and persist verdict
        finished_at = utc_now_iso()
        scenario = None
        if run.scenario_id:
            try:
                scenario = get_scenario(run.scenario_id)
            except KeyError:
                pass

        verdict_hash_raw = f"{outcome.security}:{run.id}:{finished_at}"
        verdict_hash = f"sha256:{hashlib.sha256(verdict_hash_raw.encode()).hexdigest()}"

        verdict = Verdict(
            success=bool(outcome.security) if outcome.security is not None else False,
            classification="exploited" if outcome.security else "blocked",
            impact_class=scenario.impact_class if scenario else None,
            severity=scenario.severity if scenario else None,
            evidence=[],
            verifier_version="agentbreak-v0.1.0",
            verdict_hash=verdict_hash,
            created_at=finished_at,
        )
        run_repo.save_verdict(run.id, verdict)

        # 9. Update final run status
        run_repo.update_status(
            run_id=run.id,
            status="done",
            utility=outcome.utility,
            security=outcome.security,
            model_output=outcome.model_output,
            finished_at=finished_at,
        )

    except Exception as exc:
        finished_at = utc_now_iso()
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        run_repo.update_status(
            run_id=run.id,
            status="error",
            error=error_msg[:1000],
            finished_at=finished_at,
        )

    finally:
        if owns_conn:
            active_conn.close()

    updated = run_repo.get(run.id)
    return updated or run
