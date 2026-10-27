"""Import UK data centres and related telecom infrastructure from OpenStreetMap.

Usage (from backend/):  python -m importers.osm_datacentres
"""
import logging

import httpx

from importers.common import USER_AGENT, ImportFailed, connect, replace_rows, run

log = logging.getLogger("importers.osm_datacentres")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# south, west, north, east: Great Britain and Northern Ireland
UK_BOUNDS = "49.0,-10.0,61.0,2.0"

# OSM tagging for data centres is inconsistent, so cast a wide net.
DATACENTRE_TAGS = [
    {"man_made": "data_center"},
    {"building": "data_center"},
    {"telecom": "data_center"},
    {"telecom": "exchange"},
    {"telecom": "connection_point"},
    {"building": "server_room"},
    {"building": "technical"},
    {"building": "data_hall"},
]

INSERT_SQL = """
    INSERT INTO public.osm_data_centers (osm_id, name, operator, source, geom)
    VALUES ($1, $2, $3, $4, ST_SetSRID(ST_MakePoint($5, $6), 4326))
"""


def build_overpass_query(bounds: str = UK_BOUNDS) -> str:
    parts = []
    for tags in DATACENTRE_TAGS:
        filters = "".join(f'["{k}"="{v}"]' for k, v in tags.items())
        parts.append(f"nwr{filters}({bounds});")
    # `out center` gives ways and relations a centre point, so all three become points.
    return f"[out:json][timeout:60];({''.join(parts)});out center;"


async def fetch_elements() -> list[dict]:
    log.info("Querying Overpass (this can take a minute)")
    async with httpx.AsyncClient(timeout=90.0, headers={"User-Agent": USER_AGENT}) as client:
        resp = await client.post(OVERPASS_URL, data={"data": build_overpass_query()})
    if resp.status_code != 200:
        raise ImportFailed(f"Overpass returned HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.json().get("elements", [])


def parse_elements(elements: list[dict]) -> list[tuple]:
    """Overpass elements -> (osm_id, name, operator, source, lon, lat) rows.

    osm_id is "<type>/<id>" (e.g. "way/123"): node, way and relation ids are
    separate namespaces in OSM, so the bare number is not unique.
    """
    rows = {}
    for el in elements:
        kind, el_id = el.get("type"), el.get("id")
        point = el if kind == "node" else el.get("center")
        if kind is None or el_id is None or not point or "lat" not in point:
            continue
        tags = el.get("tags", {})
        osm_id = f"{kind}/{el_id}"
        rows[osm_id] = (
            osm_id,
            tags.get("name", tags.get("operator", "Unnamed")),
            tags.get("operator"),
            "OpenStreetMap",
            point["lon"],
            point["lat"],
        )
    return list(rows.values())


async def main() -> None:
    elements = await fetch_elements()
    rows = parse_elements(elements)
    log.info("Parsed %d data centres from %d OSM elements", len(rows), len(elements))

    conn = await connect()
    try:
        await replace_rows(conn, "osm_data_centers", INSERT_SQL, rows)
    finally:
        await conn.close()


if __name__ == "__main__":
    run(main)
