"""Command line interface for AgentBreak."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agentbreak.main import create_app


def export_openapi(output_path: Path) -> None:
    """Generate openapi.json from FastAPI schema."""
    app = create_app()
    openapi_schema = app.openapi()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"OpenAPI schema successfully exported to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentBreak CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser(
        "export-openapi", help="Export OpenAPI schema to openapi.json"
    )
    export_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("openapi.json"),
        help="Target output file path",
    )

    args = parser.parse_args()

    if args.command == "export-openapi":
        export_openapi(args.output)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
