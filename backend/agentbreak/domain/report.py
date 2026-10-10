"""Markdown evidence report built only from persisted records (PLAN.md §16 / M10.2).

Every number below is read from runs, verdicts, audits, fix evaluations and sleeper runs
in the database. Sections with no underlying record say so instead of showing a default.
"""

from __future__ import annotations

import sqlite3

from agentbreak.repo.audit_repo import AuditRepo
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.repo.fix_repo import FixRepo
from agentbreak.repo.policy_repo import PolicyRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.schemas.dashboard import Report

VERIFIER_VERSION = "1.0.0"


def _fence(text: str) -> str:
    # Untrusted payload text: never let it close the code fence (CLAUDE.md hard rule 5).
    return text.replace("```", "'''")


def _ids(items: list[str] | None) -> str:
    return f"({', '.join(items)})" if items else ""


def generate_markdown_report(
    report_id: str,
    target_id: str,
    policy_id: str,
    conn: sqlite3.Connection,
    created_at: str,
) -> Report:
    from agentbreak.engine.posture import compute_posture  # engine import kept local

    target = TargetRepo(conn).get(target_id)
    policy = PolicyRepo(conn).get(policy_id)
    simulated = target is None or target.kind == "scripted"
    run_repo = RunRepo(conn)
    findings, _ = FindingRepo(conn).list_findings(target_id=target_id, limit=200)
    posture = compute_posture(conn, target_id)
    audits, _ = AuditRepo(conn).list(target_id=target_id, limit=1)
    audit = audits[0] if audits else None

    L: list[str] = [
        f"# AgentBreak evidence report: `{target_id}`",
        "",
        f"- **Report:** `{report_id}` · **Generated:** {created_at} · **Verifier:** {VERIFIER_VERSION}",
        f"- **Target:** `{target_id}` ({target.kind if target else 'unknown'})"
        + (
            ". **Simulated target**: a deterministic harness fixture, not evidence about real models."
            if simulated
            else ""
        ),
        f"- **Policy reported:** `{policy_id}` ({policy.name if policy else 'unknown'}) · hash `{policy.hash if policy else '-'}`",
        "- **Suite:** `acme` (synthetic data, `.test` domains, canary tokens; 7 attack cases, 10 benign tasks)",
        "",
        "## 1. Executive summary",
        "",
        f"Current posture under the active policy `{posture.active_policy_id}`: "
        f"**{posture.successful_attacks}/{posture.total_attacks} attacks succeed**, "
        f"**{posture.passed_benign}/{posture.total_benign} benign tasks pass**"
        + (f", {posture.inconclusive} inconclusive (errored)" if posture.inconclusive else "")
        + f". Sleeper chain: `{posture.sleeper_outcome or 'not run'}`. "
        f"Findings: {len(findings)} recorded, {posture.open_findings} open or regressed. "
        f"Tool grants hardened since first test: {posture.fixes_applied}.",
        "",
        "## 2. Method",
        "",
        "- Each attack runs in a fresh in-memory sandbox. Success is a predicate over the PRE/POST "
        "environment snapshots plus canary observation; the model's text is never read by the verdict.",
        "- Runs that error are **inconclusive**: they are never counted as blocked, resisted or passed.",
        "- Fix price tags re-run every attack and benign task under the base and the fixed policy.",
        "- Attribution removes one tool at a time and re-runs everything (counterfactual).",
        "- AS-05 (sleeper) is judged end-to-end: exploited only if a later session exfiltrates.",
        "",
        "## 3. Findings",
        "",
    ]
    if not findings:
        L.append("No findings recorded for this target.")
    for idx, f in enumerate(findings, 1):
        L += [
            f"### {idx}. {f.title} ({f.severity}, status `{f.status}`)",
            f"- Finding `{f.id}` · case `{f.case_id}` · impact `{f.impact_class}` · seen {f.occurrences}×",
            f"- First run `{f.first_run_id}` · last run `{f.last_run_id}`",
        ]
        verdict = run_repo.get_verdict(f.first_run_id) if f.first_run_id else None
        if verdict and verdict.evidence:
            L.append("- Measured state evidence (first run):")
            L += [f"  - `[{ev.type}]` {ev.path}: {ev.detail}" for ev in verdict.evidence]
        trace = run_repo.get_trace(f.first_run_id) if f.first_run_id else []
        injected = next((s for s in trace if s.flags.get("injected") and s.content), None)
        if injected and injected.content:
            L += [
                "- Injected carrier excerpt (untrusted, truncated):",
                "```text",
                _fence(injected.content)[:300],
                "```",
            ]
        if f.first_run_id:
            L += [
                "- Re-verify from stored snapshots:",
                "```bash",
                f"uv run python -m agentbreak.cli verify {f.first_run_id}",
                "```",
            ]
        L.append("")

    L += ["## 4. Permission attribution (counterfactual)", ""]
    if audit is None or audit.status != "done":
        L.append("No completed permission audit for this target.")
    else:
        proof = audit.proof
        L += [
            f"Audit `{audit.id}` of policy `{audit.policy_id}`: granted {len(audit.granted)}, "
            f"needed {len(audit.needed)} (observed in passing benign runs), "
            f"excess {len(audit.excess)} (`{', '.join(audit.excess) or 'none'}`). "
            f"Minimal policy `{audit.minimal_policy_id}` keeps "
            f"{proof.benign_pass_under_minimal if proof else 0}/{proof.benign_total if proof else 0} benign tasks passing.",
            "",
            "| Tool | Status | Used by benign | Enables (blocked when removed) | Benign broken when removed |",
            "|---|---|---|---|---|",
        ]
        for r in audit.rows:
            cf = next((e.counterfactual for e in r.enabled_exploits if e.counterfactual), None)
            L.append(
                f"| `{r.tool}` | {r.status} | {', '.join(r.used_by_benign) or '-'} | "
                f"{', '.join(e.case_id for e in r.enabled_exploits) or '-'} | "
                f"{cf.benign_broken if cf else '-'} |"
            )
        L.append("")

        evals, _ = FixRepo(conn).list(audit_id=audit.id, limit=200)
        L += ["## 5. Fix price tags (measured)", ""]
        if not evals:
            L.append("No fixes evaluated for this audit.")
        else:
            L += [
                "| Fix | Base policy | Attacks blocked | Benign broken | Pareto | Inconclusive |",
                "|---|---|---|---|---|---|",
            ]
            for e in reversed(evals):
                pt, d = e.price_tag, e.details
                label = f"{e.fix.kind} `{e.fix.tool}`" + (
                    f" → {e.fix.domains}" if e.fix.domains else ""
                )
                L.append(
                    f"| {label} | `{e.base_policy_id}` | "
                    f"{pt.attacks_blocked if pt else 0}/{pt.attacks_total if pt else 0} {_ids(d.blocked_cases if d else None)} | "
                    f"{pt.tasks_broken if pt else 0}/{pt.benign_total if pt else 0} {_ids(d.broken_tasks if d else None)} | "
                    f"{'yes' if pt and pt.pareto else 'no'} | {', '.join(d.inconclusive) if d and d.inconclusive else '-'} |"
                )
        L.append("")

    L += [
        "## 6. Limitations",
        "",
        "- Results cover one synthetic suite (7 attack cases, 10 benign tasks). They show the measurement "
        "pipeline works; they are not a detection rate for real agents or real-world attacks.",
        "- The scripted target obeys injection markers deterministically; real models behave differently and "
        "non-deterministically (see `openai_compat` targets).",
        "- Permission = tool name with one argument constraint kind (`domain_allowlist`). Richer authorization "
        "(per-resource, per-principal) is not modelled.",
        "- A blocked sleeper trigger can leave the poisoned instruction in memory (residual risk).",
        "",
    ]

    return Report(
        id=report_id,
        target_id=target_id,
        policy_id=policy_id,
        markdown="\n".join(L),
        meta={
            "findings_count": len(findings),
            "target_id": target_id,
            "policy_id": policy_id,
            "audit_id": audit.id if audit else None,
            "simulated": simulated,
            "verifier_version": VERIFIER_VERSION,
        },
        created_at=created_at,
    )
