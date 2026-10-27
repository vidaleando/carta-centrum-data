import asyncio
import logging

import asyncpg

from app.config import get_settings
from migrations import apply_migrations

log = logging.getLogger("migrations")


async def main() -> None:
    settings = get_settings()
    log.info("Migrating %s", settings.database_label)
    conn = await asyncpg.connect(dsn=settings.asyncpg_dsn)
    try:
        applied = await apply_migrations(conn)
    finally:
        await conn.close()
    log.info("Applied: %s", ", ".join(applied) if applied else "nothing (up to date)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(main())
