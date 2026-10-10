"""AgentBreak pure domain modules."""

from agentbreak.domain.permissions import (
    ACME_TOOL_EFFECTS,
    EXCESS_PERMISSIONS,
    NEEDED_PERMISSIONS,
    get_tool_effect,
)
from agentbreak.domain.policy import (
    canonical_grants_repr,
    compute_policy_hash,
    diff_policies,
)
from agentbreak.domain.severity import (
    CASE_SEVERITY_MAP,
    determine_severity,
    get_case_impact_class,
    get_case_severity,
)
from agentbreak.domain.verdict import (
    VERIFIER_VERSION,
    compute_verdict_hash,
    evaluate,
)

__all__ = [
    "compute_policy_hash",
    "diff_policies",
    "canonical_grants_repr",
    "ACME_TOOL_EFFECTS",
    "NEEDED_PERMISSIONS",
    "EXCESS_PERMISSIONS",
    "get_tool_effect",
    "evaluate",
    "compute_verdict_hash",
    "VERIFIER_VERSION",
    "determine_severity",
    "get_case_severity",
    "get_case_impact_class",
    "CASE_SEVERITY_MAP",
]
