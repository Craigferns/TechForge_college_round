"""AgentBreakAttack implementation conforming to AgentDojo's BaseAttack interface."""

from __future__ import annotations

from typing import Any

from agentdojo.agent_pipeline import BasePipelineElement
from agentdojo.attacks.base_attacks import BaseAttack
from agentdojo.task_suite import BaseInjectionTask, BaseUserTask, TaskSuite

from agentbreak.attacks.templates import DEFAULT_TEMPLATE_ID, render_payload


class AgentBreakAttack(BaseAttack):  # type: ignore[misc]
    """Attack generator registering prompt injection payloads into task suite carriers."""

    name = "agentbreak_attack"
    template_id: str

    def __init__(
        self,
        task_suite: TaskSuite[Any],
        target_pipeline: BasePipelineElement,
        template_id: str = DEFAULT_TEMPLATE_ID,
    ) -> None:
        super().__init__(task_suite, target_pipeline)
        self.template_id = template_id

    def attack(
        self,
        user_task: BaseUserTask[Any],
        injection_task: BaseInjectionTask[Any],
    ) -> dict[str, str]:
        """Generate vector dictionary containing the rendered payload for the user task carrier."""
        task_id = getattr(user_task, "BENIGN_ID", getattr(user_task, "ID", ""))
        inj_id = getattr(injection_task, "INJECTION_ID", getattr(injection_task, "ID", ""))
        goal = getattr(injection_task, "GOAL", "")

        payload, _ = render_payload(
            template_id=self.template_id,
            injection_task_id=inj_id,
            goal_text=goal,
        )

        vector_name = "inj_email_body"
        if task_id == "BT-08" or "doc" in task_id.lower():
            vector_name = "inj_doc_content"

        return {vector_name: payload}
