"""Runtime sandbox policy enforcement and tool interposition."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Sequence
from typing import Any

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


class PolicyRuntime:
    """Evaluates and enforces active policy grants and argument constraints at runtime."""

    def __init__(self, policy: Policy | Sequence[Grant]) -> None:
        if isinstance(policy, Policy):
            self.grants_by_tool = {g.tool: g for g in policy.grants}
        else:
            self.grants_by_tool = {g.tool: g for g in policy}

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
