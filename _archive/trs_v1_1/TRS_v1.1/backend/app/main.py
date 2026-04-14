import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from .routes import router
from .routes_proposals import router as proposals_router
from .routes_search import router as search_router
from .routes_health import router as health_router
from .dashboard import router as dashboard_router
from .logging_config import setup_logging, get_logger
from .middleware import setup_middleware

# Setup logging
log_level = os.getenv("TRS_LOG_LEVEL", "INFO")
json_logs = os.getenv("TRS_JSON_LOGS", "false").lower() == "true"
setup_logging(level=log_level, json_format=json_logs)

logger = get_logger(__name__)

app = FastAPI(
    title="Tag Registry Service (TRS)",
    version="0.0.5",
    description="""
## Tag Registry Service API

The Tag Registry Service (TRS) is the centralized tag management system for the NeuroArch research platform.

### Features

- **Registry**: Browse and search 400+ environmental psychology tags
- **Proposals**: Submit, review, and approve tag changes
- **Releases**: Versioned releases with validation gates
- **Contracts**: Consumer-specific projections (Image Tagger, Article Eater, etc.)

### Authentication

Write operations require an API key. Include it in the `X-API-Key` header.

Roles:
- `viewer`: Read-only access
- `proposer`: Submit proposals
- `reviewer`: Approve/reject proposals
- `admin`: Release and key management

### Getting Started

1. Get an API key: `python bin/keys.py create "Your Name" proposer`
2. Browse tags: `GET /registry`
3. Search: `GET /api/search?q=lighting`
4. Submit proposal: `POST /api/proposals`
    """,
    contact={
        "name": "TRS Support",
        "email": "trs@example.com",
    },
    license_info={
        "name": "MIT",
    },
)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication",
        }
    }
    
    # Add tags
    openapi_schema["tags"] = [
        {"name": "registry", "description": "Tag registry operations"},
        {"name": "proposals", "description": "Proposal workflow"},
        {"name": "search", "description": "Search and discovery"},
        {"name": "releases", "description": "Release management"},
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# CORS for Streamlit UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
from .ratelimit import RateLimitMiddleware
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    exempt_paths=["/health", "/ready", "/live", "/metrics"],
)

# Setup observability middleware
setup_middleware(
    app,
    enable_tracing=True,
    enable_error_tracking=True,
    enable_metrics=True,
    enable_slow_request_logging=True,
    slow_request_threshold=1.0,
)

# Include routers
app.include_router(router)  # Existing registry routes
app.include_router(proposals_router, prefix="/api")  # Proposal routes
app.include_router(search_router, prefix="/api")  # Search routes
app.include_router(health_router)  # Health check routes
app.include_router(dashboard_router)  # Dashboard/metrics routes

logger.info("TRS API started", extra={"version": app.version})
