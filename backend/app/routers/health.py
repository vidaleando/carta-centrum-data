import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas import Health

log = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=Health, responses={503: {"model": Health}})
async def health(request: Request):
    """Database connectivity. Returns 503 when the database is unreachable."""
    try:
        pool = await request.app.state.db.pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        log.exception("Health check failed")
        return JSONResponse(
            status_code=503,
            content=Health(status="unhealthy", database="unavailable").model_dump(),
        )
    return Health(status="healthy", database="connected")
