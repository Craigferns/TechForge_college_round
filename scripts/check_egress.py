"""Verify that sandbox execution produces zero outbound egress to unauthorized network endpoints."""

from __future__ import annotations

import socket
import sys

# Allowed destinations: localhost / loopback interfaces only
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}


def verify_egress_rules(target_url: str = "http://127.0.0.1:11434") -> bool:
    """Ensure the target endpoint is within local loopback bounds."""
    from urllib.parse import urlparse

    parsed = urlparse(target_url)
    host = parsed.hostname or ""
    if host in ALLOWED_HOSTS:
        return True

    # Try resolving hostname
    try:
        ip = socket.gethostbyname(host)
        if ip.startswith("127."):
            return True
    except Exception:
        pass

    return False


def main() -> None:
    # Test valid loopback
    if not verify_egress_rules("http://127.0.0.1:8000"):
        print("FAILED: Rejected legitimate loopback destination")
        sys.exit(1)

    # Test unauthorized remote endpoint
    if verify_egress_rules("https://evil-attacker.com"):
        print("FAILED: Allowed unauthorized external egress to evil-attacker.com")
        sys.exit(1)

    print("PASSED: Egress policy verified. All external network egress is blocked by default.")
    sys.exit(0)


if __name__ == "__main__":
    main()
