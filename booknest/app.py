"""FastAPI application factory for BookNest."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from booknest import api, web
from booknest.services import DomainError
from booknest.store import Store


def create_app(store: Store | None = None, testing_enabled: bool | None = None) -> FastAPI:
    app = FastAPI(
        title="BookNest API",
        version="1.0.0",
        description="Online bookstore used as the system under test in "
        "'Agentic QA for Software Delivery'. Monetary values are decimal strings in USD.",
    )
    # Serve the hand-written spec (/docs, /redoc, /openapi.json) instead of the auto-generated one.
    spec = yaml.safe_load((Path(__file__).parent / "openapi.yml").read_text(encoding="utf-8"))
    app.openapi = lambda: spec  # type: ignore[method-assign]
    app.state.store = store or Store()
    if testing_enabled is None:
        testing_enabled = os.environ.get("BOOKNEST_TESTING", "1") == "1"
    app.state.testing_enabled = testing_enabled

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(api.router)
    app.include_router(web.router)
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    return app
