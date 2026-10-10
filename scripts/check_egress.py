"""Egress checking script verifying only allowed base_url destinations are queried (PLAN.md M11.2)."""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse


def check_egress_rules(target_url: str) -> bool:
    """Verify destination is allowed. In sandbox mode, only localhost or local ports are allowed unless remote flag set."""
    parsed = urlparse(target_url)
    hostname = parsed.hostname or ""

    is_local = hostname in ("localhost", "127.0.0.1", "::1", "")
    allow_remote = os.environ.get("AGENTBREAK_ALLOW_REMOTE_TARGETS") == "1"

    if is_local or allow_remote:
        print(
            f"PASS: Egress to '{target_url}' permitted (local={is_local}, allow_remote={allow_remote})."
        )
        return True
    else:
        print(
            f"BLOCK: Egress to '{target_url}' blocked by sandbox policy (remote targets disabled)."
        )
        return False


def main() -> int:
    test_urls = [
        "http://localhost:11434/v1",
        "http://127.0.0.1:8000/api/v1",
        "http://evil-external-server.com/exfil",
    ]

    print("Verifying sandbox egress controls...")
    # First two should pass
    p1 = check_egress_rules(test_urls[0])
    p2 = check_egress_rules(test_urls[1])
    # Third must be blocked
    p3 = not check_egress_rules(test_urls[2])

    if p1 and p2 and p3:
        print("ALL EGRESS CHECKS PASSED: Non-local egress successfully fails closed.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
