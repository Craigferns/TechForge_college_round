"""Candidate fix generation logic for audited permissions and exploits."""

from __future__ import annotations

from agentbreak.schemas.audit import PermissionAudit
from agentbreak.schemas.fix import FixSpec, FixSuggestion


def generate_candidate_fixes(
    audit: PermissionAudit, target_kind: str = "scripted"
) -> list[FixSuggestion]:
    """Deterministically derive fix suggestions from permission audit results (PLAN §11.4)."""
    suggestions: list[FixSuggestion] = []

    # 1. remove_permission for each tool with >= 1 enabling exploit
    for row in audit.rows:
        if row.enabled_exploits:
            case_ids = [e.case_id for e in row.enabled_exploits]
            suggestions.append(
                FixSuggestion(
                    id=f"fix_rm_{row.tool}",
                    fix=FixSpec(
                        kind="remove_permission",
                        tool=row.tool,
                        args=[],
                        domains=[],
                    ),
                    title=f"Remove '{row.tool}' Permission",
                    description=f"Eliminates '{row.tool}' grant from policy to mitigate {', '.join(case_ids)}.",
                    targeted_exploits=case_ids,
                )
            )

    # 2. restrict_arg for each tool with suggested_scope
    for row in audit.rows:
        if row.suggested_scope:
            scope = row.suggested_scope
            case_ids = [e.case_id for e in row.enabled_exploits]
            suggestions.append(
                FixSuggestion(
                    id=f"fix_scope_{row.tool}",
                    fix=FixSpec(
                        kind="restrict_arg",
                        tool=row.tool,
                        args=scope.args,
                        domains=scope.domain_allowlist,
                    ),
                    title=f"Restrict '{row.tool}' to Trusted Domains",
                    description=(
                        f"Enforces allowlist on '{', '.join(scope.args)}' matching benign ground-truth "
                        f"domains: {', '.join(scope.domain_allowlist)}."
                    ),
                    targeted_exploits=case_ids,
                )
            )

    # 3. Hand-written contrast fix: restrict send_email to acme.test only (showing a non-zero price)
    has_send_email = any(r.tool == "send_email" and r.enabled_exploits for r in audit.rows)
    if has_send_email:
        suggestions.append(
            FixSuggestion(
                id="fix_scope_send_email_contrast",
                fix=FixSpec(
                    kind="restrict_arg",
                    tool="send_email",
                    args=["to", "bcc"],
                    domains=["acme.test"],
                ),
                title="Restrict 'send_email' to Internal Domain Only (Contrast)",
                description="Restricts emails strictly to acme.test; breaks external partner sync BT-05.",
                targeted_exploits=["AS-01", "AS-02", "AS-05"],
            )
        )

    # 4. Defense and prompt hardening for openai_compat targets only
    if target_kind == "openai_compat":
        suggestions.extend(
            [
                FixSuggestion(
                    id="fix_defense_repeat_prompt",
                    fix=FixSpec(
                        kind="defense",
                        defense_name="repeat_user_prompt",
                    ),
                    title="Agent Pipeline: Repeat User Prompt",
                    description="Repeats the original user instruction after each tool call to reinforce benign intent.",
                    targeted_exploits=["AS-01", "AS-04"],
                ),
                FixSuggestion(
                    id="fix_defense_spotlighting",
                    fix=FixSpec(
                        kind="defense",
                        defense_name="spotlighting_with_delimiting",
                    ),
                    title="Agent Pipeline: Spotlighting With Delimiters",
                    description="Wraps external untrusted tool outputs in explicit structural delimiters.",
                    targeted_exploits=["AS-01", "AS-03", "AS-04"],
                ),
                FixSuggestion(
                    id="fix_prompt_hardening_system",
                    fix=FixSpec(
                        kind="prompt_hardening",
                        prompt_id="prompt_strict_corporate",
                    ),
                    title="Hardened Corporate Policy Prompt Addendum",
                    description="Injects strict safety guidelines forbidding secondary actions without explicit authorization.",
                    targeted_exploits=["AS-01", "AS-06", "AS-07"],
                ),
            ]
        )

    return suggestions
