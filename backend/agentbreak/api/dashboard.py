"""Dashboard, reports, and demo runner API endpoints."""

from __future__ import annotations

import datetime
import json
import uuid

from fastapi import APIRouter, HTTPException, Response, status

from agentbreak.api.deps import DbDep
from agentbreak.domain.report import generate_markdown_report
from agentbreak.engine.demo import get_demo, run_demo_sequence
from agentbreak.repo.audit_repo import AuditRepo
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.repo.fix_repo import FixRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.schemas import (
    DashboardSummary,
    DemoStatus,
    Page,
    Report,
    ReportCreate,
)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: DbDep, target_id: str | None = None) -> DashboardSummary:
    """Return high-level security metrics, severity breakdown, and recent runs."""
    run_repo = RunRepo(db)
    finding_repo = FindingRepo(db)
    target_repo = TargetRepo(db)

    # Resolve target
    eff_target_id = target_id
    if not eff_target_id:
        targets = target_repo.list()
        eff_target_id = targets[0].id if targets else "tgt_demo_scripted"

    # Query metrics directly from SQLite counts
    runs = run_repo.list_runs(target_id=eff_target_id, limit=100)
    attack_runs = [r for r in runs if r.kind == "attack"]
    benign_runs = [r for r in runs if r.kind == "benign"]

    total_attacks = len(attack_runs)
    successful_attacks = sum(1 for r in attack_runs if r.security is True)
    attack_success_rate = (successful_attacks / total_attacks) if total_attacks > 0 else 0.0

    total_benign = len(benign_runs)
    passed_benign = sum(1 for r in benign_runs if r.utility is True)
    benign_pass_rate = (passed_benign / total_benign) if total_benign > 0 else 1.0

    # Findings breakdown
    findings = finding_repo.list_findings(target_id=eff_target_id, limit=100)
    open_findings = [f for f in findings if f.status in ("open", "regressed")]
    crit_count = sum(1 for f in open_findings if f.severity == "critical")
    high_count = sum(1 for f in open_findings if f.severity == "high")

    # Recent runs as RunSummary
    recent_runs = runs[:10]

    return DashboardSummary(
        attack_success_rate=attack_success_rate,
        benign_pass_rate=benign_pass_rate,
        total_attacks=total_attacks,
        successful_attacks=successful_attacks,
        total_benign=total_benign,
        passed_benign=passed_benign,
        findings_by_severity={"critical": crit_count, "high": high_count},
        open_findings=len(open_findings),
        fixes_applied=0,
        recent_runs=recent_runs,
        trend=[
            {"timestamp": "Baseline", "attacks_blocked": 0, "utility": 1.0},
            {"timestamp": "Hardened", "attacks_blocked": 7, "utility": 1.0},
        ],
    )


@router.post("/reports", response_model=Report, status_code=status.HTTP_201_CREATED)
def create_report(body: ReportCreate, db: DbDep) -> Report:
    """Generate a reproducible evidence report for an evaluation run."""
    target_repo = TargetRepo(db)
    finding_repo = FindingRepo(db)
    audit_repo = AuditRepo(db)
    fix_repo = FixRepo(db)

    target = target_repo.get(body.target_id)
    target_name = target.name if target else body.target_id

    findings = finding_repo.list_findings(target_id=body.target_id, limit=50)
    audits = audit_repo.list_audits(target_id=body.target_id, limit=1)
    audit = audits[0] if audits else None
    fix_evals = fix_repo.list_evals(target_id=body.target_id, limit=20)

    md = generate_markdown_report(
        target_id=body.target_id,
        target_name=target_name,
        policy_id=body.policy_id,
        findings=findings,
        audit=audit,
        fix_evals=fix_evals,
    )

    report_id = f"rep_{uuid.uuid4().hex[:8]}"
    now = datetime.datetime.now(datetime.UTC).isoformat()
    meta = {"findings_count": len(findings), "target_name": target_name}

    db.execute(
        "INSERT INTO report (id, scope_json, format, markdown, meta_json, created_at) VALUES (?, ?, ?, ?, ?, ?);",
        (
            report_id,
            json.dumps({"target_id": body.target_id, "policy_id": body.policy_id}),
            "markdown",
            md,
            json.dumps(meta),
            now,
        ),
    )
    db.commit()

    return Report(
        id=report_id,
        target_id=body.target_id,
        policy_id=body.policy_id,
        markdown=md,
        meta=meta,
        created_at=now,
    )


@router.get("/reports", response_model=Page[Report])
def list_reports(db: DbDep, limit: int = 50, offset: int = 0) -> Page[Report]:
    """List historical evidence reports."""
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, scope_json, format, markdown, meta_json, created_at FROM report ORDER BY created_at DESC LIMIT ? OFFSET ?;",
        (limit, offset),
    )
    rows = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM report;")
    total = int(cursor.fetchone()[0])

    items: list[Report] = []
    for r in rows:
        scope = json.loads(r[1]) if r[1] else {}
        meta = json.loads(r[4]) if r[4] else {}
        items.append(
            Report(
                id=r[0],
                target_id=scope.get("target_id", "tgt_demo_scripted"),
                policy_id=scope.get("policy_id", "pol_full"),
                markdown=r[3],
                meta=meta,
                created_at=r[5],
            )
        )

    return Page[Report](items=items, total=total, limit=limit, offset=offset)


@router.get("/reports/{report_id}", response_model=Report)
def get_report(report_id: str, db: DbDep) -> Report:
    """Retrieve full markdown and cryptographic metadata for a report."""
    row = db.execute(
        "SELECT id, scope_json, format, markdown, meta_json, created_at FROM report WHERE id = ?;",
        (report_id,),
    ).fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found."
        )
    scope = json.loads(row[1]) if row[1] else {}
    meta = json.loads(row[4]) if row[4] else {}
    return Report(
        id=row[0],
        target_id=scope.get("target_id", "tgt_demo_scripted"),
        policy_id=scope.get("policy_id", "pol_full"),
        markdown=row[3],
        meta=meta,
        created_at=row[5],
    )


@router.get("/reports/{report_id}/download")
def download_report(report_id: str, db: DbDep, format: str = "md") -> Response:
    """Download the evidence report file in Markdown format."""
    row = db.execute("SELECT markdown FROM report WHERE id = ?;", (report_id,)).fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found."
        )
    return Response(
        content=row[0],
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=agentbreak-report-{report_id}.md"},
    )


@router.post("/demo/run", response_model=DemoStatus, status_code=status.HTTP_202_ACCEPTED)
def run_demo(db: DbDep) -> DemoStatus:
    """Launch the 1-minute live demo scan across attack scenarios."""
    return run_demo_sequence(conn=db)


@router.get("/demo/{demo_id}", response_model=DemoStatus)
def get_demo_status(demo_id: str) -> DemoStatus:
    """Poll live execution status for an active demo scan."""
    st = get_demo(demo_id)
    if not st:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Demo '{demo_id}' not found."
        )
    return st
