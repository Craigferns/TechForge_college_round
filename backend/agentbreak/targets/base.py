"""Abstract Target interface defining the pipeline contract for AgentBreak agents."""

from __future__ import annotations

import abc
from collections.abc import Sequence
from typing import Any

from agentdojo.agent_pipeline import BasePipelineElement
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.types import ChatMessage


class BaseTarget(abc.ABC):
    """Abstract interface representing an evaluation target (scripted or real LLM)."""

    id: str
    name: str
    kind: str
    config: dict[str, Any]

    def __init__(
        self,
        id: str,
        name: str,
        kind: str,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.kind = kind
        self.config = config or {}

    @abc.abstractmethod
    def build_pipeline(
        self,
        runtime: FunctionsRuntime,
        env: Any,
    ) -> BasePipelineElement:
        """Construct the AgentDojo pipeline element for this target."""
        ...

    def query(
        self,
        prompt: str,
        runtime: FunctionsRuntime,
        env: Any,
        messages: Sequence[ChatMessage] | None = None,
        extra_args: dict[str, Any] | None = None,
    ) -> tuple[str, FunctionsRuntime, Any, Sequence[ChatMessage], dict[str, Any]]:
        """Convenience method executing the constructed pipeline element on the prompt."""
        pipeline = self.build_pipeline(runtime, env)
        return pipeline.query(  # type: ignore[no-any-return]
            prompt,
            runtime,
            env,
            messages or [],
            extra_args or {},
        )
