"""Serves the built Svelte app. Must be included after every other router."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.config import Settings, app_settings

router = APIRouter(include_in_schema=False)

# Paths that must never fall back to index.html.
_RESERVED_PREFIXES = ("api/", "assets/", "docs", "redoc", "openapi.json")
# Files that must be revalidated on every load so new deploys are picked up.
_NO_CACHE = {"Cache-Control": "no-cache"}


@router.get("/{full_path:path}")
async def serve_frontend(full_path: str, settings: Settings = Depends(app_settings)):
    build_dir = settings.frontend_build_dir.resolve()

    # Real files first (sw.js, manifest.json, favicon.svg, /assets/*), guarding
    # against paths that resolve outside the build directory.
    if full_path:
        candidate = (build_dir / full_path).resolve()
        if candidate.is_file() and candidate.is_relative_to(build_dir):
            headers = None if full_path.startswith("assets/") else _NO_CACHE
            return FileResponse(candidate, headers=headers)

    if full_path.startswith(_RESERVED_PREFIXES):
        raise HTTPException(status_code=404, detail="Not found")

    # Anything else is a client-side route.
    index_path = build_dir / "index.html"
    if index_path.is_file():
        return FileResponse(index_path, headers=_NO_CACHE)
    return {"message": "API is running. Frontend not built."}
