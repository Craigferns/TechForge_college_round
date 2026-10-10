"""Factory module for instantiating BaseTarget instances from Target schema models."""

from __future__ import annotations

from agentbreak.schemas.target import Target
from agentbreak.targets.base import BaseTarget
from agentbreak.targets.openai_compat import OpenAICompatTarget
from agentbreak.targets.scripted import ScriptedTarget


def create_target(target: Target) -> BaseTarget:
    """Instantiate the appropriate BaseTarget adapter for a target entity."""
    if target.kind == "scripted":
        return ScriptedTarget(
            id=target.id,
            name=target.name,
            config=target.config,
        )
    elif target.kind == "openai_compat":
        return OpenAICompatTarget(
            id=target.id,
            name=target.name,
            config=target.config,
        )
    else:
        raise ValueError(
            f"Unsupported target kind: '{target.kind}'. Supported: scripted, openai_compat"
        )
