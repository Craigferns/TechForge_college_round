"""Command line interface for AgentBreak."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agentbreak.main import create_app


def export_openapi(output_path: Path) -> None:
    """Generate openapi.json from FastAPI schema."""
    app = create_app()
    openapi_schema = app.openapi()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"OpenAPI schema successfully exported to {output_path}")


def check_suite(suite_name: str) -> None:
    """Validate benign ground truths and vector exposures for a test suite."""
    if suite_name != "acme":
        print(f"Error: Unknown suite '{suite_name}'. Supported suites: acme")
        sys.exit(1)

    from agentbreak.sandbox.acme.suite import (
        compute_needed_permissions,
        evaluate_task_ground_truth,
    )
    from agentbreak.sandbox.acme.user_tasks import ALL_BENIGN_TASKS

    print("=" * 70)
    print(f"AGENTBREAK SUITE INTEGRITY CHECK: {suite_name.upper()}")
    print("=" * 70)

    vector_exposures = {
        "BT-01": "inj_email_body (e-1003)",
        "BT-08": "inj_doc_content (f-004)",
        "BT-10": "inj_email_body (e-1003)",
    }

    passed_count = 0
    for task_cls in ALL_BENIGN_TASKS:
        task_id = getattr(task_cls, "BENIGN_ID", task_cls.ID)
        passed, msg = evaluate_task_ground_truth(task_cls)
        vector_str = (
            f" | Exposes: {vector_exposures[task_id]}" if task_id in vector_exposures else ""
        )
        if passed:
            passed_count += 1
            print(f"  [PASS] {task_id:6} utility=True {vector_str}")
        else:
            print(f"  [FAIL] {task_id:6} utility=False ({msg})")

    needed = sorted(compute_needed_permissions())
    print("=" * 70)
    print(
        f"Result: {passed_count}/{len(ALL_BENIGN_TASKS)} benign ground truths passed with utility=True"
    )
    print(f"Computed Needed Tools ({len(needed)} tools): {', '.join(needed)}")
    print("=" * 70)

    if passed_count != len(ALL_BENIGN_TASKS):
        sys.exit(1)


def seed_cmd() -> None:
    """Seed benchmark targets and default policies into SQLite."""
    from agentbreak.config import get_settings
    from agentbreak.db import get_connection, migrate
    from agentbreak.seed import seed_database

    settings = get_settings()
    conn = get_connection(settings.db_path)
    migrate(conn)
    p_count, t_count = seed_database(conn)
    print(
        f"Database seeded successfully ({settings.db_path}): "
        f"seeded {p_count} new policies, {t_count} new targets."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentBreak CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser(
        "export-openapi", help="Export OpenAPI schema to openapi.json"
    )
    export_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("openapi.json"),
        help="Target output file path",
    )

    suite_parser = subparsers.add_parser(
        "check-suite", help="Validate benchmark suite benign tasks and tools"
    )
    suite_parser.add_argument(
        "suite",
        type=str,
        default="acme",
        nargs="?",
        help="Suite identifier (default: acme)",
    )

    subparsers.add_parser("seed", help="Seed default targets and security policies")

    args = parser.parse_args()

    if args.command == "export-openapi":
        export_openapi(args.output)
    elif args.command == "check-suite":
        check_suite(args.suite)
    elif args.command == "seed":
        seed_cmd()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
