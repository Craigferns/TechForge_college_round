"""CI gate exit codes, fail-closed re-verification, and data-driven reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from agentbreak.db import get_connection
from agentbreak.domain.report import generate_markdown_report
from agentbreak.engine.ci import run_ci_gate
from agentbreak.engine.measure import measure_policy
from agentbreak.engine.verify import reverify_run
from agentbreak.seed import seed_database
from agentbreak.targets.scripted import ScriptedTarget

T = "tgt_demo_scripted"


def test_ci_gate_fails_on_full_policy_and_passes_on_hardened(tmp_path: Path) -> None:
    out = tmp_path / "ci.json"
    assert run_ci_gate(T, "pol_full", 0, 1.0, out) == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["summary"]["exploited"] == 7 and report["gate"]["passed"] is False
    assert report["target"]["simulated"] is True
    # A lenient gate on the same evidence passes: the threshold is the only difference.
    assert run_ci_gate(T, "pol_full", 7, 1.0, out) == 0


def test_ci_gate_infra_error_is_exit_2_not_a_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import agentbreak.engine.runner as runner

    def broken(_: Any) -> Any:
        raise ConnectionError("target down")

    monkeypatch.setattr(runner, "create_target", broken)
    out = tmp_path / "ci.json"
    # max_exploited=7 would pass if errors were miscounted as "not exploited".
    assert run_ci_gate(T, "pol_full", 7, 0.0, out) == 2
    assert json.loads(out.read_text(encoding="utf-8"))["summary"]["inconclusive"] == 17
    assert run_ci_gate(T, "pol_missing", 0, 1.0, out) == 2


def test_ci_gate_policy_file_is_measured(tmp_path: Path) -> None:
    """Policy-as-code: the committed example policy passes; the same grants minus scopes fail."""
    example = Path(__file__).resolve().parents[3] / "examples" / "hardened-policy.json"
    assert run_ci_gate(T, None, 0, 1.0, tmp_path / "ok.json", policy_file=example) == 0
    loose = [{"tool": g["tool"], "constraints": []} for g in json.loads(example.read_text())]
    (tmp_path / "loose.json").write_text(json.dumps(loose))
    assert (
        run_ci_gate(T, None, 0, 1.0, tmp_path / "bad.json", policy_file=tmp_path / "loose.json")
        == 1
    )


def test_reverify_matches_and_fails_closed_without_snapshots() -> None:
    conn = get_connection(":memory:")
    seed_database(conn)
    m = measure_policy("pol_full", T, conn, ScriptedTarget())
    rid = next(
        r
        for r in m.run_ids
        if conn.execute("SELECT kind FROM run WHERE id=?", (r,)).fetchone()[0] == "attack"
    )
    assert reverify_run(rid, conn).matches_stored is True
    conn.execute("DELETE FROM env_snapshot WHERE run_id = ?", (rid,))
    with pytest.raises(ValueError, match="cannot be re-verified"):
        reverify_run(rid, conn)


def test_report_has_no_unbacked_sections() -> None:
    conn = get_connection(":memory:")
    seed_database(conn)
    md = generate_markdown_report("rep_t", T, "pol_full", conn, "2026-10-11T00:00:00Z").markdown
    assert "No completed permission audit" in md
    assert "No findings recorded" in md
    assert "7/7" not in md  # nothing measured yet, so no headline numbers
    assert "Simulated target" in md
