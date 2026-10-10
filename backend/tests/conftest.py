"""Global test configuration and fixtures."""

import socket
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from agentbreak.main import create_app
from fastapi.testclient import TestClient

_real_connect = socket.socket.connect


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test gets its own SQLite file; tests never touch ./data/agentbreak.db."""
    monkeypatch.setenv("AGENTBREAK_DB_PATH", str(tmp_path / "agentbreak-test.db"))


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Socket guard (CLAUDE.md §5): only loopback connections are allowed in tests."""

    def guarded(self: socket.socket, address: Any) -> None:
        host = address[0] if isinstance(address, tuple) else address
        if host not in ("127.0.0.1", "::1", "localhost"):
            raise RuntimeError(f"Network access blocked in tests: {address!r}")
        _real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)


@pytest.fixture
def client() -> Iterator[TestClient]:
    """FastAPI TestClient bound to the per-test database (lifespan runs migrations)."""
    with TestClient(create_app()) as c:
        yield c
