"""Importer parsing (pure) and loading (against the test database, rolled back)."""
import asyncpg
import pytest

from importers import constituencies, mps, osm_datacentres
from importers.common import ImportFailed, replace_rows
from migrations import apply_migrations
from tests.conftest import requires_db, run_db

SQUARE = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}


def test_parse_constituencies_uses_ons_2024_fields_and_skips_incomplete():
    rows = constituencies.parse_constituencies({"features": [
        {"properties": {"PCON24NM": "Aberavon and Neath", "PCON24CD": "W07000081", "PCON24NMW": "Aberafan a Castell-nedd"},
         "geometry": SQUARE},
        {"properties": {"PCON24NM": "No Geometry"}, "geometry": None},
        {"properties": {}, "geometry": SQUARE},
    ]})
    assert [r[:3] for r in rows] == [("W07000081", "Aberavon and Neath", "Aberafan a Castell-nedd")]


def test_parse_mps_takes_first_office_and_skips_duplicates():
    rows = mps.parse_mps([
        {"member_id": "1", "person_id": "10", "name": "A", "party": "Labour", "constituency": "X",
         "office": [{"position": "Minister"}, {"position": "Other"}]},
        {"member_id": "1", "name": "Duplicate"},
        {"name": "No id"},
        {"member_id": 2, "name": "B"},
    ])
    assert [(r[0], r[1], r[2], r[5]) for r in rows] == [("1", 10, "A", "Minister"), ("2", 0, "B", None)]
    assert rows[1][3:5] == ("Unknown", "Unknown")


def test_parse_osm_elements_keeps_node_and_way_with_same_number_apart():
    rows = osm_datacentres.parse_elements([
        {"type": "node", "id": 5, "lat": 51.0, "lon": -1.0, "tags": {"name": "Node DC"}},
        {"type": "way", "id": 5, "center": {"lat": 52.0, "lon": -2.0}, "tags": {"operator": "Op Ltd"}},
        {"type": "relation", "id": 9, "center": {"lat": 53.0, "lon": -3.0}, "tags": {}},
        {"type": "way", "id": 6, "tags": {}},  # no centre: skipped
    ])
    assert rows == [
        ("node/5", "Node DC", None, "OpenStreetMap", -1.0, 51.0),
        ("way/5", "Op Ltd", "Op Ltd", "OpenStreetMap", -2.0, 52.0),
        ("relation/9", "Unnamed", None, "OpenStreetMap", -3.0, 53.0),
    ]


def test_overpass_query_covers_nodes_ways_and_relations():
    query = osm_datacentres.build_overpass_query()
    assert 'nwr["man_made"="data_center"](49.0,-10.0,61.0,2.0);' in query
    assert query.endswith("out center;")


# --- Loading (each test runs inside a transaction that is rolled back) ---

class _Rollback(Exception):
    pass


def run_and_rollback(coro_fn):
    async def wrapper(conn: asyncpg.Connection):
        await apply_migrations(conn)
        try:
            async with conn.transaction():
                result = await coro_fn(conn)
                raise _Rollback(result)
        except _Rollback as r:
            return r.args[0]
    return run_db(wrapper)


@requires_db
@pytest.mark.parametrize("module, table, row", [
    (constituencies, "uk_parliamentary_constituencies", ("E1", "Test Seat", "", '{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}')),
    (mps, "uk_mps", ("99", 1, "Test MP", "Green", "Test Seat", None, None)),
    (osm_datacentres, "osm_data_centers", ("node/99", "Test DC", None, "OpenStreetMap", -1.0, 51.0)),
])
def test_importer_sql_matches_schema(module, table, row):
    async def load(conn):
        await replace_rows(conn, table, module.INSERT_SQL, [row])
        return await conn.fetchval(f"SELECT count(*) FROM public.{table}")
    assert run_and_rollback(load) == 1


@requires_db
def test_failed_load_keeps_existing_rows():
    async def load(conn):
        await conn.execute("CREATE TEMP TABLE before AS SELECT osm_id FROM public.osm_data_centers")
        bad_row = ("node/1", "Bad", None, "OpenStreetMap", "not-a-number", 51.0)
        with pytest.raises(asyncpg.DataError):
            await replace_rows(conn, "osm_data_centers", osm_datacentres.INSERT_SQL, [bad_row])
        return await conn.fetchval(
            "SELECT count(*) = (SELECT count(*) FROM before) AND count(*) > 0 FROM public.osm_data_centers"
        )
    assert run_and_rollback(load) is True


@requires_db
def test_refuses_empty_or_missing_tables():
    async def load(conn):
        with pytest.raises(ImportFailed, match="zero rows"):
            await replace_rows(conn, "uk_mps", mps.INSERT_SQL, [])
        with pytest.raises(ImportFailed, match="Run `python -m migrations`"):
            await replace_rows(conn, "no_such_table", mps.INSERT_SQL, [("x",)])
        return True
    assert run_and_rollback(load)


@requires_db
def test_migrations_are_idempotent():
    assert run_db(apply_migrations) == []
