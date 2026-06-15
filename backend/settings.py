"""Centralized typed application settings (Task A-1).

Loads configuration from environment variables (and a local `.env` file
when present) via ``pydantic-settings``. Production-critical settings have
no defaults; if they are unset when ``ENVIRONMENT=production`` the
application fails fast at FastAPI lifespan startup.

The canonical list of shared environment variable names is defined in
``/docs/CONTRACT.md``. Backend-only runtime variables discovered during
implementation are documented here and in ``.env.example``.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Populate ``os.environ`` from the repo-root ``.env`` before anything else
# reads it. Pydantic-settings handles ``.env`` for its own typed fields,
# but several modules (notably ``backend/database/core.py`` and the
# legacy VLM cost lookups in ``backend/api/v1_admin.py``) still read
# ``os.getenv(...)`` directly. Running ``load_dotenv()`` here means a
# developer who copies ``.env.example`` to ``.env`` gets a consistent
# configuration across the whole process, which is the behaviour
# promised by Task A-1's acceptance criterion #3.
try:  # pragma: no cover - best-effort, optional dep
    from dotenv import load_dotenv as _load_dotenv

    _load_dotenv(override=False)
except Exception:
    pass


Environment = Literal["development", "staging", "production"]

# Required environment variable names that must be present (non-empty) when
# the application is started in production mode. Keys here are the shared
# names used in the deployment contract; they map 1:1 to the typed fields
# on ``Settings`` via pydantic's default case-insensitive env binding.
_REQUIRED_IN_PRODUCTION: tuple[str, ...] = (
    "DATABASE_URL",
    "SUPABASE_JWT_SECRET",
    "CORS_ALLOWED_ORIGINS",
    "VLM_HARD_LIMIT_USD",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Environment = Field(default="development")

    database_url: Optional[str] = Field(default=None)
    supabase_jwt_secret: Optional[str] = Field(default=None)
    cors_allowed_origins: Optional[str] = Field(default=None)
    # Optional regex matched against the Origin header. Useful for allowing
    # Vercel preview URLs (e.g. https://image-tagger-<hash>-<team>.vercel.app)
    # without enumerating each one in cors_allowed_origins.
    cors_allowed_origin_regex: Optional[str] = Field(default=None)
    vlm_hard_limit_usd: Optional[float] = Field(default=None)

    image_storage_root: str = Field(default="data_store")
    log_level: str = Field(default="INFO")
    enable_legacy_prefixes: bool = Field(default=True)

    supabase_url: Optional[str] = Field(default=None)
    supabase_anon_key: Optional[str] = Field(default=None)

    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    gemini_api_key: Optional[str] = Field(default=None)
    google_api_key: Optional[str] = Field(default=None)

    # Legacy header-trust auth secret. Replaced by Supabase JWT in Task A-3.
    # Kept here only so no literal default leaks into backend/services/auth.py.
    api_secret: Optional[str] = Field(default=None)

    # Static demo token — if set, any bearer matching this value is accepted
    # as an admin user on all protected routes. Intended for permanent demo
    # deployments where Supabase JWT rotation is not desired.
    demo_token: Optional[str] = Field(default=None)

    # Deferred in Phase 1 (see PLAN_BACKEND_PHASE1.md Task A-10).
    sentry_dsn: Optional[str] = Field(default=None)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origins_list(self) -> List[str]:
        raw = self.cors_allowed_origins
        if not raw:
            return []
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    def assert_production_ready(self) -> None:
        """Raise ``RuntimeError`` if any production-critical setting is missing.

        Called from the FastAPI lifespan on startup so the process aborts
        with a clear, actionable message before it begins serving traffic.
        In non-production environments this is a no-op and local dev
        defaults remain in effect.
        """
        if not self.is_production:
            return

        value_map = {
            "DATABASE_URL": self.database_url,
            "SUPABASE_JWT_SECRET": self.supabase_jwt_secret,
            "CORS_ALLOWED_ORIGINS": self.cors_allowed_origins,
            "VLM_HARD_LIMIT_USD": self.vlm_hard_limit_usd,
        }
        missing = [
            name
            for name, value in value_map.items()
            if value is None or (isinstance(value, str) and not value.strip())
        ]
        if missing:
            raise RuntimeError(
                "Cannot start backend in production mode: missing required "
                "environment variable(s): "
                + ", ".join(missing)
                + ". Populate them (e.g. via the deployment secret store) "
                "and retry."
            )


def _build_settings() -> Settings:
    return Settings()


settings: Settings = _build_settings()

# Ensure the image storage directory exists when possible. Mirrors the
# historical behaviour of backend/services/storage.py::get_image_storage_root
# so nothing else has to know about the detail.
try:
    Path(settings.image_storage_root).mkdir(parents=True, exist_ok=True)
except Exception:  # pragma: no cover - best-effort on read-only FS
    pass


# Backwards-compat module-level alias consumed by legacy code paths that
# import ``from backend.settings import IMAGE_STORAGE_ROOT`` (see
# backend/api/v1_admin.py). New code should prefer ``settings.image_storage_root``.
IMAGE_STORAGE_ROOT: str = settings.image_storage_root


__all__ = [
    "Settings",
    "settings",
    "IMAGE_STORAGE_ROOT",
]
