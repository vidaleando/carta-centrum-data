"""Shared helpers for the data import scripts.

Every importer follows the same shape: fetch, then parse and validate, then
replace the table's rows in one transaction. A failure at any point leaves the
existing data untouched. Importers never create tables; run migrations first.
"""
import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable, Sequence

import asyncpg
import httpx

from app.config import get_settings

log = logging.getLogger("importers")

USER_AGENT = "carta-magna-import/1.0"


class ImportFailed(Exception):
    """Raised for expected failures (bad input, upstream errors). Exits with status 1."""


async def connect() -> asyncpg.Connection:
    settings = get_settings()
    log.info("Connecting to %s", settings.database_label)
    return await asyncpg.connect(dsn=settings.asyncpg_dsn)


async def replace_rows(conn: asyncpg.Connection, table: str, insert_sql: str, rows: Sequence[tuple]) -> None:
    """Atomically replace every row of public.<table> with `rows`.

    Uses DELETE rather than TRUNCATE so API reads aren't blocked during the import.
    """
    if not rows:
        raise ImportFailed(f"Refusing to replace public.{table} with zero rows")
    if await conn.fetchval("SELECT to_regclass($1)", f"public.{table}") is None:
        raise ImportFailed(f"Table public.{table} does not exist. Run `python -m migrations` first.")
    async with conn.transaction():
        await conn.execute(f"DELETE FROM public.{table}")
        await conn.executemany(insert_sql, rows)
    log.info("Replaced public.%s with %d rows", table, len(rows))


def run(main: Callable[[], Awaitable[None]]) -> None:
    """Entry point for `python -m importers.<name>`."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # httpx logs full request URLs at INFO, which would include API keys.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        asyncio.run(main())
    except ImportFailed as e:
        log.error("Import failed: %s", e)
        sys.exit(1)
    except httpx.TransportError as e:
        # Only the host: some httpx messages include the full URL, and with it API keys.
        log.error("Import failed: %s contacting %s", type(e).__name__, e.request.url.host)
        sys.exit(1)
