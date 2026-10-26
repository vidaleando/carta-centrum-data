"""Application settings, read from environment variables and backend/.env."""
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from fastapi import Request
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

# libpq connection parameters that asyncpg doesn't understand. asyncpg would
# forward them to the server as runtime settings, which the server rejects.
_LIBPQ_ONLY_PARAMS = {"channel_binding"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: Optional[str] = None
    # Serve fixture data without a database. Off by default: without it, a
    # missing database is an error (503), not a silent fallback.
    demo_mode: bool = False
    # Comma-separated list of allowed origins. Empty disables CORS, which is
    # right when the frontend is served from the same origin (the default).
    cors_origins: str = ""
    frontend_build_dir: Path = REPO_DIR / "frontend" / "build"
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10
    theyworkforyou_key: Optional[str] = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def asyncpg_dsn(self) -> str:
        """DATABASE_URL with libpq-only query parameters removed."""
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not set")
        parsed = urlparse(self.database_url)
        query = [(k, v) for k, v in parse_qsl(parsed.query) if k not in _LIBPQ_ONLY_PARAMS]
        return urlunparse(parsed._replace(query=urlencode(query)))

    @property
    def database_label(self) -> str:
        """Host and database name, safe to log (no credentials)."""
        if not self.database_url:
            return "<unset>"
        parsed = urlparse(self.database_url)
        return f"{parsed.hostname}/{parsed.path.lstrip('/')}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def app_settings(request: Request) -> Settings:
    """FastAPI dependency: the settings the running app was created with."""
    return request.app.state.settings
