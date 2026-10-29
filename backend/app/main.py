"""FastAPI app: GeoJSON API over PostGIS, plus the built Svelte frontend.

Run from backend/:  uvicorn app.main:app --reload --port 8001
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.auth import jwks_client, require_user
from app.config import Settings, get_settings
from app.db import Database
from app.routers import boundaries, constituencies, datacentres, demo, health, spa

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
log = logging.getLogger(__name__)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.demo_mode:
            log.warning("DEMO_MODE is on: serving sample data, no database")
        else:
            try:
                await app.state.db.pool()
            except Exception:
                # Keep serving: /health reports 503 and requests retry the connection.
                log.exception("Could not connect to %s at startup", settings.database_label)
        yield
        await app.state.db.close()

    app = FastAPI(
        title="Carta Magna API",
        description="UK data centres, parliamentary constituencies and MPs, served as GeoJSON from PostGIS.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.db = Database(settings)
    if settings.auth_enabled:
        app.state.jwks = jwks_client(settings)

    # The boundary layers are several MB of GeoJSON. Compressing them also keeps
    # them under Vercel's 4.5 MB function response limit.
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET"],
            allow_headers=["*"],
        )

    # /health stays open for uptime checks; everything else needs a signed-in user.
    protected = [Depends(require_user)] if settings.auth_enabled else []
    if settings.demo_mode:
        app.include_router(demo.router, dependencies=protected)
    else:
        app.include_router(health.router)
        app.include_router(datacentres.router, dependencies=protected)
        app.include_router(constituencies.router, dependencies=protected)
        app.include_router(boundaries.router, dependencies=protected)
    # Catch-all: must be last.
    app.include_router(spa.router)
    return app


app = create_app()
