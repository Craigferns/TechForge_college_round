"""Policy and grant schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ArgConstraint(BaseModel):
    arg: str
    kind: str = "domain_allowlist"
    values: list[str]
    model_config = {"extra": "forbid"}


Constraint = ArgConstraint


class Grant(BaseModel):
    tool: str
    constraints: list[ArgConstraint] = Field(default_factory=list)
    model_config = {"extra": "forbid"}


class PolicyCreate(BaseModel):
    name: str
    parent_id: str | None = None
    grants: list[Grant]
    model_config = {"extra": "forbid"}


class Policy(BaseModel):
    id: str
    name: str
    parent_id: str | None = None
    grants: list[Grant]
    hash: str
    created_at: str
    model_config = {"extra": "forbid"}


class PolicyDiff(BaseModel):
    policy_a: str
    policy_b: str
    added_tools: list[str]
    removed_tools: list[str]
    constraint_changes: list[dict[str, str]]
    model_config = {"extra": "forbid"}
