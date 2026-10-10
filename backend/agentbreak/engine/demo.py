"""Demo orchestrator executing the full AgentBreak live evaluation sequence in <= 60 seconds (SM-1)."""

from __future__ import annotations

import datetime
import sqlite3
import uuid

from agentbreak.attacks.scenarios import ATTACK_CASES
from agentbreak.domain.report import generate_markdown_report
from agentbreak.engine.audit import run_permission_audit
from agentbreak.engine.fixes import evaluate_all_suggestions
from agentbreak.engine.runner import execute_run
from agentbreak.engine.sleeper import execute_sleeper_run
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.schemas.audit import AuditCreate
from agentbreak.schemas.dashboard import DemoLinks, DemoStage, DemoStatus
from agentbreak.schemas.run import Run
from agentbreak.schemas.sleeper import SleeperRunCreate
from agentbreak.seed import seed_database

# In-memory registry of active/completed demo runs
_DEMO_RUNS: dict[str, DemoStatus] = {}


def run_demo_sequence(conn: sqlite3.Connection) -> DemoStatus:
    """Execute the full demo pipeline: seed -> attacks -> benign -> audit -> fixes -> sleeper -> report."""
    demo_id = f"demo_{uuid.uuid4().hex[:8]}"

    stages = [
        DemoStage(
            id="seed",
            name="Environment Seeding",
            status="running",
            detail="Seeding sandbox targets and policies",
        ),
        DemoStage(
            id="attacks",
            name="Security Test Engine",
            status="pending",
            detail="Executing 7 benchmark attack cases",
        ),
        DemoStage(
            id="benign",
            name="Benign Utility Verification",
            status="pending",
            detail="Running 10 user tasks for baseline utility",
        ),
        DemoStage(
            id="audit",
            name="Permission Diff & Attribution",
            status="pending",
            detail="Attributing exploits to excess tools",
        ),
        DemoStage(
            id="fixes",
            name="Fix Lab & Price Tags",
            status="pending",
            detail="Measuring blocked vs broken trade-offs",
        ),
        DemoStage(
            id="sleeper",
            name="Sleeper Mode Evaluation",
            status="pending",
            detail="Testing cross-session memory poisoning",
        ),
        DemoStage(
            id="report",
            name="Evidence Report Export",
            status="pending",
            detail="Generating Markdown evidence document",
        ),
    ]

    status = DemoStatus(
        id=demo_id,
        status="running",
        stage="Environment Seeding",
        stages=stages,
        links=DemoLinks(),
    )
    _DEMO_RUNS[demo_id] = status

    # 1. Seed
    seed_database(conn)
    stages[0].status = "completed"
    stages[1].status = "running"
    status.stage = "Security Test Engine"

    # 2. Run all 7 attack cases on scripted Alex target
    run_repo = RunRepo(conn)
    target_id = "tgt_demo_scripted"
    policy_id = "pol_full"

    for case in ATTACK_CASES:
        r_id = f"run_demo_{case.id.lower()}"
        existing = run_repo.get(r_id)
        if not existing:
            r = Run(
                id=r_id,
                kind="attack",
                target_id=target_id,
                policy_id=policy_id,
                suite="acme",
                case_id=case.id,
                scenario_id=case.scenario_id,
                user_task_id=case.carrier_task_id,
                injection_task_id=case.injection_task_id,
                template_id="tpl_authority_note",
                origin="static",
                status="queued",
                repro={"case_id": case.id},
                created_at=datetime.datetime.now(datetime.UTC).isoformat(),
            )
            run_repo.create(r)
            execute_run(r_id, conn=conn)

    stages[1].status = "completed"
    stages[2].status = "running"
    status.stage = "Benign Utility Verification"

    # 3. Benign baseline run (BT-01...10)
    for i in range(1, 11):
        bt_id = f"BT-{i:02d}"
        r_id = f"run_demo_benign_{i}"
        if not run_repo.get(r_id):
            r = Run(
                id=r_id,
                kind="benign",
                target_id=target_id,
                policy_id=policy_id,
                suite="acme",
                user_task_id=bt_id,
                status="queued",
                repro={"user_task_id": bt_id},
                created_at=datetime.datetime.now(datetime.UTC).isoformat(),
            )
            run_repo.create(r)
            execute_run(r_id, conn=conn)

    stages[2].status = "completed"
    stages[3].status = "running"
    status.stage = "Permission Diff & Attribution"

    # 4. Permission Audit (D1)
    audit = run_permission_audit(
        AuditCreate(target_id=target_id, policy_id=policy_id, verify_counterfactual=True),
        conn=conn,
    )

    stages[3].status = "completed"
    stages[4].status = "running"
    status.stage = "Fix Lab & Price Tags"

    # 5. Fix Lab (D2)
    fix_evals = evaluate_all_suggestions(audit.id, conn=conn)

    stages[4].status = "completed"
    stages[5].status = "running"
    status.stage = "Sleeper Mode Evaluation"

    # 6. Sleeper Mode (D3)
    execute_sleeper_run(
        SleeperRunCreate(target_id=target_id, policy_id=policy_id, case_id="AS-05"),
        conn=conn,
    )

    stages[5].status = "completed"
    stages[6].status = "running"
    status.stage = "Evidence Report Export"

    # 7. Evidence Report Generation
    finding_repo = FindingRepo(conn)
    findings = finding_repo.list_findings(target_id=target_id, limit=50)

    md = generate_markdown_report(
        target_id=target_id,
        target_name="Simulated Target (Scripted)",
        policy_id=policy_id,
        findings=findings,
        audit=audit,
        fix_evals=fix_evals,
    )

    # Save report to SQLite
    now = datetime.datetime.now(datetime.UTC).isoformat()
    rep_id = f"rep_{uuid.uuid4().hex[:8]}"
    conn.execute(
        "INSERT INTO report (id, scope_json, format, markdown, meta_json, created_at) VALUES (?, ?, ?, ?, ?, ?);",
        (
            rep_id,
            f'{{"target_id":"{target_id}"}}',
            "markdown",
            md,
            f'{{"findings_count":{len(findings)}}}',
            now,
        ),
    )
    conn.commit()

    stages[6].status = "completed"
    status.status = "completed"
    status.stage = "Completed"

    return status


def get_demo(demo_id: str) -> DemoStatus | None:
    """Retrieve active or completed demo status."""
    return _DEMO_RUNS.get(demo_id)
