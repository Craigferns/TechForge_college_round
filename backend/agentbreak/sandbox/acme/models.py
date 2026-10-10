"""Data models for the Acme Corporation sandbox environment."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Email(BaseModel):
    id: str
    sender: str
    recipients: list[str]
    subject: str
    body: str
    bcc: list[str] = Field(default_factory=list)
    model_config = {"extra": "forbid"}


class File(BaseModel):
    id: str
    name: str
    content: str
    shared_with: list[str] = Field(default_factory=list)
    model_config = {"extra": "forbid"}
