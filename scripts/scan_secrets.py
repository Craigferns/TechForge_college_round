"""Script scanning repository codebase for potential secret leaks (PLAN.md §20 / M11.2)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Patterns for potential secrets
SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"ghp_[0-9a-zA-Z]{36}", "GitHub Personal Access Token"),
    (r"sk-[a-zA-Z0-9]{48}", "OpenAI API Key"),
    (r"AIza[0-9A-Za-z-_]{35}", "Google API Key"),
]

ALLOWED_CANARY_PREFIX = "AB-CANARY-"


def scan_file(file_path: Path) -> list[str]:
    violations = []
    # Skip binary, venv, git, node_modules
    if any(
        part in file_path.parts for part in (".git", ".venv", "node_modules", "dist", "__pycache__")
    ):
        return []

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    for pattern, desc in SECRET_PATTERNS:
        matches = re.findall(pattern, content)
        for m in matches:
            violations.append(
                f"{desc} pattern detected in {file_path.relative_to(REPO_ROOT)}: {m[:6]}..."
            )

    return violations


def main() -> int:
    print(f"Scanning {REPO_ROOT} for secrets...")
    all_violations = []

    for path in REPO_ROOT.rglob("*"):
        if path.is_file():
            violations = scan_file(path)
            all_violations.extend(violations)

    if all_violations:
        print(f"FAILED: {len(all_violations)} potential secret(s) found:")
        for v in all_violations:
            print(f" - {v}")
        return 1

    print("PASS: 0 secrets found. Clean repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
