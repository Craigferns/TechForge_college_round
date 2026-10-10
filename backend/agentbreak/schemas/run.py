"""Run, trace, snapshot, evidence, and verdict schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RunCreate(BaseModel):
    target_id: str
    policy_id: str
    attack_case_ids: list[str] = Field(default_factory=list)
    benign_task_ids: list[str] = Field(default_factory=list)
    include_controls: bool = True
    trials: int = 1
    seed: int | None = None
    model_config = {"extra": "forbid"}


class Evidence(BaseModel):
    type: Literal["state_diff", "canary_seen", "call_match"]
    path: str
    before: Any
    after: Any
    detail: str
    model_config = {"extra": "forbid"}


class Verdict(BaseModel):
    success: bool
    classification: Literal["exploited", "blocked", "said_not_did", "invalid_run", "error"]
    impact_class: str | None = None
    severity: Literal["critical", "high", "medium", "low", "none"] | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    verifier_version: str
    verdict_hash: str
    created_at: str
    matches_stored: bool | None = None
    model_config = {"extra": "forbid"}


class RunSummary(BaseModel):
    id: str
    kind: Literal["attack", "benign", "control"]
    target_id: str
    policy_id: str
    suite: str
    case_id: str | None = None
    scenario_id: str | None = None
    user_task_id: str
    status: Literal["queued", "running", "done", "error", "cancelled"]
    utility: bool | None = None
    security: bool | None = None
    verdict_success: bool | None = None
    severity: str | None = None
    created_at: str
    finished_at: str | None = None
    model_config = {"extra": "forbid"}


class Run(BaseModel):
    id: str
    kind: Literal["attack", "benign", "control"]
    target_id: str
    policy_id: str
    suite: str
    case_id: str | None = None
    scenario_id: str | None = None
    user_task_id: str
    injection_task_id: str | None = None
    template_id: str | None = None
    payload_text: str | None = None
    payload_hash: str | None = None
    origin: Literal["static", "mutated", "llm"] | None = None
    status: Literal["queued", "running", "done", "error", "cancelled"]
    error: str | None = None
    utility: bool | None = None
    security: bool | None = None
    model_output: str | None = None
    verdict: Verdict | None = None
    repro: dict[str, Any]
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    model_config = {"extra": "forbid"}


class TraceStep(BaseModel):
    idx: int
    session_id: str | None = None
    role: str
    kind: Literal["system", "user", "assistant", "tool_call", "tool_result"]
    tool: str | None = None
    args: dict[str, Any] | None = None
    content: str | None = None
    flags: dict[str, bool] = Field(default_factory=dict)
    caused_by_idx: int | None = None
    model_config = {"extra": "forbid"}


class SnapshotPair(BaseModel):
    pre: dict[str, Any]
    post: dict[str, Any]
    diff: list[dict[str, Any]]
    model_config = {"extra": "forbid"}
