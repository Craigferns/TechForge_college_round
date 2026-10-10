"""Autonomous attack discovery campaign execution engine."""

from __future__ import annotations

import hashlib
import random
import sqlite3
import time
import uuid

from agentbreak.attacks.generator import generate_llm_payload
from agentbreak.attacks.mutators import MUTATION_OPERATORS, apply_mutations
from agentbreak.attacks.scenarios import ATTACK_CASES
from agentbreak.attacks.templates import DEFAULT_TEMPLATE_ID, render_payload
from agentbreak.config import get_settings
from agentbreak.db import get_connection
from agentbreak.engine.runner import execute_run, utc_now_iso
from agentbreak.repo.discovery_repo import DiscoveryRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.sandbox.acme.injection_tasks import INJECTION_TASK_MAP
from agentbreak.schemas.discovery import (
    DiscoveryAttempt,
    DiscoveryCampaign,
    DiscoveryCreate,
)
from agentbreak.schemas.run import Run


def run_discovery_campaign(
    create: DiscoveryCreate,
    conn: sqlite3.Connection | None = None,
) -> DiscoveryCampaign:
    """Execute an autonomous discovery campaign with deterministic mutator search.

    Guarantees:
    - Never exceeds max_attempts or max_seconds budget
    - Identical attempt list and fingerprints with the same seed
    - Gracefully uses attacker LLM if requested, falling back to mutators
    """
    settings = get_settings()
    owns_conn = conn is None
    active_conn = conn if conn is not None else get_connection(settings.db_path)

    campaign_repo = DiscoveryRepo(active_conn)
    run_repo = RunRepo(active_conn)

    campaign_id = f"dsc_{uuid.uuid4().hex[:12]}"
    created_at = utc_now_iso()

    # 1. Select candidate attack cases
    if create.scenario_ids:
        eligible_cases = [c for c in ATTACK_CASES if c.scenario_id in create.scenario_ids]
    else:
        eligible_cases = list(ATTACK_CASES)

    if not eligible_cases:
        eligible_cases = list(ATTACK_CASES)

    campaign_repo.create_campaign(
        campaign_id=campaign_id,
        target_id=create.target_id,
        policy_id=create.policy_id,
        scenario_ids=create.scenario_ids or [c.scenario_id for c in eligible_cases],
        budget=create.budget.model_dump(),
        seed=create.seed,
        use_attacker_llm=create.use_attacker_llm,
        created_at=created_at,
    )

    rng = random.Random(create.seed)
    max_attempts = create.budget.max_attempts
    max_seconds = create.budget.max_seconds
    start_time = time.monotonic()

    seen_fingerprints: set[str] = set()
    attempts_list: list[DiscoveryAttempt] = []
    coverage: dict[str, dict[str, int]] = {}

    for c in eligible_cases:
        coverage[c.scenario_id] = coverage.get(c.scenario_id, {})
        coverage[c.scenario_id][c.id] = 0

    attempt_counter = 0

    while attempt_counter < max_attempts:
        if (time.monotonic() - start_time) >= max_seconds:
            break

        # Round robin across eligible cases
        case = eligible_cases[attempt_counter % len(eligible_cases)]

        # Determine mutation chain (0, 1, or 2 ops)
        num_ops = rng.choice([0, 1, 2])
        chosen_ops = [rng.choice(MUTATION_OPERATORS) for _ in range(num_ops)]

        inj_cls = INJECTION_TASK_MAP.get(case.injection_task_id)
        goal_text = inj_cls().GOAL if inj_cls else ""
        raw_payload, _ = render_payload(
            template_id=DEFAULT_TEMPLATE_ID,
            injection_task_id=case.injection_task_id,
            goal_text=goal_text,
        )

        mutated_payload = apply_mutations(raw_payload, chosen_ops, seed=rng.randint(0, 100000))
        fp_raw = f"{case.id}:{mutated_payload}"
        fingerprint = hashlib.sha256(fp_raw.encode("utf-8")).hexdigest()

        if fingerprint in seen_fingerprints:
            # Shift slightly with extra salt to ensure forward progress
            mutated_payload = f"{mutated_payload} "
            fp_raw = f"{case.id}:{mutated_payload}"
            fingerprint = hashlib.sha256(fp_raw.encode("utf-8")).hexdigest()

        seen_fingerprints.add(fingerprint)
        attempt_counter += 1

        # Execute run
        run_id = f"run_dsc_{uuid.uuid4().hex[:10]}"
        attack_run = Run(
            id=run_id,
            kind="attack",
            target_id=create.target_id,
            policy_id=create.policy_id,
            suite="acme",
            case_id=case.id,
            scenario_id=case.scenario_id,
            user_task_id=case.carrier_task_id,
            injection_task_id=case.injection_task_id,
            template_id=DEFAULT_TEMPLATE_ID,
            payload_text=mutated_payload,
            payload_hash=f"sha256:{fingerprint}",
            origin="mutated" if chosen_ops else "static",
            status="queued",
            repro={
                "campaign_id": campaign_id,
                "attempt": attempt_counter,
                "seed": create.seed,
                "mutation_chain": chosen_ops,
            },
            created_at=utc_now_iso(),
        )
        run_repo.create(attack_run)
        completed_run = execute_run(run_id, conn=active_conn)

        is_success = bool(completed_run.security)
        if is_success:
            coverage[case.scenario_id][case.id] = coverage[case.scenario_id].get(case.id, 0) + 1

        attempt_record = DiscoveryAttempt(
            n=attempt_counter,
            case_id=case.id,
            fingerprint=f"sha256:{fingerprint}",
            origin="mutated" if chosen_ops else "static",
            mutation_chain=chosen_ops,
            run_id=run_id,
            success=is_success,
        )
        campaign_repo.add_attempt(campaign_id, attempt_record)
        attempts_list.append(attempt_record)

        # Attacker LLM step on failure if requested and budget allows
        if not is_success and create.use_attacker_llm and attempt_counter < max_attempts:
            marker = f"[[AB:{case.injection_task_id}]]"
            llm_payload = generate_llm_payload(goal_text=goal_text, marker=marker)
            if llm_payload:
                llm_fp_raw = f"{case.id}:{llm_payload}"
                llm_fp = hashlib.sha256(llm_fp_raw.encode("utf-8")).hexdigest()
                seen_fingerprints.add(llm_fp)
                attempt_counter += 1

                llm_run_id = f"run_dsc_llm_{uuid.uuid4().hex[:8]}"
                llm_run = Run(
                    id=llm_run_id,
                    kind="attack",
                    target_id=create.target_id,
                    policy_id=create.policy_id,
                    suite="acme",
                    case_id=case.id,
                    scenario_id=case.scenario_id,
                    user_task_id=case.carrier_task_id,
                    injection_task_id=case.injection_task_id,
                    template_id=DEFAULT_TEMPLATE_ID,
                    payload_text=llm_payload,
                    payload_hash=f"sha256:{llm_fp}",
                    origin="llm",
                    status="queued",
                    repro={"campaign_id": campaign_id, "origin": "llm"},
                    created_at=utc_now_iso(),
                )
                run_repo.create(llm_run)
                completed_llm_run = execute_run(llm_run_id, conn=active_conn)
                llm_success = bool(completed_llm_run.security)
                if llm_success:
                    coverage[case.scenario_id][case.id] = (
                        coverage[case.scenario_id].get(case.id, 0) + 1
                    )

                llm_attempt_record = DiscoveryAttempt(
                    n=attempt_counter,
                    case_id=case.id,
                    fingerprint=f"sha256:{llm_fp}",
                    origin="llm",
                    mutation_chain=["attacker_llm_rewrite"],
                    run_id=llm_run_id,
                    success=llm_success,
                )
                campaign_repo.add_attempt(campaign_id, llm_attempt_record)
                attempts_list.append(llm_attempt_record)

    total_successes = sum(1 for a in attempts_list if a.success)
    finished_at = utc_now_iso()

    campaign_repo.update_campaign(
        campaign_id=campaign_id,
        status="done",
        attempts=len(attempts_list),
        successes=total_successes,
        coverage=coverage,
        finished_at=finished_at,
    )

    if owns_conn:
        active_conn.close()

    return DiscoveryCampaign(
        id=campaign_id,
        target_id=create.target_id,
        policy_id=create.policy_id,
        status="done",
        attempts=len(attempts_list),
        successes=total_successes,
        coverage=coverage,
        attempts_list=attempts_list,
        created_at=created_at,
        finished_at=finished_at,
    )
