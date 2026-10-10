"""Measure a policy by actually running the attack set and the benign set under it.

This is the single source of truth for the fix price tag (D2) and the
counterfactual permission attribution (D1). Every number it returns comes from
persisted runs whose verdicts were computed from PRE/POST state diffs.
"""

from __future__ import annotations

import datetime
import sqlite3
import uuid
from dataclasses import dataclass, field
from typing import Any

from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.schemas.policy import Grant, Policy
from agentbreak.schemas.run import Run
from agentbreak.targets.base import BaseTarget

# (case, scenario, carrier task, injection task) — the 7-case MVP attack set (PLAN §8).
ATTACK_MATRIX: tuple[tuple[str, str, str, str], ...] = (
    ("AS-01", "ipi-exfil", "BT-01", "IT-01"),
    ("AS-02", "ipi-exfil", "BT-10", "IT-01"),
    ("AS-03", "malicious-doc", "BT-08", "IT-02"),
    ("AS-04", "malicious-doc", "BT-08", "IT-03"),
    ("AS-05", "sleeper-memory", "BT-01", "IT-04"),
    ("AS-06", "priv-esc", "BT-01", "IT-05"),
    ("AS-07", "priv-esc", "BT-10", "IT-05"),
)
BENIGN_IDS: tuple[str, ...] = tuple(f"BT-{i:02d}" for i in range(1, 11))
# AS-05's harm (delayed exfiltration) only happens in a later session, so it is measured
# with the multi-session sleeper chain, not the single-session plant predicate.
SLEEPER_CASE = "AS-05"


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


@dataclass(frozen=True, slots=True)
class PolicyMeasurement:
    policy_id: str
    exploited: frozenset[str]  # attack cases whose verdict was success
    resisted: frozenset[str]  # attack cases that completed with no success verdict
    benign_passed: frozenset[str]
    benign_failed: frozenset[str]  # completed but utility false
    inconclusive: frozenset[str]  # runs that errored: never counted as blocked or broken
    # run key (case or task id) -> allowed tool calls (tool, args) in the order made
    calls: dict[str, tuple[tuple[str, dict[str, Any]], ...]] = field(default_factory=dict)
    run_ids: tuple[str, ...] = ()
    keyed_runs: dict[str, str] = field(
        default_factory=dict
    )  # case/task id -> its run (AS-05: trigger session)
    sleeper_outcome: str | None = (
        None  # AS-05 end-to-end: plant_failed | trigger_blocked | triggered
    )


