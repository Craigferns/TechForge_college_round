"""Autonomous discovery schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DiscoveryBudget(BaseModel):
    max_attempts: int = 40
    max_seconds: int = 300
    model_config = {"extra": "forbid"}


class DiscoveryCreate(BaseModel):
    target_id: str
    policy_id: str
    scenario_ids: list[str] = Field(default_factory=list)
    budget: DiscoveryBudget = Field(default_factory=DiscoveryBudget)
    seed: int = 42
    use_attacker_llm: bool = False
    model_config = {"extra": "forbid"}


class DiscoveryAttempt(BaseModel):
    n: int
    case_id: str
    fingerprint: str
    origin: Literal["static", "mutated", "llm"]
    mutation_chain: list[str] = Field(default_factory=list)
    run_id: str | None = None
    success: bool
    model_config = {"extra": "forbid"}


class DiscoveryCampaign(BaseModel):
    id: str
    target_id: str
    policy_id: str
    status: Literal["queued", "running", "done", "error"]
    attempts: int = 0
    successes: int = 0
    coverage: dict[str, Any] = Field(default_factory=dict)
    attempts_list: list[DiscoveryAttempt] = Field(default_factory=list)
    created_at: str
    finished_at: str | None = None
    model_config = {"extra": "forbid"}
