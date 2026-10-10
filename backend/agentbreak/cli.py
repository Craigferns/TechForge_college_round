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


def run_cmd(target_name: str, case_id: str, policy_name: str | None = None) -> None:
    """Execute a single attack case evaluation run via CLI."""
    import uuid

    from agentbreak.attacks.scenarios import get_attack_case
    from agentbreak.config import get_settings
    from agentbreak.db import get_connection, migrate
    from agentbreak.engine.runner import execute_run, utc_now_iso
    from agentbreak.repo.policy_repo import PolicyRepo
    from agentbreak.repo.run_repo import RunRepo
    from agentbreak.repo.target_repo import TargetRepo
    from agentbreak.schemas.run import Run
    from agentbreak.seed import seed_database

    settings = get_settings()
    conn = get_connection(settings.db_path)
    migrate(conn)
    seed_database(conn)

    target_repo = TargetRepo(conn)
    policy_repo = PolicyRepo(conn)
    run_repo = RunRepo(conn)

    # 1. Resolve Target
    target_model = target_repo.get(target_name)
    if not target_model:
        # Search by prefix or normalized name
        norm_name = target_name.replace("-", "_")
        for t in target_repo.list():
            if (
                t.id == target_name
                or t.id == f"tgt_{norm_name}"
                or norm_name in t.id
                or target_name.lower() in t.name.lower()
            ):
                target_model = t
                break
    if not target_model:
        print(f"Error: Target '{target_name}' could not be resolved.")
        sys.exit(1)

    # 2. Resolve Policy
    pol_id = policy_name or "pol_full"
    policy_model = policy_repo.get(pol_id)
    if not policy_model:
        for p in policy_repo.list():
            if p.id == pol_id or pol_id in p.name.lower():
                policy_model = p
                break
    if not policy_model:
        print(f"Error: Policy '{pol_id}' could not be resolved.")
        sys.exit(1)

    # 3. Resolve Attack Case
    try:
        case = get_attack_case(case_id)
    except KeyError:
        print(f"Error: Unknown attack case ID '{case_id}'.")
        sys.exit(1)

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    run = Run(
        id=run_id,
        kind="attack",
        target_id=target_model.id,
        policy_id=policy_model.id,
        suite="acme",
        case_id=case.id,
        scenario_id=case.scenario_id,
        user_task_id=case.carrier_task_id,
        injection_task_id=case.injection_task_id,
        template_id="authority_note",
        origin="static",
        status="queued",
        repro={
            "suite_hash": "sha256:acme",
            "target_id": target_model.id,
            "policy_id": policy_model.id,
            "case_id": case.id,
        },
        created_at=utc_now_iso(),
    )
    run_repo.create(run)

    # 4. Execute Run
    completed_run = execute_run(run_id, conn=conn)
    trace_steps = run_repo.get_trace(run_id)

    print("=" * 60)
    print(f"Run ID:      {completed_run.id}")
    print(f"Target:      {target_model.name} ({target_model.id})")
    print(f"Case:        {case.id} ({case.scenario_id})")
    print(f"Status:      {completed_run.status}")
    print(f"Utility:     {completed_run.utility}")
    print(f"Security:    {completed_run.security}")
    print(f"Step Count:  {len(trace_steps)}")
    if completed_run.error:
        print(f"Error:       {completed_run.error}")
    print("=" * 60)


def sleeper_cmd(target_name: str, case_id: str = "AS-05", policy_name: str | None = None) -> None:
    """Execute a multi-session sleeper evaluation run via CLI."""
    from agentbreak.config import get_settings
    from agentbreak.db import get_connection, migrate
    from agentbreak.engine.sleeper import execute_sleeper_run
    from agentbreak.repo.policy_repo import PolicyRepo
    from agentbreak.repo.target_repo import TargetRepo
    from agentbreak.schemas.sleeper import SleeperRunCreate
    from agentbreak.seed import seed_database

    settings = get_settings()
    conn = get_connection(settings.db_path)
    migrate(conn)
    seed_database(conn)

    target_repo = TargetRepo(conn)
    policy_repo = PolicyRepo(conn)

    target_model = target_repo.get(target_name)
    if not target_model:
        norm_name = target_name.replace("-", "_")
        for t in target_repo.list():
            if (
                t.id == target_name
                or t.id == f"tgt_{norm_name}"
                or norm_name in t.id
                or target_name.lower() in t.name.lower()
            ):
                target_model = t
                break
    if not target_model:
        print(f"Error: Target '{target_name}' could not be resolved.")
        sys.exit(1)

    pol_id = policy_name or "pol_full"
    policy_model = policy_repo.get(pol_id)
    if not policy_model:
        for p in policy_repo.list():
            if p.id == pol_id or pol_id in p.name.lower():
                policy_model = p
                break
    if not policy_model:
        print(f"Error: Policy '{pol_id}' could not be resolved.")
        sys.exit(1)

    sleeper_create = SleeperRunCreate(
        target_id=target_model.id,
        policy_id=policy_model.id,
        case_id=case_id,
        gap_sessions=1,
    )
    result = execute_sleeper_run(sleeper_create, conn=conn)

    print("=" * 60)
    print(f"Sleeper Run ID:  {result.id}")
    print(f"Target:          {target_model.name} ({target_model.id})")
    print(f"Status:          {result.status}")
    print(f"Outcome:         {result.outcome}")
    print(f"Sessions Count:  {len(result.sessions)}")
    print("=" * 60)


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

    run_parser = subparsers.add_parser("run", help="Execute an evaluation attack case")
    run_parser.add_argument(
        "--target",
        type=str,
        default="tgt_demo_scripted",
        help="Target ID or alias (default: tgt_demo_scripted)",
    )
    run_parser.add_argument(
        "--case",
        type=str,
        required=True,
        help="Attack case ID (e.g. AS-01..AS-07)",
    )
    run_parser.add_argument(
        "--policy",
        type=str,
        default="pol_full",
        help="Policy ID (default: pol_full)",
    )

    sleeper_parser = subparsers.add_parser("sleeper", help="Execute a sleeper agent evaluation")
    sleeper_parser.add_argument(
        "--target",
        type=str,
        default="tgt_demo_scripted",
        help="Target ID or alias (default: tgt_demo_scripted)",
    )
    sleeper_parser.add_argument(
        "--case",
        type=str,
        default="AS-05",
        help="Attack case ID (default: AS-05)",
    )
    sleeper_parser.add_argument(
        "--policy",
        type=str,
        default="pol_full",
        help="Policy ID (default: pol_full)",
    )

    args = parser.parse_args()

    if args.command == "export-openapi":
        export_openapi(args.output)
    elif args.command == "check-suite":
        check_suite(args.suite)
    elif args.command == "seed":
        seed_cmd()
    elif args.command == "run":
        run_cmd(target_name=args.target, case_id=args.case, policy_name=args.policy)
    elif args.command == "sleeper":
        sleeper_cmd(target_name=args.target, case_id=args.case, policy_name=args.policy)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
