import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

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
from agentbreak.seed import seed_database

log = logging.getLogger(__name__)
_HTTP_CODES = {400: "validation", 404: "not_found", 409: "conflict", 422: "validation"}


def _envelope(status_code: int, code: str, message: str) -> JSONResponse:
    # PLAN §15.1 error envelope; the frontend client reads error.message.
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": {}}},
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle context manager performing startup recovery and clean shutdown."""
    settings = get_settings()
    conn = get_connection(settings.db_path)
    migrate(conn)
    seed_database(conn)  # idempotent: the simulated demo target + base policies always exist
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

    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, exc: HTTPException) -> JSONResponse:
        return _envelope(
            exc.status_code, _HTTP_CODES.get(exc.status_code, "internal"), str(exc.detail)
        )

    @app.exception_handler(ValueError)
    async def _value_error(_: Request, exc: ValueError) -> JSONResponse:
        return _envelope(422, "validation", str(exc))

    @app.exception_handler(Exception)
    async def _internal_error(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled API error")  # full detail stays in the server log
        return _envelope(500, "internal", f"Internal error ({type(exc).__name__}).")

    @app.get("/", include_in_schema=False)
    def root() -> HTMLResponse:
        # Port 8000 is the API. People open it in a browser expecting the UI; say where it is.
        return HTMLResponse(
            "<!doctype html><meta charset=utf-8><title>AgentBreak API</title>"
            "<body style='font:15px system-ui;margin:3rem;max-width:40rem'>"
            "<h1>AgentBreak API is running</h1>"
            "<p>This port serves the API only. The interface runs separately: start it with "
            "<code>cd frontend &amp;&amp; npm run dev</code> and open "
            "<a href='http://127.0.0.1:5173'>http://127.0.0.1:5173</a>.</p>"
            "<p>API reference: <a href='/docs'>/docs</a> &middot; health: "
            "<a href='/api/v1/health'>/api/v1/health</a></p>"
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
