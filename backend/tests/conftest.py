"""Global test configuration and fixtures."""

import pytest
from agentbreak.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a FastAPI TestClient."""
    app = create_app()
    return TestClient(app)
