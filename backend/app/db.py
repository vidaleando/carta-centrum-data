"""Database connection pool and the FastAPI dependency that hands out connections."""
import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Optional

import asyncpg
from fastapi import Depends, HTTPException, Request

from app.config import Settings

log = logging.getLogger(__name__)


class Database:
    """Lazily created asyncpg pool.

    If the database is unreachable at startup the app still boots (so /health
    can report it), and each request retries the connection.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._pool: Optional[asyncpg.Pool] = None
        self._lock: Optional[asyncio.Lock] = None

    async def pool(self) -> asyncpg.Pool:
        if self._pool is not None:
            return self._pool
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            if self._pool is None:
                log.info("Connecting to database %s", self._settings.database_label)
                self._pool = await asyncpg.create_pool(
                    dsn=self._settings.asyncpg_dsn,
                    min_size=self._settings.db_pool_min_size,
                    max_size=self._settings.db_pool_max_size,
                    statement_cache_size=self._settings.db_statement_cache_size,
                    timeout=10,
                )
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


@asynccontextmanager
async def connection(request: Request) -> AsyncIterator[asyncpg.Connection]:
    """A pooled connection, or HTTP 503 if the database is unreachable."""
    database: Database = request.app.state.db
    try:
        pool = await database.pool()
    except Exception:
        log.exception("Database unavailable")
        raise HTTPException(status_code=503, detail="Database unavailable")
    async with pool.acquire() as conn:
        yield conn


async def get_conn(request: Request) -> AsyncIterator[asyncpg.Connection]:
    """FastAPI dependency wrapping connection()."""
    async with connection(request) as conn:
        yield conn


Conn = Annotated[asyncpg.Connection, Depends(get_conn)]
