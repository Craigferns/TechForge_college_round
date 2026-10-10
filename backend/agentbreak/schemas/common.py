"""Common pagination, error, and system schemas."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    model_config = {"extra": "forbid"}


class ErrorEnvelope(BaseModel):
    error: ErrorDetail
    model_config = {"extra": "forbid"}


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
    model_config = {"extra": "forbid"}


class Health(BaseModel):
    status: str
    version: str
    agentdojo_version: str
    db_ok: bool
    model_config = {"extra": "forbid"}


class Meta(BaseModel):
    suites: list[str]
    scenarios: list[str]
    fix_kinds: list[str]
    defenses: list[str]
    verifier_version: str
    limits: dict[str, int]
    model_config = {"extra": "forbid"}
