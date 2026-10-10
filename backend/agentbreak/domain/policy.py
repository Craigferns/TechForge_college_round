"""Policy domain logic: canonical hashing and structural diffing."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from agentbreak.schemas.policy import Grant, Policy, PolicyDiff


def canonical_grants_repr(grants: list[Grant]) -> list[dict[str, Any]]:
    """Produce a canonically sorted dictionary structure for a list of grants.

    - Grants are sorted by tool name
    - Constraints within each grant are sorted by arg name
    - Values within each constraint are sorted
    """
    sorted_grants = sorted(grants, key=lambda g: g.tool)
    canonical: list[dict[str, Any]] = []

    for g in sorted_grants:
        sorted_constraints = sorted(g.constraints, key=lambda c: c.arg)
        canonical.append(
            {
                "tool": g.tool,
                "constraints": [
                    {
                        "arg": c.arg,
                        "kind": c.kind,
                        "values": sorted(c.values),
                    }
                    for c in sorted_constraints
                ],
            }
        )
    return canonical


def compute_policy_hash(grants: list[Grant]) -> str:
    """Compute deterministic SHA-256 hash for a policy's grants."""
    canonical = canonical_grants_repr(grants)
    encoded = json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return f"sha256:{digest}"


def diff_policies(policy_a: Policy, policy_b: Policy) -> PolicyDiff:
    """Compute structural grant deltas between two policies.

    - added_tools: tools present in policy_b but absent in policy_a
    - removed_tools: tools present in policy_a but absent in policy_b
    - constraint_changes: differences in arg constraints for shared tools
    """
    tools_a = {g.tool: g for g in policy_a.grants}
    tools_b = {g.tool: g for g in policy_b.grants}

    added_tools = sorted(tools_b.keys() - tools_a.keys())
    removed_tools = sorted(tools_a.keys() - tools_b.keys())

    shared_tools = sorted(tools_a.keys() & tools_b.keys())
    constraint_changes: list[dict[str, str]] = []

    for tool in shared_tools:
        grant_a = tools_a[tool]
        grant_b = tools_b[tool]
        constraints_a = {c.arg: sorted(c.values) for c in grant_a.constraints}
        constraints_b = {c.arg: sorted(c.values) for c in grant_b.constraints}

        if constraints_a != constraints_b:
            constraint_changes.append(
                {
                    "tool": tool,
                    "before": json.dumps(constraints_a),
                    "after": json.dumps(constraints_b),
                }
            )

    return PolicyDiff(
        policy_a=policy_a.id,
        policy_b=policy_b.id,
        added_tools=added_tools,
        removed_tools=removed_tools,
        constraint_changes=constraint_changes,
    )
