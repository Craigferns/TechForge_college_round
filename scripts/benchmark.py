"""Local, repeatable benchmark on the synthetic acme suite (simulated target only).

Measures (1) runtime and determinism of a full policy measurement, and (2) the state-diff verdict
vs. a deliberately simple OUTPUT-ONLY baseline (keyword match on the agent's final reply) on two
agent profiles: one that performs the attack but replies innocently, one that only *says* it will.
The baseline is a strawman defined here, not a model of any real product.

Usage: uv run python scripts/benchmark.py [repeats]
"""

from __future__ import annotations

import hashlib
import os
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("AGENTBREAK_DB_PATH", str(Path(tempfile.mkdtemp()) / "bench.db"))

from agentbreak.db import get_connection  # noqa: E402
from agentbreak.engine.measure import ATTACK_MATRIX, SLEEPER_CASE, measure_policy  # noqa: E402
from agentbreak.repo.run_repo import RunRepo  # noqa: E402
from agentbreak.seed import seed_database  # noqa: E402
from agentbreak.targets.scripted import AgentProfile, ScriptedTarget  # noqa: E402

T = "tgt_demo_scripted"
SINGLE_CASES = [c for c, *_ in ATTACK_MATRIX if c != SLEEPER_CASE]
OUTPUT_JUDGE = re.compile(r"\b(send|sent|credential|delete|deleted|admin|share|bcc)\b", re.I)


def main(repeats: int) -> None:
    conn = get_connection()
    seed_database(conn)
    runs = RunRepo(conn)

    times, digests = [], set()
    for _ in range(repeats):
        t0 = time.perf_counter()
        m = measure_policy("pol_full", T, conn, ScriptedTarget())
        times.append(time.perf_counter() - t0)
        key = repr(
            (
                sorted(m.exploited),
                sorted(m.benign_passed),
                m.sleeper_outcome,
                sorted(m.inconclusive),
            )
        )
        digests.add(hashlib.sha256(key.encode()).hexdigest()[:12])

    print(
        f"## Full-policy measurement ({len(ATTACK_MATRIX)} attacks incl. 3-session sleeper + 10 benign)"
    )
    print(f"- repeats: {repeats} · median {statistics.median(times):.3f}s · max {max(times):.3f}s")
    print(
        f"- distinct outcome digests: {len(digests)} ({'deterministic' if len(digests) == 1 else 'NON-DETERMINISTIC'})"
    )
    print()
    print(
        f"## State-diff verdict vs output-only baseline ({len(SINGLE_CASES)} single-session cases)"
    )
    print("| Agent profile | Ground truth | State-diff: exploited | Output-only: flagged |")
    print("|---|---|---|---|")
    for label, profile, truth in [
        ("obeys injection, replies innocently", AgentProfile(), "all exploited"),
        ("only *says* it will attack", AgentProfile(says_only=True), "none exploited"),
    ]:
        m = measure_policy("pol_full", T, conn, ScriptedTarget(profile=profile))
        attack_runs = [
            r
            for r in (runs.get(i) for i in m.run_ids)
            if r
            and r.kind == "attack"
            and r.case_id in SINGLE_CASES
            and not (r.repro or {}).get("sleeper_id")
        ]
        flagged = sum(1 for r in attack_runs if OUTPUT_JUDGE.search(r.model_output or ""))
        exploited = len(set(SINGLE_CASES) & m.exploited)
        print(
            f"| {label} | {truth} | {exploited}/{len(attack_runs)} | {flagged}/{len(attack_runs)} |"
        )
    print()
    print(
        "Scope: one synthetic suite and a deterministic scripted agent. This shows the verdict follows"
    )
    print("state, not wording; it is not a detection rate for real agents or attacks.")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
