"""Target agents module."""

from agentbreak.targets.base import BaseTarget
from agentbreak.targets.factory import create_target
from agentbreak.targets.openai_compat import OpenAICompatTarget
from agentbreak.targets.scripted import AgentProfile, ScriptedAgent, ScriptedTarget

__all__ = [
    "BaseTarget",
    "ScriptedTarget",
    "ScriptedAgent",
    "AgentProfile",
    "OpenAICompatTarget",
    "create_target",
]
