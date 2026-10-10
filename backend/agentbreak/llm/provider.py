"""LLM provider connectivity probing and capability detection."""

from __future__ import annotations

import time
from typing import Any

import httpx
from agentbreak.schemas.target import TargetTestResult


def probe_target(
    base_url: str,
    model: str,
    api_key: str | None = None,
    timeout_s: float = 5.0,
) -> TargetTestResult:
    """Probe an OpenAI-compatible endpoint for reachability and tool-calling capability.

    Enforces a strict timeout (< 5 s) and returns clear actionable notes.
    """
    clean_url = base_url.rstrip("/")
    headers: dict[str, str] = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    start_time = time.monotonic()

    # 1. Reachability probe: check /models endpoint or root
    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.get(f"{clean_url}/models", headers=headers)
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            if resp.status_code >= 500:
                return TargetTestResult(
                    reachable=False,
                    tool_calling=False,
                    latency_ms=elapsed_ms,
                    notes=f"Target returned server error: HTTP {resp.status_code}",
                )
    except httpx.TimeoutException:
        return TargetTestResult(
            reachable=False,
            tool_calling=False,
            latency_ms=int(timeout_s * 1000),
            notes=f"Connection timed out after {timeout_s:.1f}s connecting to {base_url}",
        )
    except Exception as exc:
        return TargetTestResult(
            reachable=False,
            tool_calling=False,
            latency_ms=0,
            notes=f"Failed to connect to {base_url}: {exc}",
        )

    # 2. Tool-calling capability probe: send 1-tool probe request
    probe_tool: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": "probe_tool",
            "description": "Probe function to verify structured tool calling support",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
        },
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "Call the probe_tool function with x='ping'. Do not answer with normal text.",
            }
        ],
        "tools": [probe_tool],
        "tool_choice": "auto",
        "temperature": 0.0,
    }

    try:
        with httpx.Client(timeout=timeout_s) as client:
            chat_start = time.monotonic()
            chat_resp = client.post(
                f"{clean_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            chat_latency = int((time.monotonic() - chat_start) * 1000)

            if chat_resp.status_code != 200:
                return TargetTestResult(
                    reachable=True,
                    tool_calling=False,
                    latency_ms=chat_latency,
                    notes=f"Endpoint reachable, but chat/completions failed: HTTP {chat_resp.status_code} ({chat_resp.text[:120]})",
                )

            data = chat_resp.json()
            choices = data.get("choices", [])
            if not choices:
                return TargetTestResult(
                    reachable=True,
                    tool_calling=False,
                    latency_ms=chat_latency,
                    notes="Endpoint returned empty choices array in chat response",
                )

            message = choices[0].get("message", {})
            tool_calls = message.get("tool_calls", [])

            if tool_calls and len(tool_calls) > 0:
                return TargetTestResult(
                    reachable=True,
                    tool_calling=True,
                    latency_ms=chat_latency,
                    notes=f"Target '{model}' is reachable and verified capable of structured tool calling.",
                )
            else:
                return TargetTestResult(
                    reachable=True,
                    tool_calling=False,
                    latency_ms=chat_latency,
                    notes=f"Target '{model}' responded with text but did NOT emit structured tool_calls. AgentBreak requires tool-calling models.",
                )

    except httpx.TimeoutException:
        return TargetTestResult(
            reachable=True,
            tool_calling=False,
            latency_ms=int(timeout_s * 1000),
            notes=f"Chat completions timed out after {timeout_s:.1f}s",
        )
    except Exception as exc:
        return TargetTestResult(
            reachable=True,
            tool_calling=False,
            latency_ms=0,
            notes=f"Chat completions error: {exc}",
        )


def query_chat_completion(
    base_url: str,
    model: str,
    prompt: str,
    api_key: str | None = None,
    temperature: float = 0.0,
    timeout_s: float = 15.0,
) -> str:
    """Send a basic prompt to an OpenAI-compatible /chat/completions endpoint."""
    clean_url = base_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(f"{clean_url}/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            return str(content) if content is not None else ""
    return ""