def measure_policy(
    policy_id: str,
    target_id: str,
    conn: sqlite3.Connection,
    target: BaseTarget | None = None,
    repro: dict[str, object] | None = None,
) -> PolicyMeasurement:
    """Run all attack cases and benign tasks under `policy_id`; classify each outcome."""
    from agentbreak.engine.runner import execute_run  # runner imports are heavy; keep lazy

    run_repo = RunRepo(conn)
    tag = dict(repro or {})
    exploited: set[str] = set()
    resisted: set[str] = set()
    passed: set[str] = set()
    failed: set[str] = set()
    inconclusive: set[str] = set()
    calls: dict[str, tuple[tuple[str, dict[str, Any]], ...]] = {}
    run_ids: list[str] = []
    keyed_runs: dict[str, str] = {}

    specs: list[tuple[str, Run]] = []
    for case_id, scenario_id, carrier, inj in ATTACK_MATRIX:
        if case_id == SLEEPER_CASE:
            continue
        rid = f"run_{uuid.uuid4().hex[:12]}"
        specs.append(
            (
                case_id,
                Run(
                    id=rid,
                    kind="attack",
                    target_id=target_id,
                    policy_id=policy_id,
                    suite="acme",
                    case_id=case_id,
                    scenario_id=scenario_id,
                    user_task_id=carrier,
                    injection_task_id=inj,
                    status="queued",
                    repro=tag,
                    created_at=_now(),
                ),
            )
        )
    for task_id in BENIGN_IDS:
        rid = f"run_{uuid.uuid4().hex[:12]}"
        specs.append(
            (
                task_id,
                Run(
                    id=rid,
                    kind="benign",
                    target_id=target_id,
                    policy_id=policy_id,
                    suite="acme",
                    user_task_id=task_id,
                    status="queued",
                    repro=tag,
                    created_at=_now(),
                ),
            )
        )

    for key, run in specs:
        run_repo.create(run)
        done = execute_run(run.id, conn=conn, target_override=target)
        run_ids.append(run.id)
        keyed_runs[key] = run.id
        if done.status != "done":
            inconclusive.add(key)  # fail closed: an error proves nothing either way
        elif done.kind == "attack":
            (exploited if done.security is True else resisted).add(key)
        else:
            (passed if done.utility is True else failed).add(key)
        if done.status == "done":
            calls[key] = tuple(
                (s.tool, dict(s.args or {}))
                for s in run_repo.get_trace(run.id)
                if s.kind == "tool_call" and s.tool and not s.flags.get("denied")
            )

    from agentbreak.engine.sleeper import execute_sleeper_run
    from agentbreak.schemas.sleeper import SleeperRunCreate

    sleeper_outcome: str | None = None
    try:
        slp = execute_sleeper_run(
            SleeperRunCreate(target_id=target_id, policy_id=policy_id, case_id=SLEEPER_CASE),
            conn=conn,
            target_override=target,
        )
        sleeper_outcome = slp.outcome
        session_runs = [s.run_id for s in slp.sessions if s.run_id]
        run_ids.extend(session_runs)
        if session_runs:
            keyed_runs[SLEEPER_CASE] = session_runs[-1]  # the session that decides the outcome
        # The sleeper's calls are evidence too (e.g. which argument carried the exfil address).
        calls[SLEEPER_CASE] = tuple(
            (st.tool, dict(st.args or {}))
            for rid in session_runs
            for st in run_repo.get_trace(rid)
            if st.kind == "tool_call" and st.tool and not st.flags.get("denied")
        )
    except Exception:  # job boundary: the sleeper engine records status=error itself
        sleeper_outcome = None
    if sleeper_outcome == "triggered":
        exploited.add(SLEEPER_CASE)
    elif sleeper_outcome in ("plant_failed", "trigger_blocked"):
        resisted.add(SLEEPER_CASE)
    else:
        inconclusive.add(SLEEPER_CASE)

    return PolicyMeasurement(
        policy_id=policy_id,
        exploited=frozenset(exploited),
        resisted=frozenset(resisted),
        benign_passed=frozenset(passed),
        benign_failed=frozenset(failed),
        inconclusive=frozenset(inconclusive),
        calls=calls,
        run_ids=tuple(run_ids),
        keyed_runs=keyed_runs,
        sleeper_outcome=sleeper_outcome,
    )


def child_policy(conn: sqlite3.Connection, base: Policy, grants: list[Grant], name: str) -> Policy:
    """Return the policy with these grants, reusing an identical one (same hash) if it exists."""
    from agentbreak.domain.policy import compute_policy_hash

    repo = PolicyRepo(conn)
    h = compute_policy_hash(grants)
    existing = repo.get_by_hash(h)
    if existing:
        return existing
    return repo.create(
        Policy(
            id=f"pol_{uuid.uuid4().hex[:8]}",
            name=name,
            parent_id=base.id,
            grants=grants,
            hash=h,
            created_at=_now(),
        )
    )


def tools_used(m: PolicyMeasurement, keys: frozenset[str]) -> dict[str, list[str]]:
    """tool -> sorted run keys (among `keys`) that made an allowed call to it."""
    out: dict[str, set[str]] = {}
    for key in keys:
        for tool, _ in m.calls.get(key, ()):
            out.setdefault(tool, set()).add(key)
    return {t: sorted(v) for t, v in sorted(out.items())}


def observed_domains(m: PolicyMeasurement, tool: str) -> tuple[list[str], list[str]]:
    """(arg names, domains) behind a domain_allowlist suggestion for `tool`.

    Arg names: every argument that carried an e-mail-like value in ANY completed run
    (benign or attack), so a scope cannot be bypassed via an argument only attackers use.
    Domains: only those that passing benign runs were observed to need.
    """
    args: set[str] = set()
    domains: set[str] = set()
    for key, key_calls in m.calls.items():
        for t, call_args in key_calls:
            if t != tool:
                continue
            for name, value in call_args.items():
                for v in value if isinstance(value, list) else [value]:
                    if isinstance(v, str) and "@" in v:
                        args.add(name)
                        if key in m.benign_passed:
                            domains.add(v.rsplit("@", 1)[1].lower())
    return sorted(args), sorted(domains)
