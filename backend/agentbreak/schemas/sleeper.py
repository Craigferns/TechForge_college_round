"""Cross-session sleeper attack schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SleeperRunCreate(BaseModel):
    target_id: str
    policy_id: str
    case_id: str = "AS-05"
    gap_sessions: int = 1
    seed: int | None = None
    model_config = {"extra": "forbid"}


class SleeperSession(BaseModel):
    idx: int
    role: Literal["plant", "gap", "trigger"]
    run_id: str | None = None
    memory_before: dict[str, str] = Field(default_factory=dict)
    memory_after: dict[str, str] = Field(default_factory=dict)
    model_config = {"extra": "forbid"}


class SleeperRun(BaseModel):
    id: str
    target_id: str
    policy_id: str
    case_id: str
    gap_sessions: int
    status: Literal["queued", "running", "done", "error"]
    outcome: Literal["plant_failed", "trigger_blocked", "triggered"] | None = None
    sessions: list[SleeperSession] = Field(default_factory=list)
    created_at: str
    finished_at: str | None = None
    model_config = {"extra": "forbid"}
