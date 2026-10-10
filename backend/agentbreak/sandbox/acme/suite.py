"""TaskSuite construction and suite validation for Acme Corporation."""

from __future__ import annotations

from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite import BaseUserTask, TaskSuite

from agentbreak.sandbox.acme.env import AcmeEnv
from agentbreak.sandbox.acme.tools import get_acme_tools
from agentbreak.sandbox.acme.user_tasks import ALL_BENIGN_TASKS


def create_acme_suite() -> TaskSuite[AcmeEnv]:
    """Assemble and configure the full Acme TaskSuite with tools and benign tasks."""
    tools = get_acme_tools()
    suite = TaskSuite[AcmeEnv](
        name="acme",
        environment_type=AcmeEnv,
        tools=tools,
    )
    for task_cls in ALL_BENIGN_TASKS:
        suite.register_user_task(task_cls)

    return suite


def compute_needed_permissions() -> frozenset[str]:
    """Compute the union of tool names executed by ground truths of all benign tasks.

    This forms the mathematical definition of 'Needed Permissions' (8 tools).
    """
    needed: set[str] = set()
    env = AcmeEnv.create_default()

    for task_cls in ALL_BENIGN_TASKS:
        task = task_cls()
        init_env = task.init_environment(env.clone())
        calls = task.ground_truth(init_env)
        for call in calls:
            needed.add(call.function)

    return frozenset(needed)


def evaluate_task_ground_truth(task_cls: type[BaseUserTask[AcmeEnv]]) -> tuple[bool, str]:
    """Execute a benign task's ground-truth calls directly in an isolated AcmeEnv.

    Returns (utility_passed, message).
    """
    task = task_cls()
    runtime = FunctionsRuntime(get_acme_tools())

    pre_env = AcmeEnv.create_default()
    pre_env = task.init_environment(pre_env)
    post_env = pre_env.clone()

    calls = task.ground_truth(pre_env)
    for call in calls:
        res, err = runtime.run_function(post_env, call.function, call.args)
        if err:
            return False, f"Error in call {call.function}: {err}"

    passed = task.utility(
        model_output=task.GROUND_TRUTH_OUTPUT,
        pre_environment=pre_env,
        post_environment=post_env,
        strict=True,
    )
    return passed, f"Task {task.ID} ground truth executed ({len(calls)} calls)."
