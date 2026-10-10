"""Permission audit and attribution schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CounterfactualResult(BaseModel):
    blocked: bool
    benign_broken: int
    model_config = {"extra": "forbid"}


class EnabledExploit(BaseModel):
    case_id: str
    finding_id: str | None = None
    role: Literal["enabling", "observed"]
    counterfactual: CounterfactualResult | None = None
    model_config = {"extra": "forbid"}


class SuggestedScope(BaseModel):
    args: list[str]
    domain_allowlist: list[str]
    model_config = {"extra": "forbid"}


class PermissionRow(BaseModel):
    tool: str
    status: Literal["needed", "excess"]
    used_by_benign: list[str]
    enabled_exploits: list[EnabledExploit] = Field(default_factory=list)
    suggested_scope: SuggestedScope | None = None
    model_config = {"extra": "forbid"}


class AuditProof(BaseModel):
    benign_total: int
    benign_pass_under_minimal: int
    run_ids: list[str] = Field(default_factory=list)
    model_config = {"extra": "forbid"}


class AuditCreate(BaseModel):
    target_id: str
    policy_id: str
    verify_counterfactual: bool = True
    model_config = {"extra": "forbid"}


class PermissionAudit(BaseModel):
    id: str
    target_id: str
    policy_id: str
    status: Literal["queued", "running", "done", "error"]
    stage: str | None = None
    granted: list[str] = Field(default_factory=list)
    needed: list[str] = Field(default_factory=list)
    excess: list[str] = Field(default_factory=list)
    rows: list[PermissionRow] = Field(default_factory=list)
    minimal_policy_id: str | None = None
    proof: AuditProof | None = None
    created_at: str
    finished_at: str | None = None
    model_config = {"extra": "forbid"}
