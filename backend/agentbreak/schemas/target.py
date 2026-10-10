"""Target agent schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TargetCreate(BaseModel):
    name: str
    kind: Literal["scripted", "openai_compat"]
    config: dict[str, Any] = Field(default_factory=dict)
    model_config = {"extra": "forbid"}


class Target(BaseModel):
    id: str
    name: str
    kind: Literal["scripted", "openai_compat"]
    config: dict[str, Any]
    active_policy_id: str | None = None
    created_at: str
    model_config = {"extra": "forbid"}


class TargetTestResult(BaseModel):
    reachable: bool
    tool_calling: bool
    latency_ms: int
    notes: str
    model_config = {"extra": "forbid"}
