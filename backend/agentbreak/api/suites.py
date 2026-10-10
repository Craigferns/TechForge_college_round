"""Suites, scenarios, and attack cases endpoints."""

from fastapi import APIRouter, HTTPException, status

from agentbreak.schemas import AttackCase, ScenarioSpec, SuiteInfo

router = APIRouter(tags=["suites"])


@router.get("/suites/acme", response_model=SuiteInfo)
def get_suite_acme() -> SuiteInfo:
    """Retrieve specifications for the Acme Corporation benchmark suite (tools, tasks, vectors)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/scenarios", response_model=list[ScenarioSpec])
def list_scenarios() -> list[ScenarioSpec]:
    """List all 4 core evaluation scenarios (ipi-exfil, malicious-doc, sleeper-memory, priv-esc)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/scenarios/{scenario_id}", response_model=ScenarioSpec)
def get_scenario(scenario_id: str) -> ScenarioSpec:
    """Retrieve full configuration and attack cases for a scenario."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")


@router.get("/attack-cases", response_model=list[AttackCase])
def list_attack_cases() -> list[AttackCase]:
    """List all registered attack test cases (AS-01 through AS-07)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint stub")
