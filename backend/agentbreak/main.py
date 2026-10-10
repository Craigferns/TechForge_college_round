from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentbreak.api import (
    audits,
    dashboard,
    discovery,
    findings,
    fixes,
    policies,
    runs,
    sleeper,
    suites,
    system,
    targets,
)
from agentbreak.config import get_settings
from agentbreak.db import get_connection, migrate
from agentbreak.engine.jobs import get_job_pool, reset_job_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle context manager performing startup recovery and clean shutdown."""
    settings = get_settings()
    conn = get_connection(settings.db_path)
    migrate(conn)
    get_job_pool().startup_recovery(conn)
    conn.close()
    yield
    reset_job_pool()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="AgentBreak API",
        version="0.1.0",
        description="Autonomous security-testing platform for tool-using AI agents",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API v1 routers
    app.include_router(system.router, prefix="/api/v1")
    app.include_router(targets.router, prefix="/api/v1")
    app.include_router(suites.router, prefix="/api/v1")
    app.include_router(policies.router, prefix="/api/v1")
    app.include_router(runs.router, prefix="/api/v1")
    app.include_router(sleeper.router, prefix="/api/v1")
    app.include_router(discovery.router, prefix="/api/v1")
    app.include_router(findings.router, prefix="/api/v1")
    app.include_router(audits.router, prefix="/api/v1")
    app.include_router(fixes.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")

    return app


app = create_app()
