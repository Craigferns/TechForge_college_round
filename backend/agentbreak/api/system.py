"""System health and metadata endpoints."""

from fastapi import APIRouter

from agentbreak.schemas import Health, Meta

router = APIRouter(tags=["system"])


@router.get("/health", response_model=Health)
def health_check() -> Health:
    """Return operational health status, versions, and database connectivity."""
    return Health(
        status="ok",
        version="0.1.0",
        agentdojo_version="0.1.35",
        db_ok=True,
    )


@router.get("/meta", response_model=Meta)
def get_meta() -> Meta:
    """Return platform metadata, supported test suites, scenarios, defenses, and limits."""
    return Meta(
        suites=["acme"],
        scenarios=["ipi-exfil", "malicious-doc", "sleeper-memory", "priv-esc"],
        fix_kinds=["remove_permission", "restrict_arg", "defense", "prompt_hardening"],
        defenses=[
            "tool_filter",
            "transformers_pi_detector",
            "spotlighting_with_delimiting",
            "repeat_user_prompt",
        ],
        verifier_version="1.0.0",
        limits={"max_attempts": 40, "max_seconds": 300},
    )
