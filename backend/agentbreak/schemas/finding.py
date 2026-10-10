"""Finding and attack graph schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Finding(BaseModel):
    id: str
    fingerprint: str
    target_id: str
    scenario_id: str
    case_id: str
    title: str
    severity: Literal["critical", "high", "medium", "low"]
    impact_class: str
    status: Literal["open", "fixed", "regressed", "accepted_risk", "partially_mitigated"]
    success_rate: float = 1.0
    confidence: Literal["confirmed", "flaky"] = "confirmed"
    enabling_permissions: list[str] = Field(default_factory=list)
    first_run_id: str | None = None
    last_run_id: str | None = None
    occurrences: int = 1
    first_seen: str
    last_seen: str
    model_config = {"extra": "forbid"}


class FindingUpdate(BaseModel):
    status: Literal["open", "accepted_risk"]
    model_config = {"extra": "forbid"}


class GraphNode(BaseModel):
    id: str
    label: str
    type: Literal["vector", "tool", "impact", "finding"]
    severity: str | None = None
    count: int = 1
    model_config = {"extra": "forbid"}


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str | None = None
    model_config = {"extra": "forbid"}


class AttackGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    model_config = {"extra": "forbid"}
