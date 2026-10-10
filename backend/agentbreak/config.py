"""Application configuration for AgentBreak."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime application settings loaded from environment."""

    db_path: Path = Field(
        default_factory=lambda: Path(os.getenv("AGENTBREAK_DB_PATH", "./data/agentbreak.db"))
    )
    host: str = Field(default_factory=lambda: os.getenv("AGENTBREAK_HOST", "127.0.0.1"))
    port: int = Field(default_factory=lambda: int(os.getenv("AGENTBREAK_PORT", "8000")))
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("AGENTBREAK_CORS_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ]
    )
    run_timeout_s: int = Field(
        default_factory=lambda: int(os.getenv("AGENTBREAK_RUN_TIMEOUT_S", "120"))
    )
    max_workers: int = Field(default_factory=lambda: int(os.getenv("AGENTBREAK_MAX_WORKERS", "2")))
    allow_remote_targets: bool = Field(
        default_factory=lambda: (
            os.getenv("AGENTBREAK_ALLOW_REMOTE_TARGETS", "0") in ("1", "true", "True")
        )
    )
    ollama_base_url: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    )
    target_model: str = Field(default_factory=lambda: os.getenv("TARGET_MODEL", ""))
    attacker_model: str = Field(default_factory=lambda: os.getenv("ATTACKER_MODEL", ""))

    model_config = {"extra": "forbid"}


def get_settings() -> Settings:
    """Return a cached or freshly instantiated Settings instance."""
    return Settings()
