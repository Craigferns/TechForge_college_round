"""Permissions taxonomy and tool effect classes for AgentBreak."""

from __future__ import annotations

from typing import Literal

EffectClass = Literal[
    "read",
    "external_send",
    "acl_write",
    "destructive",
    "persistent_write",
    "privilege",
]

# Tool metadata for the Acme suite
ACME_TOOL_EFFECTS: dict[str, EffectClass] = {
    "list_inbox": "read",
    "read_email": "read",
    "send_email": "external_send",
    "list_files": "read",
    "read_file": "read",
    "share_file": "acl_write",
    "delete_file": "destructive",
    "read_memory": "read",
    "write_memory": "persistent_write",
    "set_role": "privilege",
}

# The 8 tools strictly required by the union of ground-truth benign tasks (BT-01...BT-10)
NEEDED_PERMISSIONS: frozenset[str] = frozenset(
    [
        "list_inbox",
        "read_email",
        "send_email",
        "list_files",
        "read_file",
        "share_file",
        "read_memory",
        "write_memory",
    ]
)

# Excess tools present in the unrestricted full policy (D1 differentiator)
EXCESS_PERMISSIONS: frozenset[str] = frozenset(
    [
        "delete_file",
        "set_role",
    ]
)


def get_tool_effect(tool_name: str) -> EffectClass:
    """Return the effect classification for a given tool."""
    return ACME_TOOL_EFFECTS.get(tool_name, "read")
