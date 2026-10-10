"""Unit tests for policy hashing, diffing, and PolicyRuntime enforcement."""

import pytest
from agentbreak.domain.policy import compute_policy_hash, diff_policies
from agentbreak.sandbox.policy_runtime import PermissionDenied, PolicyRuntime
from agentbreak.schemas.policy import ArgConstraint, Grant, Policy


def test_policy_hash_is_order_independent():
    """Test that grants in different order produce the exact same canonical SHA-256 hash."""
    grant1 = Grant(
        tool="send_email",
        constraints=[
            ArgConstraint(
                arg="to", kind="domain_allowlist", values=["partnerco.test", "acme.test"]
            ),
        ],
    )
    grant2 = Grant(tool="read_email", constraints=[])

    hash_a = compute_policy_hash([grant1, grant2])
    hash_b = compute_policy_hash([grant2, grant1])

    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_diff_policies():
    """Test policy diff correctly identifies added, removed, and constraint changes."""
    policy_a = Policy(
        id="pol_a",
        name="Policy A",
        grants=[
            Grant(tool="read_file", constraints=[]),
            Grant(tool="delete_file", constraints=[]),
            Grant(
                tool="send_email",
                constraints=[
                    ArgConstraint(arg="to", kind="domain_allowlist", values=["acme.test"]),
                ],
            ),
        ],
        hash="sha256:a",
        created_at="2026-10-10T12:00:00Z",
    )

    policy_b = Policy(
        id="pol_b",
        name="Policy B",
        grants=[
            Grant(tool="read_file", constraints=[]),
            Grant(tool="share_file", constraints=[]),  # Added
            # delete_file removed
            Grant(
                tool="send_email",
                constraints=[
                    ArgConstraint(
                        arg="to",
                        kind="domain_allowlist",
                        values=["acme.test", "partnerco.test"],  # Modified constraint
                    ),
                ],
            ),
        ],
        hash="sha256:b",
        created_at="2026-10-10T12:00:00Z",
    )

    diff = diff_policies(policy_a, policy_b)
    assert diff.added_tools == ["share_file"]
    assert diff.removed_tools == ["delete_file"]
    assert len(diff.constraint_changes) == 1
    assert diff.constraint_changes[0]["tool"] == "send_email"


def test_policy_runtime_ungranted_tool():
    """Test ungranted tool raises PermissionDenied and never executes the tool body."""
    executed = False

    def toy_tool():
        nonlocal executed
        executed = True
        return "done"

    runtime = PolicyRuntime(policy=[])  # Empty policy
    wrapped = runtime.wrap_tool(toy_tool, tool_name="delete_file")

    with pytest.raises(PermissionDenied) as exc_info:
        wrapped()

    assert exc_info.value.reason == "not_granted"
    assert exc_info.value.tool == "delete_file"
    assert executed is False  # Side effect did not happen


def test_policy_runtime_domain_allowlist_enforcement():
    """Test domain_allowlist rejects evil.test in to and bcc, accepts acme.test."""
    send_count = 0

    def send_email(to: list[str], subject: str, bcc: list[str] | None = None):
        nonlocal send_count
        send_count += 1
        return "sent"

    grant = Grant(
        tool="send_email",
        constraints=[
            ArgConstraint(arg="to", kind="domain_allowlist", values=["acme.test"]),
            ArgConstraint(arg="bcc", kind="domain_allowlist", values=["acme.test"]),
        ],
    )
    runtime = PolicyRuntime(policy=[grant])
    wrapped = runtime.wrap_tool(send_email)

    # Allowed invocation
    res = wrapped(to=["sam@acme.test"], subject="Hello", bcc=["kim@acme.test"])
    assert res == "sent"
    assert send_count == 1

    # Rejected in 'to'
    with pytest.raises(PermissionDenied) as exc_info:
        wrapped(to=["mallory@evil.test"], subject="Exfil")
    assert exc_info.value.reason == "domain_not_allowed"
    assert exc_info.value.arg == "to"
    assert send_count == 1  # Tool body was NOT executed

    # Rejected in 'bcc'
    with pytest.raises(PermissionDenied) as exc_info:
        wrapped(to=["sam@acme.test"], subject="Exfil", bcc=["mallory@evil.test"])
    assert exc_info.value.reason == "domain_not_allowed"
    assert exc_info.value.arg == "bcc"
    assert send_count == 1  # Tool body was NOT executed
