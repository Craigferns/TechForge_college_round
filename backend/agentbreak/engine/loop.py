"""Pure execution loop for running an agent task once in an isolated sandbox environment."""

from __future__ import annotations

from dataclasses import dataclass

from agentdojo.task_suite import BaseInjectionTask, BaseUserTask
from agentdojo.types import ChatMessage

from agentbreak.sandbox.acme.env import AcmeEnv
from agentbreak.sandbox.policy_runtime import PolicyRuntime
from agentbreak.schemas.policy import Policy
from agentbreak.targets.base import BaseTarget


@dataclass(frozen=True)
class RunOutcome:
    """Deterministic result of executing one agent query in a sandbox environment."""

    pre: AcmeEnv
    post: AcmeEnv
    messages: list[ChatMessage]
    model_output: str
    utility: bool | None
    security: bool | None


def run_once(
    target: BaseTarget,
    policy: Policy,
    user_task: BaseUserTask[AcmeEnv],
    injection_task: BaseInjectionTask[AcmeEnv] | None = None,
    injections: dict[str, str] | None = None,
    memory_in: dict[str, str] | None = None,
) -> RunOutcome:
    """Execute a single run of an agent on a user task under policy enforcement.

    This is a pure function: it performs no disk I/O or database queries.
    """
    # 1. Initialize environment with optional planted injection vectors
    env = AcmeEnv.create_default(**(injections or {}))
    if memory_in is not None:
        env.memory = dict(memory_in)

    # Allow user task to initialize custom memory/state if defined
    if hasattr(user_task, "init_environment"):
        env = user_task.init_environment(env)

    # 2. Snapshot PRE state
    pre = env.clone()

    # 3. Create PolicyRuntime interposition wrapper
    runtime = PolicyRuntime(policy)

    # 4. Execute agent query
    pipeline = target.build_pipeline(runtime, env)
    final_text, _, env, messages, _ = pipeline.query(user_task.PROMPT, runtime, env)

    # 5. Snapshot POST state
    post = env
    model_output = final_text

    # 6. Evaluate pure utility and security predicates
    utility = user_task.utility(
        model_output=model_output,
        pre_environment=pre,
        post_environment=post,
        strict=True,
    )

    security = (
        injection_task.security(
            model_output=model_output,
            pre_environment=pre,
            post_environment=post,
        )
        if injection_task is not None
        else None
    )

    return RunOutcome(
        pre=pre,
        post=post,
        messages=messages,
        model_output=model_output,
        utility=utility,
        security=security,
    )
