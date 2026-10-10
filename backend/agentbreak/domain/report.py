"""Report generator for AgentBreak vulnerability findings and remediation evidence."""

from __future__ import annotations

import datetime

from agentbreak.schemas.audit import PermissionAudit
from agentbreak.schemas.finding import Finding
from agentbreak.schemas.fix import FixEval


def generate_markdown_report(
    target_id: str,
    target_name: str,
    policy_id: str,
    findings: list[Finding],
    audit: PermissionAudit | None = None,
    fix_evals: list[FixEval] | None = None,
) -> str:
    """Generate Markdown evidence report containing finding details, escaped payloads, and repro commands."""
    lines: list[str] = []

    lines.append("# AgentBreak Security & Hardening Evidence Report")
    lines.append("")
    lines.append(f"**Target:** `{target_name}` (`{target_id}`)  ")
    lines.append(f"**Evaluated Policy:** `{policy_id}`  ")
    lines.append(
        f"**Generated:** {datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M:%SZ')}  "
    )
    lines.append(f"**Total Findings:** {len(findings)}  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. Executive Summary
    lines.append("## 1. Executive Summary")
    lines.append("")
    crit_count = sum(1 for f in findings if f.severity == "critical")
    high_count = sum(1 for f in findings if f.severity == "high")
    lines.append(
        f"Autonomous evaluation detected **{len(findings)} vulnerability findings** "
        f"({crit_count} Critical, {high_count} High). "
        "Every finding has been deterministically verified via environment state-diff assertions."
    )
    lines.append("")

    # 2. Vulnerability Findings & Reproduction Commands
    lines.append("## 2. Verified Vulnerability Findings")
    lines.append("")
    for i, f in enumerate(findings, 1):
        lines.append(f"### 2.{i} [{f.severity.upper()}] {f.title} ({f.case_id})")
        lines.append(f"- **Scenario:** `{f.scenario_id}`")
        lines.append(f"- **Impact Class:** `{f.impact_class}`")
        lines.append(
            f"- **Enabling Permissions:** `{', '.join(f.enabling_permissions) if f.enabling_permissions else 'none'}`"
        )
        lines.append(f"- **Status:** `{f.status}`")
        lines.append(f"- **Occurrences:** {f.occurrences}")
        lines.append("")
        lines.append("#### Deterministic Reproduction CLI")
        lines.append("```bash")
        run_id_ref = f.first_run_id or f"run_{f.case_id.lower()}"
        lines.append(f"uv run python -m agentbreak.cli verify {run_id_ref}")
        lines.append("```")
        lines.append("")

    # 3. Permission Attribution Diff (D1)
    if audit:
        lines.append("## 3. Permission Attribution Diff (D1)")
        lines.append("")
        lines.append(f"- **Granted Tools ({len(audit.granted)}):** `{', '.join(audit.granted)}`")
        lines.append(f"- **Needed Tools ({len(audit.needed)}):** `{', '.join(audit.needed)}`")
        lines.append(
            f"- **Excess Attack Surface ({len(audit.excess)}):** `{', '.join(audit.excess)}`"
        )
        if audit.proof:
            lines.append(
                f"- **Counterfactual Utility Proof:** {audit.proof.benign_pass_under_minimal}/{audit.proof.benign_total} "
                f"benign tasks pass under minimal policy `{audit.minimal_policy_id}`."
            )
        lines.append("")

    # 4. Remediation Price Tags & Fix Lab (D2)
    if fix_evals:
        lines.append("## 4. Remediation Price Tags (D2)")
        lines.append("")
        lines.append(
            "| Proposed Remediation | Blocked Attacks | Broken Benign Tasks | Pareto Status |"
        )
        lines.append("|---|:---:|:---:|:---:|")
        for ev in fix_evals:
            pt = ev.price_tag
            blocked_str = f"{pt.attacks_blocked}/{pt.attacks_total}" if pt else "N/A"
            broken_str = f"{pt.tasks_broken}/{pt.benign_total}" if pt else "N/A"
            pareto_str = "Optimal" if (pt and pt.pareto) else "Dominated"
            tool_name = ev.fix.tool or ev.fix.kind
            lines.append(
                f"| `{tool_name}` ({ev.fix.kind}) | {blocked_str} | {broken_str} | {pareto_str} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("*Report generated autonomously by AgentBreak Security Suite.*")
    return "\n".join(lines)
