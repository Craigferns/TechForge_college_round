"""Verify that all sandbox fixtures and environment data comply with fake data rules."""

from __future__ import annotations

import re
import sys

from agentbreak.sandbox.acme.env import AcmeEnv

CANARY_REGEX = re.compile(r"^AB-CANARY-(KEY|BUD)-[0-9a-f]{4,8}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$")


def lint_environment(env: AcmeEnv) -> list[str]:
    """Scan AcmeEnv for compliance with fake-data rules. Returns list of violations."""
    violations: list[str] = []

    # Check all email addresses in inbox
    for email in env.inbox:
        if not email.sender.endswith(".test"):
            violations.append(f"Inbox email sender '{email.sender}' does not end with .test")
        for r in email.recipients:
            if not r.endswith(".test"):
                violations.append(f"Inbox email recipient '{r}' does not end with .test")

    # Check all email addresses in directory
    for principal in env.directory.keys():
        if not principal.endswith(".test"):
            violations.append(f"Directory principal '{principal}' does not end with .test")

    # Check canary format in files
    canaries_found = 0
    for file_obj in env.drive.values():
        for token in re.findall(r"AB-CANARY-[A-Z]+-[0-9a-fA-F]+", file_obj.content):
            canaries_found += 1
            if not CANARY_REGEX.match(token):
                violations.append(
                    f"Canary token '{token}' in file '{file_obj.id}' does not match required regex"
                )

    if canaries_found < 2:
        violations.append(
            f"Expected at least 2 canary tokens (budget + key) in drive files, found {canaries_found}"
        )

    return violations


def main() -> None:
    env = AcmeEnv.create_default()
    violations = lint_environment(env)
    if violations:
        print("Fake data linting FAILED:")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)

    print("Fake data linting PASSED: all emails end in .test and canaries match required format.")
    sys.exit(0)


if __name__ == "__main__":
    main()
