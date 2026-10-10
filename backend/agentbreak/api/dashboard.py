"""Dashboard summaries, reports, and demo runner endpoints."""

from __future__ import annotations

import datetime
import uuid

from fastapi import APIRouter, HTTPException, Response, status

from agentbreak.api.deps import DbDep
from agentbreak.domain.report import generate_markdown_report
from agentbreak.engine.demo import DEMO_RUNS_CACHE, start_demo
from agentbreak.engine.posture import compute_posture
from agentbreak.repo.report_repo import ReportRepo
from agentbreak.schemas import DashboardSummary, DemoStatus, Page, Report, ReportCreate

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: DbDep, target_id: str | None = None) -> DashboardSummary:
    """Current posture under the target's active policy (see DashboardSummary docstring)."""
    return compute_posture(db, target_id or "tgt_demo_scripted")


@router.post("/reports", response_model=Report, status_code=status.HTTP_201_CREATED)
def create_report(body: ReportCreate, db: DbDep) -> Report:
    """Generate a reproducible evidence report for an evaluation run."""
    report_id = f"rep_{uuid.uuid4().hex[:8]}"
    created_at = datetime.datetime.now(datetime.UTC).isoformat()
    rep = generate_markdown_report(
        report_id=report_id,
        target_id=body.target_id,
        policy_id=body.policy_id,
        conn=db,
        created_at=created_at,
    )
    repo = ReportRepo(db)
    return repo.create(rep)


@router.get("/reports", response_model=Page[Report])
def list_reports(db: DbDep, limit: int = 50, offset: int = 0) -> Page[Report]:
    """List historical evidence reports."""
    repo = ReportRepo(db)
    items, total = repo.list(limit=limit, offset=offset)
    return Page[Report](items=items, total=total, limit=limit, offset=offset)


@router.get("/reports/{report_id}", response_model=Report)
def get_report(report_id: str, db: DbDep) -> Report:
    """Retrieve full markdown and cryptographic metadata for a report."""
    repo = ReportRepo(db)
    rep = repo.get(report_id)
    if not rep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found.",
        )
    return rep


@router.get("/reports/{report_id}/download")
def download_report(report_id: str, db: DbDep, format: str = "md") -> Response:
    """Download the evidence report file in Markdown format."""
    repo = ReportRepo(db)
    rep = repo.get(report_id)
    if not rep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found.",
        )
    return Response(
        content=rep.markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=agentbreak-report-{report_id}.md"},
    )


@router.post("/demo/run", response_model=DemoStatus, status_code=status.HTTP_202_ACCEPTED)
def run_demo() -> DemoStatus:
    """Start the demo in the background; poll GET /demo/{id} for real stage progress."""
    return start_demo()


@router.get("/demo/{demo_id}", response_model=DemoStatus)
def get_demo_status(demo_id: str) -> DemoStatus:
    """Poll live execution status for an active demo scan."""
    if demo_id in DEMO_RUNS_CACHE:
        return DEMO_RUNS_CACHE[demo_id]
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Demo run '{demo_id}' not found.",
    )
