"""Unit tests for ScriptedAgent execution across benign tasks and policy variations."""

from __future__ import annotations

import hashlib
import json

import pytest
from agentbreak.domain.policy import compute_policy_hash
from agentbreak.engine.loop import run_once
from agentbreak.sandbox.acme.user_tasks import (
    ALL_BENIGN_TASKS,
    BT01_SummarizeNewestEmail,
)
from agentbreak.schemas.policy import ArgConstraint, Grant, Policy
from agentbreak.targets.scripted import ScriptedTarget

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


@pytest.fixture
def full_policy() -> Policy:
    grants = [Grant(tool=t) for t in ALL_10_TOOLS]
    return Policy(
        id="pol_full",
        name="Full Policy",
        grants=grants,
        hash=compute_policy_hash(grants),
        created_at="2026-10-10T00:00:00Z",
    )


@pytest.fixture
def no_send_email_policy() -> Policy:
    grants = [Grant(tool=t) for t in ALL_10_TOOLS if t != "send_email"]
    return Policy(
        id="pol_no_send_email",
        name="Policy without send_email",
        grants=grants,
        hash=compute_policy_hash(grants),
        created_at="2026-10-10T00:00:00Z",
    )


@pytest.fixture
def restricted_send_email_policy() -> Policy:
    grants = []
    for t in ALL_10_TOOLS:
        if t == "send_email":
            grants.append(
                Grant(
                    tool="send_email",
                    constraints=[
                        ArgConstraint(
                            arg="to",
                            kind="domain_allowlist",
                            values=["acme.test"],
                        ),
                        ArgConstraint(
                            arg="bcc",
                            kind="domain_allowlist",
                            values=["acme.test"],
                        ),
                    ],
                )
            )
        else:
            grants.append(Grant(tool=t))
    return Policy(
        id="pol_restricted_send_email",
        name="Policy with send_email restricted to acme.test",
        grants=grants,
        hash=compute_policy_hash(grants),
        created_at="2026-10-10T00:00:00Z",
    )


@pytest.mark.parametrize("task_cls", ALL_BENIGN_TASKS, ids=lambda t: getattr(t, "BENIGN_ID", t.ID))
def test_scripted_agent_passes_all_benign_tasks(task_cls: type, full_policy: Policy) -> None:
    target = ScriptedTarget()
    task = task_cls()
    outcome = run_once(
        target=target,
        policy=full_policy,
        user_task=task,
    )
    assert outcome.utility is True, f"Task {task.ID} failed utility check under full policy"


def test_scripted_agent_execution_determinism(full_policy: Policy) -> None:
    """Three repetitions must give byte-identical message lists and hash equality."""
    target = ScriptedTarget()
    task = BT01_SummarizeNewestEmail()

    hashes = []
    for _ in range(3):
        outcome = run_once(
            target=target,
            policy=full_policy,
            user_task=task,
        )
        msg_str = json.dumps(outcome.messages, sort_keys=True, default=str)
        hashes.append(hashlib.sha256(msg_str.encode()).hexdigest())

    assert hashes[0] == hashes[1] == hashes[2]


def test_no_send_email_policy_fails_exact_tasks(no_send_email_policy: Policy) -> None:
    """With send_email removed from policy, exactly BT-02, 04, 05, 10 fail utility (4 fail)."""
    target = ScriptedTarget()
    results: dict[str, bool] = {}

    for task_cls in ALL_BENIGN_TASKS:
        task = task_cls()
        outcome = run_once(
            target=target,
            policy=no_send_email_policy,
            user_task=task,
        )
        task_id = getattr(task_cls, "BENIGN_ID", task.ID)
        results[task_id] = outcome.utility is True

    failed = [tid for tid, passed in results.items() if not passed]
    passed = [tid for tid, passed in results.items() if passed]

    assert sorted(failed) == ["BT-02", "BT-04", "BT-05", "BT-10"]
    assert len(failed) == 4
    assert len(passed) == 6


def test_restricted_domain_policy_fails_only_bt05(restricted_send_email_policy: Policy) -> None:
    """With to/bcc restricted to acme.test, exactly BT-05 fails (sends to partner@partnerco.test)."""
    target = ScriptedTarget()
    results: dict[str, bool] = {}

    for task_cls in ALL_BENIGN_TASKS:
        task = task_cls()
        outcome = run_once(
            target=target,
            policy=restricted_send_email_policy,
            user_task=task,
        )
        task_id = getattr(task_cls, "BENIGN_ID", task.ID)
        results[task_id] = outcome.utility is True

    failed = [tid for tid, passed in results.items() if not passed]
    assert failed == ["BT-05"]
