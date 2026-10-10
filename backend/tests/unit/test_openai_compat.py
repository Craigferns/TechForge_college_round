"""Unit tests for OpenAICompatTarget adapter, HTTP transport, and probe_target."""

from __future__ import annotations

import time

import httpx
import pytest
from agentbreak.llm.provider import probe_target
from agentbreak.targets.openai_compat import OpenAICompatTarget


def test_openai_compat_resolves_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify api_key_env is resolved dynamically from environment without persisting secret."""
    monkeypatch.setenv("MY_SECRET_AGENT_KEY", "sk-agentbreak-secret-key-12345")

    target = OpenAICompatTarget(
        id="tgt_test_key",
        name="Test Target Key",
        config={
            "base_url": "http://localhost:11434/v1",
            "model": "llama3.1",
            "api_key_env": "MY_SECRET_AGENT_KEY",
        },
    )

    resolved = target.resolve_api_key()
    assert resolved == "sk-agentbreak-secret-key-12345"
    # Verify key is NOT stored directly in config
    assert "sk-agentbreak" not in str(target.config)


def test_probe_target_dead_url_fails_fast() -> None:
    """Verify dead/unreachable URL fails fast (< 5 s) with an informative note."""
    start = time.monotonic()
    result = probe_target(
        base_url="http://127.0.0.1:59999/v1",  # Unused port
        model="non-existent-model",
        timeout_s=1.0,
    )
    elapsed = time.monotonic() - start

    assert result.reachable is False
    assert result.tool_calling is False
    assert elapsed < 5.0
    assert "Failed to connect" in result.notes or "timed out" in result.notes


def test_probe_target_mocked_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify probe_target with mocked responses reports reachable and tool_calling."""

    def mock_get(url: str, *args, **kwargs) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "mock-model"}]})

    def mock_post(url: str, *args, **kwargs) -> httpx.Response:
        body = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "probe_tool", "arguments": '{"x":"ping"}'},
                            }
                        ],
                    }
                }
            ]
        }
        return httpx.Response(200, json=body)

    monkeypatch.setattr(httpx.Client, "get", mock_get)
    monkeypatch.setattr(httpx.Client, "post", mock_post)

    result = probe_target(
        base_url="http://mocked-provider.test/v1",
        model="mock-model",
        timeout_s=2.0,
    )

    assert result.reachable is True
    assert result.tool_calling is True
    assert "verified capable of structured tool calling" in result.notes


def test_probe_target_mocked_no_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify probe_target identifies models that output text but lack structured tool_calls."""

    def mock_get(url: str, *args, **kwargs) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "text-only-model"}]})

    def mock_post(url: str, *args, **kwargs) -> httpx.Response:
        body = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "I am a thinking model that doesn't output tool_calls.",
                        "tool_calls": [],
                    }
                }
            ]
        }
        return httpx.Response(200, json=body)

    monkeypatch.setattr(httpx.Client, "get", mock_get)
    monkeypatch.setattr(httpx.Client, "post", mock_post)

    result = probe_target(
        base_url="http://mocked-provider.test/v1",
        model="text-only-model",
        timeout_s=2.0,
    )

    assert result.reachable is True
    assert result.tool_calling is False
    assert "AgentBreak requires tool-calling models" in result.notes


@pytest.mark.ollama
def test_live_ollama_probe() -> None:
    """Optional live probe test against a running local Ollama instance."""
    result = probe_target(
        base_url="http://localhost:11434/v1",
        model="llama3.1",
        timeout_s=3.0,
    )
    # Just verify result object structure
    assert isinstance(result.reachable, bool)
    assert isinstance(result.tool_calling, bool)
