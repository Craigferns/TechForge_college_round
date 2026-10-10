"""Validate every frontend mock fixture against the API response model it stands in for.

Fails (exit 1) on a missing fixture, invalid JSON, or a schema mismatch — e.g. a recorded
error body. Regenerate fixtures with scripts/gen_mocks.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from agentbreak.schemas import (
    AttackCase,
    AttackGraph,
    DashboardSummary,
    DemoStatus,
    DiscoveryCampaign,
    Finding,
    FixEval,
    FixSuggestion,
    Health,
    Meta,
    Page,
    PermissionAudit,
    Policy,
    PolicyDiff,
    Report,
    Run,
    RunSummary,
    ScenarioSpec,
    SleeperRun,
    SnapshotPair,
    SuiteInfo,
    Target,
    TargetTestResult,
    TraceStep,
    Verdict,
)
from pydantic import TypeAdapter

MOCK_DIR = Path(__file__).resolve().parents[1] / "frontend" / "src" / "mocks"

FIXTURES: dict[str, Any] = {
    "health": Health,
    "meta": Meta,
    "targets": list[Target],
    "target_test": TargetTestResult,
    "suite_acme": SuiteInfo,
    "scenarios": list[ScenarioSpec],
    "attack_cases": list[AttackCase],
    "policies": list[Policy],
    "policy_diff": PolicyDiff,
    "runs_page": Page[RunSummary],
    "run_as04": Run,
    "trace_as04": list[TraceStep],
    "snapshots_as04": SnapshotPair,
    "graph_as04": AttackGraph,
    "verify_as04": Verdict,
    "sleeper_runs": Page[SleeperRun],
    "sleeper_run_as05": SleeperRun,
    "discovery_campaign": DiscoveryCampaign,
    "findings_page": Page[Finding],
    "finding_as04": Finding,
    "graph_aggregate": AttackGraph,
    "audits_page": Page[PermissionAudit],
    "audit_demo": PermissionAudit,
    "fix_suggestions": list[FixSuggestion],
    "fix_evals_page": Page[FixEval],
    "fix_eval_remove_delete_file": FixEval,
    "dashboard_summary": DashboardSummary,
    "report_demo": Report,
    "demo_status": DemoStatus,
}


def check_mocks() -> int:
    problems: list[str] = []
    for name, model in FIXTURES.items():
        path = MOCK_DIR / f"{name}.json"
        if not path.exists():
            problems.append(f"{name}: missing")
            continue
        try:
            TypeAdapter(model).validate_python(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:  # report every bad fixture, not just the first
            problems.append(f"{name}: {str(exc).splitlines()[0]}")
    for p in problems:
        print(f"FAIL {p}")
    print(f"{len(FIXTURES) - len(problems)}/{len(FIXTURES)} fixtures valid against API models")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(check_mocks())
