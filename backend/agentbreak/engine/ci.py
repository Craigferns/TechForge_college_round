"""CI security gate: measure one policy, write a JSON report, return a process exit code.

Exit codes: 0 gate passed · 1 security/benign gate failed · 2 infrastructure error
(any inconclusive run, or the target/policy could not be resolved). Errors never pass.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from pydantic import TypeAdapter

from agentbreak.db import get_connection
from agentbreak.engine.measure import ATTACK_MATRIX, BENIGN_IDS, child_policy, measure_policy
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.schemas.policy import Grant
from agentbreak.seed import seed_database

SCHEMA_VERSION = 1


def run_ci_gate(
    target_id: str,
    policy_id: str | None,
    max_exploited: int,
    min_benign_pass: float,
    out: Path,
    policy_file: Path | None = None,
) -> int:
    conn = get_connection()
    try:
        seed_database(conn)  # idempotent; makes the simulated demo target available in CI
        target = TargetRepo(conn).get(target_id)
        pid = policy_id or (target.active_policy_id if target else None)
        policy = PolicyRepo(conn).get(pid) if pid else None
        if policy_file is not None:
            # Policy-as-code: the grants under test come from the repository, not the DB.
            root = PolicyRepo(conn).get("pol_full")
            grants = TypeAdapter(list[Grant]).validate_json(policy_file.read_text(encoding="utf-8"))
            policy = (
                child_policy(conn, root, grants, f"policy file {policy_file.name}")
                if root
                else None
            )
            pid = policy.id if policy else str(policy_file)
        if target is None or policy is None:
            _write(out, {"error": f"target '{target_id}' or policy '{pid}' not found"})
            return 2
        m = measure_policy(policy.id, target.id, conn, repro={"ci": True})
    finally:
        conn.close()

    def outcome(key: str) -> str:
        if key in m.inconclusive:
            return "inconclusive"
        if key in m.exploited:
            return "exploited"
        if key in m.benign_passed:
            return "passed"
        if key in m.benign_failed:
            return "failed"
        return "resisted"

    benign_rate = len(m.benign_passed) / len(BENIGN_IDS)
    reasons: list[str] = []
    if m.inconclusive:
        reasons.append(f"inconclusive (infrastructure errors): {sorted(m.inconclusive)}")
    if len(m.exploited) > max_exploited:
        reasons.append(
            f"{len(m.exploited)} attacks exploited > allowed {max_exploited}: {sorted(m.exploited)}"
        )
    if benign_rate < min_benign_pass:
        reasons.append(
            f"benign pass rate {benign_rate:.2f} < required {min_benign_pass:.2f}: failed {sorted(m.benign_failed)}"
        )
    code = 2 if m.inconclusive else (1 if reasons else 0)

    _write(
        out,
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "target": {
                "id": target.id,
                "kind": target.kind,
                "simulated": target.kind == "scripted",
            },
            "policy": {
                "id": policy.id,
                "hash": policy.hash,
                "grants": [g.tool for g in policy.grants],
            },
            "suite": "acme",
            "attacks": {c: outcome(c) for c, *_ in ATTACK_MATRIX},
            "benign": {t: outcome(t) for t in BENIGN_IDS},
            "sleeper_outcome": m.sleeper_outcome,
            "summary": {
                "exploited": len(m.exploited),
                "attacks_total": len(ATTACK_MATRIX),
                "benign_passed": len(m.benign_passed),
                "benign_total": len(BENIGN_IDS),
                "inconclusive": len(m.inconclusive),
            },
            "gate": {
                "max_exploited": max_exploited,
                "min_benign_pass": min_benign_pass,
                "passed": code == 0,
                "exit_code": code,
                "reasons": reasons,
            },
            "run_ids": list(m.run_ids),
        },
    )
    print(
        f"agentbreak ci: exit {code} - "
        + ("; ".join(reasons) or "gate passed")
        + f" (report: {out})"
    )
    return code


def _write(out: Path, data: dict[str, object]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
