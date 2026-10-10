"""Dashboard summaries, reports, and demo runner endpoints."""

from fastapi import APIRouter, HTTPException, Response, status

from agentbreak.schemas import DashboardSummary, DemoStatus, Page, Report, ReportCreate

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(target_id: str | None = None) -> DashboardSummary:
    """Return high-level security metrics, severity breakdown, and recent runs."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.post("/reports", response_model=Report, status_code=status.HTTP_201_CREATED)
def create_report(body: ReportCreate) -> Report:
    """Generate a reproducible evidence report for an evaluation run."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/reports", response_model=Page[Report])
def list_reports(limit: int = 50, offset: int = 0) -> Page[Report]:
    """List historical evidence reports."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/reports/{report_id}", response_model=Report)
def get_report(report_id: str) -> Report:
    """Retrieve full markdown and cryptographic metadata for a report."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/reports/{report_id}/download")
def download_report(report_id: str, format: str = "md") -> Response:
    """Download the evidence report file in Markdown format."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.post("/demo/run", response_model=DemoStatus, status_code=status.HTTP_202_ACCEPTED)
def run_demo() -> DemoStatus:
    """Launch the 1-minute live demo scan across attack scenarios."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/demo/{demo_id}", response_model=DemoStatus)
def get_demo_status(demo_id: str) -> DemoStatus:
    """Poll live execution status for an active demo scan."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")
