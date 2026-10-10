"""Exploit-to-permission attribution from measured counterfactuals (PLAN.md §10.2 / D1).

Pure: the inputs are outcome sets produced by real runs (engine/measure.py); this module
only decides what they mean. A tool *enables* an exploit when the exploit succeeds with the
tool granted and is resisted when only that tool is removed.
"""

from __future__ import annotations

from collections.abc import Mapping, Set

from agentbreak.schemas.audit import CounterfactualResult, EnabledExploit


def enabling_exploits(
    base_exploited: Set[str],
    without_tool_resisted: Set[str],
    benign_broken_without_tool: int,
    finding_ids: Mapping[str, str],
) -> list[EnabledExploit]:
    """Exploits that succeeded under the base policy and were resisted once the tool was removed."""
    return [
        EnabledExploit(
            case_id=case_id,
            finding_id=finding_ids.get(case_id),
            role="enabling",
            counterfactual=CounterfactualResult(
                blocked=True, benign_broken=benign_broken_without_tool
            ),
        )
        for case_id in sorted(base_exploited & without_tool_resisted)
    ]


def observed_exploits(
    exploited_runs_using_tool: Set[str], finding_ids: Mapping[str, str]
) -> list[EnabledExploit]:
    """Without counterfactual runs we can only say the exploit run *called* the tool."""
    return [
        EnabledExploit(case_id=c, finding_id=finding_ids.get(c), role="observed")
        for c in sorted(exploited_runs_using_tool)
    ]
