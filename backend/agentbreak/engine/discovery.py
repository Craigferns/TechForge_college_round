"""Autonomous discovery campaign engine (PLAN.md §13 / M6.1 & M6.2)."""

from __future__ import annotations

import datetime
import hashlib
import random
import sqlite3
import time
import uuid

from agentbreak.attacks.generator import generate_llm_payload, is_attacker_llm_available
from agentbreak.attacks.mutators import MUTATOR_OPERATORS, apply_mutations
from agentbreak.attacks.scenarios import ATTACK_CASES
from agentbreak.attacks.templates import TEMPLATE_FAMILIES, render_payload
from agentbreak.config import get_settings
from agentbreak.db import get_connection
from agentbreak.engine.runner import execute_run
from agentbreak.repo.discovery_repo import DiscoveryRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.sandbox.acme.injection_tasks import INJECTION_TASK_MAP
from agentbreak.schemas.discovery import DiscoveryCampaign, DiscoveryCreate
from agentbreak.schemas.run import Run
from agentbreak.targets.base import BaseTarget


def utc_now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def execute_discovery_campaign(
    campaign_input: DiscoveryCreate | str,
    conn: sqlite3.Connection | None = None,
    target_override: BaseTarget | None = None,
) -> DiscoveryCampaign:
    """Run budgeted autonomous exploration over attack scenarios with seeded determinism."""
    settings = get_settings()
    owns_conn = conn is None
    active_conn = conn if conn is not None else get_connection(settings.db_path)

    discovery_repo = DiscoveryRepo(active_conn)
    run_repo = RunRepo(active_conn)

    # 1. Resolve or create campaign
    campaign_id: str
    target_id: str
    policy_id: str
    scenario_ids: list[str]
    max_attempts: int
    max_seconds: int
    seed: int
    use_attacker_llm: bool

    if isinstance(campaign_input, str):
        campaign_id = campaign_input
        camp = discovery_repo.get_campaign(campaign_id)
        if not camp:
            if owns_conn:
                active_conn.close()
            raise ValueError(f"Discovery campaign '{campaign_id}' not found.")
        target_id = camp.target_id
        policy_id = camp.policy_id
        scenario_ids = list(camp.coverage.keys()) if camp.coverage else []
        max_attempts = 40
        max_seconds = 300
        seed = 42
        use_attacker_llm = False
    else:
        campaign_id = f"dsc_{uuid.uuid4().hex[:12]}"
        target_id = campaign_input.target_id
        policy_id = campaign_input.policy_id
        scenario_ids = campaign_input.scenario_ids or [
            "ipi-exfil",
            "malicious-doc",
            "sleeper-memory",
            "priv-esc",
        ]
        max_attempts = campaign_input.budget.max_attempts
        max_seconds = campaign_input.budget.max_seconds
        seed = campaign_input.seed
        use_attacker_llm = campaign_input.use_attacker_llm

        discovery_repo.create_campaign(
            campaign_id=campaign_id,
            target_id=target_id,
            policy_id=policy_id,
            scenario_ids=scenario_ids,
            budget={"max_attempts": max_attempts, "max_seconds": max_seconds},
            seed=seed,
            use_attacker_llm=use_attacker_llm,
            created_at=utc_now_iso(),
        )

    # Filter applicable attack cases
    candidate_cases = [c for c in ATTACK_CASES if c.scenario_id in scenario_ids]
    if not candidate_cases:
        candidate_cases = ATTACK_CASES

    rng = random.Random(seed)
    template_keys = list(TEMPLATE_FAMILIES.keys())
    operator_keys = list(MUTATOR_OPERATORS.keys())

    coverage: dict[str, dict[str, int]] = {s: {} for s in scenario_ids}
    distinct_fingerprints: set[str] = set()

    start_time = time.time()
    attempts_done = 0
    successes_done = 0

    discovery_repo.update_campaign_status(
        campaign_id=campaign_id,
        status="running",
        attempts=0,
        successes=0,
        coverage=coverage,
    )

    try:
        while attempts_done < max_attempts:
            if time.time() - start_time >= max_seconds:
                break

            # Round-robin selection across candidate cases using deterministic sequence
            case = candidate_cases[attempts_done % len(candidate_cases)]
            case_id = case.id
            inj_task_id = case.injection_task_id or "IT-01"

            inj_cls = INJECTION_TASK_MAP.get(inj_task_id)
            goal_text = inj_cls().GOAL if inj_cls else "Perform unauthorized action"

            # Deterministic variation selection
            template_id = rng.choice(template_keys)
            num_ops = rng.randint(0, 2)
            chosen_ops = rng.sample(operator_keys, k=num_ops) if num_ops > 0 else []

            # Generate payload
            origin = "static"
            rendered_base, _ = render_payload(
                template_id=template_id,
                injection_task_id=inj_task_id,
                goal_text=goal_text,
            )

            if chosen_ops:
                payload = apply_mutations(rendered_base, chosen_ops)
                origin = "mutated"
            else:
                payload = rendered_base

            # Attacker LLM exploration branch if enabled and available
            if use_attacker_llm and is_attacker_llm_available() and rng.random() < 0.3:
                llm_payload = generate_llm_payload(goal_text, inj_task_id)
                if llm_payload:
                    payload = llm_payload
                    origin = "llm"

            fp_raw = f"{case_id}:{payload}"
            fingerprint = f"fp_{hashlib.sha256(fp_raw.encode('utf-8')).hexdigest()[:16]}"

            # Skip duplicate payloads within this campaign
            if fingerprint in distinct_fingerprints:
                attempts_done += 1
                continue
            distinct_fingerprints.add(fingerprint)

            # Create and execute attack run
            attempts_done += 1
            run_id = f"run_{uuid.uuid4().hex[:12]}"
            run = Run(
                id=run_id,
                kind="attack",
                target_id=target_id,
                policy_id=policy_id,
                suite="acme",
                case_id=case_id,
                scenario_id=case.scenario_id,
                user_task_id=case.carrier_task_id,
                injection_task_id=inj_task_id,
                template_id=template_id,
                payload_text=payload,
                payload_hash=f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}",
                origin=origin,  # type: ignore[arg-type]
                status="queued",
                repro={"campaign_id": campaign_id, "attempt": attempts_done, "seed": seed},
                created_at=utc_now_iso(),
            )
            run_repo.create(run)

            completed = execute_run(
                run_id=run_id,
                conn=active_conn,
                target_override=target_override,
            )

            is_success = bool(completed.security)
            if is_success:
                successes_done += 1
                scenario_cov = coverage.setdefault(case.scenario_id, {})
                scenario_cov[case_id] = scenario_cov.get(case_id, 0) + 1

            discovery_repo.add_attempt(
                campaign_id=campaign_id,
                n=attempts_done,
                case_id=case_id,
                fingerprint=fingerprint,
                origin=origin,
                mutation_chain=chosen_ops,
                run_id=run_id,
                success=is_success,
            )

        finished_at = utc_now_iso()
        discovery_repo.update_campaign_status(
            campaign_id=campaign_id,
            status="done",
            attempts=attempts_done,
            successes=successes_done,
            coverage=coverage,
            finished_at=finished_at,
        )

    except Exception:
        import traceback

        traceback.print_exc()
        finished_at = utc_now_iso()
        discovery_repo.update_campaign_status(
            campaign_id=campaign_id,
            status="error",
            attempts=attempts_done,
            successes=successes_done,
            coverage=coverage,
            finished_at=finished_at,
        )
    finally:
        if owns_conn:
            active_conn.close()

    final_camp = discovery_repo.get_campaign(campaign_id)
    if not final_camp:
        raise RuntimeError(f"Campaign '{campaign_id}' disappeared after execution.")
    return final_camp
