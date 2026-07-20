from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.frontend import router as frontend_router
from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import LocalRateLimitMiddleware, RequestIdMiddleware, RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.core.startup_validation import validate_startup
from app.db.session import get_db

configure_logging()
settings = get_settings()
logger = logging.getLogger(__name__)
validate_startup(settings)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting %s with database %s", settings.app_name, settings.database_url)
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health"},
        {"name": "Developers"},
        {"name": "Projects"},
        {"name": "Contacts"},
        {"name": "Social Profiles"},
        {"name": "Source Evidence"},
        {"name": "Exports"},
        {"name": "Collection Jobs"},
        {"name": "Map Configuration"},
        {"name": "Google Places"},
        {"name": "Worker Status"},
        {"name": "Frontend"},
    ],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LocalRateLimitMiddleware, settings=settings)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)
register_exception_handlers(app)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(frontend_router)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/ready", tags=["Health"])
def ready(db: Session = Depends(get_db)) -> dict[str, object]:
    db.execute(text("SELECT 1"))
    return {"status": "ready", "database": {"reachable": True}}
