"""Dashboard summary, report, and demo status schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from agentbreak.schemas.run import RunSummary


class DashboardSummary(BaseModel):
    """Current posture of one target: the latest completed result per attack case and
    benign task under the target's ACTIVE policy (AS-05 from its latest sleeper chain).
    Runs under other policies (baselines, counterfactuals, fix measurements) are excluded."""

    active_policy_id: str | None = None
    sleeper_outcome: str | None = None
    inconclusive: int = 0  # latest runs that errored: neither exploited nor resisted
    attack_success_rate: float
    benign_pass_rate: float
    total_attacks: int
    successful_attacks: int
    total_benign: int
    passed_benign: int
    findings_by_severity: dict[str, int]
    open_findings: int
    fixes_applied: int  # grants removed/constrained vs the policy of the target's first run
    recent_runs: list[RunSummary]
    trend: list[dict[str, Any]] = Field(default_factory=list)
    model_config = {"extra": "forbid"}


class ReportCreate(BaseModel):
    target_id: str
    policy_id: str
    finding_ids: list[str] = Field(default_factory=list)
    format: Literal["markdown"] = "markdown"
    model_config = {"extra": "forbid"}


class Report(BaseModel):
    id: str
    target_id: str
    policy_id: str
    markdown: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    model_config = {"extra": "forbid"}


class DemoStage(BaseModel):
    id: str
    name: str
    status: Literal["pending", "running", "completed", "error"]
    detail: str | None = None
    model_config = {"extra": "forbid"}


class DemoLinks(BaseModel):
    dashboard: str = "/dashboard"
    run: str = "/runs/run_demo_as04"
    audit: str = "/permissions"
    fixlab: str = "/fixes"
    sleeper: str = "/sleeper"
    report: str = "/report"
    model_config = {"extra": "forbid"}


class DemoStatus(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "error"]
    stage: str
    stages: list[DemoStage]
    links: DemoLinks = Field(default_factory=DemoLinks)
    error: str | None = None
    model_config = {"extra": "forbid"}
