from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database.core import Base, engine
import backend.models  # noqa: F401  # registers ORM mappers before create_all
from backend.error_handlers import register_exception_handlers
from backend.logging_config import configure_logging, get_logger
from backend.middleware.request_context import RequestContextMiddleware
from backend.services.storage import get_image_storage_root
from backend.settings import settings
from backend.api import (
    health,
    v1_annotation,
    v1_admin,
    v1_supervision,
    v1_discovery,
    v1_bn_export,
    v1_debug,
    v1_features,
    v1_vlm_health,
)
from backend.versioning import VERSION

# Configure structured logging before the app is constructed so any
# import-time logger calls already use the JSON formatter.
configure_logging(settings.log_level)
logger = get_logger("backend.main")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Fail fast when a production deployment is missing required secrets.
    # No-op in development/staging; see backend/settings.py::Settings.
    settings.assert_production_ready()
    # Idempotent schema bootstrap. Replaces the Render pre-deploy command,
    # which is unavailable on the free plan. create_all is a no-op when
    # tables already exist, so it is safe on every boot.
    Base.metadata.create_all(bind=engine)
    logger.info(
        "backend.startup",
        environment=settings.environment,
        version=VERSION,
    )
    yield
    logger.info("backend.shutdown")

# v3 Enterprise Application Entry Point
class PrefixStripMiddleware:
    """Strip known prefixes from incoming paths while preserving routing."""

    def __init__(self, app: Callable, prefixes: list[str]) -> None:
        self.app = app
        self.prefixes = [p.rstrip("/") for p in prefixes]

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] in {"http", "websocket"}:
            path = scope.get("path", "")
            for prefix in self.prefixes:
                if path == prefix or path.startswith(f"{prefix}/"):
                    scope = dict(scope)
                    scope["path"] = path[len(prefix):] or "/"
                    scope["root_path"] = f"{scope.get('root_path', '')}{prefix}"
                    break
        await self.app(scope, receive, send)


app = FastAPI(
    title=f"Image Tagger v3 (v{VERSION})",
    description="Unified API for Tagger Workbench, Supervisor, Admin, and Explorer.",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS: allow the configured browser origins to call the API. Added before
# other middleware so OPTIONS preflights are handled by CORSMiddleware
# rather than the router (which would return 405). cors_allowed_origin_regex
# is optional and matches dynamic preview URLs (e.g. Vercel preview deploys).
_cors_origins = settings.cors_origins_list
_cors_regex = settings.cors_allowed_origin_regex
if _cors_origins or _cors_regex:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_origin_regex=_cors_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

if settings.enable_legacy_prefixes:
    app.add_middleware(
        PrefixStripMiddleware,
        prefixes=[
            "/api/v1/tagger",
            "/api",
        ],
    )

# Request-id + access-log middleware. Added last so it wraps every other
# middleware (Starlette executes the most-recently-added middleware
# outermost), guaranteeing X-Request-ID is set on every response and the
# access log captures the full request lifetime including prefix
# rewriting.
app.add_middleware(RequestContextMiddleware)

# Global exception handlers — every error response is shaped to the
# contract envelope { error: { code, message, request_id, details? } }.
# Registered after middleware so the request id contextvar is bound by
# the time a handler runs.
register_exception_handlers(app)

# Router wiring
app.include_router(health.router)
app.include_router(v1_annotation.router)
app.include_router(v1_admin.router)
app.include_router(v1_supervision.router)
app.include_router(v1_discovery.router)
app.include_router(v1_bn_export.router)
app.include_router(v1_debug.router)
app.include_router(v1_features.router)
app.include_router(v1_vlm_health.router)

# Static file mount for image assets
IMAGE_STORAGE_ROOT = get_image_storage_root()
app.mount("/static", StaticFiles(directory=str(IMAGE_STORAGE_ROOT)), name="static")


@app.get("/")
def root():
    return {
        "message": "Image Tagger v3 API",
        "docs": "/docs",
        "workbench_api": "/v1/workbench/next",
    }
