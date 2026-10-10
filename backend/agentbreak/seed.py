"""Database seeding script establishing initial benchmark targets and policies."""

from __future__ import annotations

import datetime
import sqlite3

from agentbreak.domain.permissions import NEEDED_PERMISSIONS
from agentbreak.domain.policy import compute_policy_hash
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.schemas.policy import Grant, Policy
from agentbreak.schemas.target import Target

ALL_10_TOOLS = [
    "list_inbox",
    "read_email",
    "send_email",
    "list_files",
    "read_file",
    "share_file",
    "delete_file",
    "write_memory",
    "read_memory",
    "set_role",
]


def seed_database(conn: sqlite3.Connection) -> tuple[int, int]:
    """Seed default policies and targets into the database if not already present.

    Returns (policies_created, targets_created).
    """
    now = datetime.datetime.now(datetime.UTC).isoformat()
    policy_repo = PolicyRepo(conn)
    target_repo = TargetRepo(conn)

    policies_created = 0
    targets_created = 0

    # 1. Full Policy (all 10 tools granted without constraints)
    full_grants = [Grant(tool=t) for t in ALL_10_TOOLS]
    full_hash = compute_policy_hash(full_grants)
    if not policy_repo.get("pol_full"):
        policy_repo.create(
            Policy(
                id="pol_full",
                name="Full Access Policy (All Tools)",
                parent_id=None,
                grants=full_grants,
                hash=full_hash,
                created_at=now,
            )
        )
        policies_created += 1

    # 2. Needed Policy (exact 8 benign needed tools)
    needed_grants = [Grant(tool=t) for t in sorted(NEEDED_PERMISSIONS)]
    needed_hash = compute_policy_hash(needed_grants)
    if not policy_repo.get("pol_needed"):
        policy_repo.create(
            Policy(
                id="pol_needed",
                name="Least Privilege Policy (8 Needed Tools)",
                parent_id=None,
                grants=needed_grants,
                hash=needed_hash,
                created_at=now,
            )
        )
        policies_created += 1

    # 3. Simulated Scripted Target
    if not target_repo.get("tgt_demo_scripted"):
        target_repo.create(
            Target(
                id="tgt_demo_scripted",
                name="Simulated Target (Scripted)",
                kind="scripted",
                config={},
                active_policy_id="pol_full",
                created_at=now,
            )
        )
        targets_created += 1

    return policies_created, targets_created
