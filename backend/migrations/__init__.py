"""Plain-SQL schema migrations.

Files named NNN_description.sql are applied in order, each in its own
transaction, and recorded in public.schema_migrations. Never edit a migration
that has been applied anywhere; add a new file instead.

Apply pending migrations (from backend/):  python -m migrations
"""
from pathlib import Path

import asyncpg

MIGRATIONS_DIR = Path(__file__).resolve().parent
# Arbitrary constant: serialises concurrent migration runs.
_ADVISORY_LOCK_ID = 727_100_001


async def apply_migrations(conn: asyncpg.Connection) -> list[str]:
    """Apply pending migrations and return the versions applied."""
    await conn.execute("SELECT pg_advisory_lock($1)", _ADVISORY_LOCK_ID)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        applied = {r["version"] for r in await conn.fetch("SELECT version FROM public.schema_migrations")}
        newly_applied = []
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.stem in applied:
                continue
            async with conn.transaction():
                await conn.execute(path.read_text())
                await conn.execute("INSERT INTO public.schema_migrations (version) VALUES ($1)", path.stem)
            newly_applied.append(path.stem)
        return newly_applied
    finally:
        await conn.execute("SELECT pg_advisory_unlock($1)", _ADVISORY_LOCK_ID)
