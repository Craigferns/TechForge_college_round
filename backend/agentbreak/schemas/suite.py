"""Sandbox suite, tasks, vectors, and attack case schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolInfo(BaseModel):
    name: str
    description: str
    signature: str
    effect_class: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    model_config = {"extra": "forbid"}


class TaskInfo(BaseModel):
    id: str
    name: str
    prompt: str
    ground_truth_tools: list[str]
    carrier_vector: str | None = None
    model_config = {"extra": "forbid"}


class SuiteInfo(BaseModel):
    name: str
    persona: str
    tools: list[ToolInfo]
    benign_tasks: list[TaskInfo]
    injection_tasks: list[TaskInfo]
    vectors: list[str]
    model_config = {"extra": "forbid"}


class ScenarioSpec(BaseModel):
    id: str
    name: str
    description: str
    vector: str
    predicate: str
    severity: str
    impact_class: str
    model_config = {"extra": "forbid"}


class AttackCase(BaseModel):
    id: str
    scenario_id: str
    carrier_task_id: str
    injection_task_id: str
    description: str
    model_config = {"extra": "forbid"}
