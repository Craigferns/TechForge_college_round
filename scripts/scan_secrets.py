"""Security scanning script checking for sensitive tokens or credentials in the repo."""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Patterns indicating hardcoded private keys or live API tokens (not fake test ones)
SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----"), "Private key block detected"),
    (
        re.compile(
            r"(?i)(aws_access_key_id|aws_secret_access_key)\s*=\s*['\"][A-Za-z0-9/+=]{16,}['\"]"
        ),
        "AWS credential pattern",
    ),
    (re.compile(r"(?i)ghp_[0-9a-zA-Z]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"(?i)sk-[a-zA-Z0-9]{32,}"), "OpenAI API Key pattern"),
]

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
}


def scan_file(file_path: Path) -> list[str]:
    violations: list[str] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return violations

    for pattern, desc in SECRET_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            violations.append(f"{file_path}: {desc}")

    return violations


def scan_repo(root: Path) -> list[str]:
    all_violations: list[str] = []
    for item in root.rglob("*"):
        if item.is_file():
            if any(part in EXCLUDE_DIRS for part in item.parts):
                continue
            if item.suffix in (
                ".py",
                ".json",
                ".md",
                ".ts",
                ".tsx",
                ".yaml",
                ".yml",
                ".env",
                ".toml",
            ):
                all_violations.extend(scan_file(item))
    return all_violations


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    violations = scan_repo(repo_root)
    if violations:
        print(f"FAILED: Found {len(violations)} secret violation(s):")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)

    print("PASSED: No unapproved secrets found in repository.")
    sys.exit(0)


if __name__ == "__main__":
    main()
