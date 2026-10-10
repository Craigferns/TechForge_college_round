"""Re-verify a stored verdict from its persisted PRE/POST snapshots (API + `cli verify`)."""

from __future__ import annotations

import sqlite3

from agentbreak.domain.verdict import evaluate_verdict
from agentbreak.repo.run_repo import RunRepo
from agentbreak.sandbox.acme.env import AcmeEnv
from agentbreak.schemas.run import Verdict


def reverify_run(run_id: str, conn: sqlite3.Connection) -> Verdict:
    """Recompute the verdict and compare hashes. Raises ValueError when it cannot be checked:
    a verification that cannot run must never be reported as a match (fail closed)."""
    repo = RunRepo(conn)
    run = repo.get(run_id)
    if run is None:
        raise ValueError(f"Run '{run_id}' not found.")
    stored = repo.get_verdict(run_id)
    if stored is None:
        raise ValueError(f"Run '{run_id}' has no stored verdict.")
    snapshots = repo.get_snapshots(run_id)
    if snapshots is None:
        raise ValueError(f"Run '{run_id}' has no stored snapshots; it cannot be re-verified.")
    recomputed = evaluate_verdict(
        case_id=run.case_id,
        pre=AcmeEnv.model_validate(snapshots.pre),
        post=AcmeEnv.model_validate(snapshots.post),
        created_at=stored.created_at,
        is_control=bool(run.repro and run.repro.get("is_control")),
        # The runner derives says_only from the target profile; the stored classification records it.
        says_only=stored.classification == "said_not_did",
    )
    recomputed.matches_stored = recomputed.verdict_hash == stored.verdict_hash
    return recomputed
