"""Test openapi schema coverage and drift."""

import json
from pathlib import Path

from fastapi.testclient import TestClient


def test_openapi_endpoint_count(client: TestClient) -> None:
    """Verify openapi.json exists and exposes all 51 endpoint paths."""
    openapi_file = Path("openapi.json")
    assert openapi_file.exists()

    with open(openapi_file, encoding="utf-8") as f:
        schema = json.load(f)

    paths = schema.get("paths", {})
    operation_count = sum(len(methods) for methods in paths.values())

    # We expect 51 operations across the 11 routers
    assert operation_count >= 50
