"""Record frontend mock fixtures from the REAL API after a real demo run.

Usage: uv run python scripts/gen_mocks.py
Runs against a throwaway SQLite file, never ./data. Every fixture is a recorded response,
so mock mode shows what the product actually produced (simulated target), not invented data.
Validate afterwards with scripts/check_mocks.py.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

MOCK_DIR = Path(__file__).resolve().parents[1] / "frontend" / "src" / "mocks"


def main() -> int:
    os.environ["AGENTBREAK_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "mocks.db")
    from agentbreak.main import create_app
    from fastapi.testclient import TestClient

    out: dict[str, Any] = {}
    with TestClient(create_app()) as c:

        def get(path: str) -> Any:
            r = c.get(f"/api/v1{path}")
            r.raise_for_status()  # never record an error body as a fixture
            return r.json()

        def post(path: str, body: Any = None) -> Any:
            r = c.post(f"/api/v1{path}", json=body)
            r.raise_for_status()
            return r.json()

        demo = post("/demo/run")
        while demo["status"] in ("queued", "running"):
            time.sleep(0.2)
            demo = get(f"/demo/{demo['id']}")
        if demo["status"] != "completed":
            print(f"demo failed: {demo.get('error')}", file=sys.stderr)
            return 1
        links = demo["links"]
        run_id = links["run"].rsplit("/", 1)[1]
        audit_id = links["audit"].rsplit("/", 1)[1]
        sleeper_id = links["sleeper"].rsplit("/", 1)[1]
        report_id = links["report"].rsplit("/", 1)[1]
        active = get("/targets/tgt_demo_scripted")["active_policy_id"]
        findings = get("/findings")
        as04 = next(f for f in findings["items"] if f["case_id"] == "AS-04")
        fixes = get(f"/fix-evals?audit_id={audit_id}&limit=200")
        delete_fix = next(f for f in fixes["items"] if f["fix"]["tool"] == "delete_file")

        out = {
            "health": get("/health"),
            "meta": get("/meta"),
            "targets": get("/targets"),
            "target_test": post("/targets/tgt_demo_scripted/test"),
            "suite_acme": get("/suites/acme"),
            "scenarios": get("/scenarios"),
            "attack_cases": get("/attack-cases"),
            "policies": get("/policies"),
            "policy_diff": get(f"/policies/pol_full/diff/{active}"),
            "runs_page": get(f"/runs?limit=20&kind=attack&ids={run_id}"),
            "run_as04": get(f"/runs/{run_id}"),
            "trace_as04": get(f"/runs/{run_id}/trace"),
            "snapshots_as04": get(f"/runs/{run_id}/snapshots"),
            "graph_as04": get(f"/runs/{run_id}/graph"),
            "verify_as04": post(f"/runs/{run_id}/verify"),
            "sleeper_runs": get("/sleeper-runs"),
            "sleeper_run_as05": get(f"/sleeper-runs/{sleeper_id}"),
            "discovery_campaign": post(
                "/discovery",
                {
                    "target_id": "tgt_demo_scripted",
                    "policy_id": "pol_full",
                    "budget": {"max_attempts": 6},
                },
            ),
            "findings_page": findings,
            "finding_as04": get(f"/findings/{as04['id']}"),
            "graph_aggregate": get("/graph"),
            "audits_page": get("/audits"),
            "audit_demo": get(f"/audits/{audit_id}"),
            "fix_suggestions": get(f"/audits/{audit_id}/fixes"),
            "fix_evals_page": fixes,
            "fix_eval_remove_delete_file": delete_fix,
            "dashboard_summary": get("/dashboard/summary"),
            "report_demo": get(f"/reports/{report_id}"),
            "demo_status": demo,
        }

    for name, data in out.items():
        (MOCK_DIR / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {len(out)} fixtures into {MOCK_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
