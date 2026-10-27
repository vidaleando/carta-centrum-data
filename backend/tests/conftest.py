"""Test setup.

Database tests run against TEST_DATABASE_URL (a disposable PostGIS database,
e.g. `docker run -e POSTGRES_PASSWORD=test -p 55432:5432 postgis/postgis:15-3.3`)
and are skipped when it isn't set. DATABASE_URL and backend/.env are never used,
because the fixtures wipe and reseed tables.
"""
import asyncio
import os
from contextlib import contextmanager
from pathlib import Path

import asyncpg
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from migrations import apply_migrations

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
SEED_SQL = Path(__file__).parent / "fixtures" / "seed.sql"

requires_db = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set")


def make_settings(**overrides) -> Settings:
    """Settings isolated from the environment's .env file."""
    return Settings(_env_file=None, **overrides)


@contextmanager
def client_for(**overrides):
    with TestClient(create_app(make_settings(**overrides))) as client:
        yield client


async def _run_sql(*statements: str) -> None:
    conn = await asyncpg.connect(dsn=TEST_DATABASE_URL)
    try:
        for sql in statements:
            await conn.execute(sql)
    finally:
        await conn.close()


def run_db(coro_fn):
    """Run `coro_fn(conn)` against the test database and return its result."""
    async def runner():
        conn = await asyncpg.connect(dsn=TEST_DATABASE_URL)
        try:
            return await coro_fn(conn)
        finally:
            await conn.close()
    return asyncio.run(runner())


@pytest.fixture(scope="session")
def seeded_db():
    run_db(apply_migrations)
    asyncio.run(_run_sql(SEED_SQL.read_text()))
    return TEST_DATABASE_URL


@pytest.fixture
def db_client(seeded_db):
    with client_for(database_url=seeded_db) as client:
        yield client
