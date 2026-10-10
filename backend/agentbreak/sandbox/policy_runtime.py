"""Runtime sandbox policy enforcement and tool interposition."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from agentdojo.functions_runtime import Function, FunctionsRuntime

from agentbreak.schemas.policy import Grant, Policy


class PermissionDenied(Exception):
    """Raised when an agent tool invocation violates the active security policy."""

    def __init__(
        self,
        reason: str,
        tool: str,
        arg: str | None = None,
        value: Any | None = None,
    ) -> None:
        self.reason = reason
        self.tool = tool
        self.arg = arg
        self.value = value
        msg = f"PermissionDenied: {reason} for tool '{tool}'"
        if arg:
            msg += f" on argument '{arg}' (value: {value})"
        super().__init__(msg)


class PolicyRuntime(FunctionsRuntime):
    """Evaluates and enforces active policy grants and argument constraints at runtime."""

    grants_by_tool: dict[str, Grant]
    all_tools: dict[str, Function]

    def __init__(
        self,
        policy: Policy | Sequence[Grant],
        tools: Sequence[Function] | None = None,
    ) -> None:
        if isinstance(policy, Policy):
            self.grants_by_tool = {g.tool: g for g in policy.grants}
        else:
            self.grants_by_tool = {g.tool: g for g in policy}

        if tools is None:
            try:
                from agentbreak.sandbox.acme.tools import get_acme_tools

                tool_list = list(get_acme_tools())
            except Exception:
                tool_list = []
        else:
            tool_list = list(tools)

        self.all_tools = {f.name: f for f in tool_list}
        granted_tools = [f for f in tool_list if f.name in self.grants_by_tool]
        super().__init__(granted_tools)

    def has_function(self, function: str) -> bool:
        """Check if tool is registered and permitted under current policy."""
        return function in self.functions and self.is_granted(function)

    def is_granted(self, tool_name: str) -> bool:
        """Check if a tool is granted under the active policy."""
        return tool_name in self.grants_by_tool

    def check_allowed(
        self, tool_name: str, args: dict[str, Any] | None = None
    ) -> tuple[bool, str | None, str | None, Any | None]:
        """Verify whether an invocation is allowed under policy grants and constraints.

        Returns (allowed, reason, offending_arg, offending_value).
        """
        if tool_name not in self.grants_by_tool:
            return False, "not_granted", None, None

        grant = self.grants_by_tool[tool_name]
        if not grant.constraints or not args:
            return True, None, None, None

        for constraint in grant.constraints:
            if constraint.kind == "domain_allowlist":
                arg_name = constraint.arg
                if arg_name in args:
                    val = args[arg_name]
                    emails: list[str] = []
                    if isinstance(val, str):
                        emails = [val]
                    elif isinstance(val, (list, tuple, set)):
                        emails = [str(item) for item in val]

                    allowed_domains = set(constraint.values)
                    for email in emails:
                        if "@" in email:
                            domain = email.split("@")[-1].strip().lower()
                            if domain not in allowed_domains:
                                return False, "domain_not_allowed", arg_name, email

        return True, None, None, None

    def enforce(self, tool_name: str, args: dict[str, Any] | None = None) -> None:
        """Enforce policy. Raises PermissionDenied if tool or args are unauthorized."""
        allowed, reason, arg, val = self.check_allowed(tool_name, args)
        if not allowed:
            raise PermissionDenied(
                reason=reason or "not_granted",
                tool=tool_name,
                arg=arg,
                value=val,
            )

    def run_function(
        self,
        env: Any,
        function: str,
        kwargs: Mapping[str, Any],
        raise_on_error: bool = False,
    ) -> tuple[Any, str | None]:
        """Run function with pre-execution policy check."""
        # 1. Enforce policy grant
        if not self.is_granted(function):
            err_msg = f"PermissionDenied: not_granted for tool '{function}'"
            if raise_on_error:
                raise PermissionDenied(reason="not_granted", tool=function)
            return "", err_msg

        # 2. Enforce argument constraints
        allowed, reason, arg, val = self.check_allowed(function, dict(kwargs))
        if not allowed:
            err_msg = f"PermissionDenied: {reason} for tool '{function}' on argument '{arg}' (value: {val})"
            if raise_on_error:
                raise PermissionDenied(
                    reason=reason or "constraint_violated",
                    tool=function,
                    arg=arg,
                    value=val,
                )
            return "", err_msg

        # 3. Check function availability in functions dictionary
        if function not in self.functions:
            err_msg = f"ToolNotFoundError: The requested function `{function}` is not available."
            if raise_on_error:
                from agentdojo.functions_runtime import ToolNotFoundError

                raise ToolNotFoundError(err_msg)
            return "", err_msg

        # 4. Delegate to underlying FunctionsRuntime execution
        return super().run_function(env, function, kwargs, raise_on_error=raise_on_error)  # type: ignore[no-any-return]

    def wrap_tool(
        self, func: Callable[..., Any], tool_name: str | None = None
    ) -> Callable[..., Any]:
        """Wrap a tool function with policy enforcement.

        Ensures the underlying tool body is NEVER executed if the call is denied.
        """
        name = tool_name or func.__name__
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Bind args to inspect kwargs passed by caller
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            # Enforce policy before calling func
            self.enforce(name, bound.arguments)
            return func(*args, **kwargs)

        return wrapper
