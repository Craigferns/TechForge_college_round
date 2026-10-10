"""Fix proposals and evaluation schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FixSpec(BaseModel):
    kind: Literal["remove_permission", "restrict_arg", "defense", "prompt_hardening"]
    tool: str | None = None
    args: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    defense_name: str | None = None
    prompt_id: str | None = None
    model_config = {"extra": "forbid"}


class FixSuggestion(BaseModel):
    id: str
    fix: FixSpec
    title: str
    description: str
    targeted_exploits: list[str] = Field(default_factory=list)
    model_config = {"extra": "forbid"}


class PriceTag(BaseModel):
    attacks_blocked: int
    attacks_total: int
    tasks_broken: int
    benign_total: int
    pareto: bool = False
    model_config = {"extra": "forbid"}


class FixEvalCreate(BaseModel):
    target_id: str
    base_policy_id: str
    fix: FixSpec
    trials: int = 1
    model_config = {"extra": "forbid"}


class FixEvalDetails(BaseModel):
    blocked_cases: list[str] = Field(default_factory=list)
    still_exploitable: list[str] = Field(default_factory=list)
    broken_tasks: list[str] = Field(default_factory=list)
    # Runs that errored under the fixed policy: never counted as blocked or broken.
    inconclusive: list[str] = Field(default_factory=list)
    # AS-05 end-to-end outcome under the fixed policy (plant_failed | trigger_blocked | triggered).
    sleeper_outcome: str | None = None
    # Evidence: every run executed under the fixed policy for this evaluation.
    run_ids: list[str] = Field(default_factory=list)
    # Before/after evidence per attack case and benign task (AS-05: the sleeper trigger session).
    before_runs: dict[str, str] = Field(default_factory=dict)
    after_runs: dict[str, str] = Field(default_factory=dict)
    model_config = {"extra": "forbid"}


class FixEval(BaseModel):
    id: str
    audit_id: str | None = None
    target_id: str
    base_policy_id: str
    fix: FixSpec
    result_policy_id: str | None = None
    trials: int = 1
    status: Literal["queued", "running", "done", "error"]
    price_tag: PriceTag | None = None
    details: FixEvalDetails | None = None
    retest_of: str | None = None
    created_at: str
    finished_at: str | None = None
    model_config = {"extra": "forbid"}
