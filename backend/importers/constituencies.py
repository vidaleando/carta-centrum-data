"""Import ONS Westminster constituency boundaries (July 2024) from a GeoJSON file.

Usage (from backend/):  python -m importers.constituencies [path/to/file.geojson]
Default file: backend/constituencies.geojson (WGS84 / EPSG:4326, not committed).
"""
import json
import logging
import sys
from pathlib import Path

from app.config import BACKEND_DIR
from importers.common import ImportFailed, connect, replace_rows, run

log = logging.getLogger("importers.constituencies")

DEFAULT_FILE = BACKEND_DIR / "constituencies.geojson"
EXPECTED_COUNT = 650

# ST_Multi handles files that mix Polygon and MultiPolygon.
INSERT_SQL = """
    INSERT INTO public.uk_parliamentary_constituencies (ons_code, name, name_welsh, geometry)
    VALUES ($1, $2, $3, ST_Multi(ST_GeomFromGeoJSON($4)))
"""


def parse_constituencies(data: dict) -> list[tuple]:
    """GeoJSON FeatureCollection -> (ons_code, name, name_welsh, geometry_json) rows."""
    rows, skipped = [], 0
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        geometry = feature.get("geometry")
        # 2024 ONS field names, with fallbacks for other exports.
        name = props.get("PCON24NM") or props.get("pcd24nm") or props.get("name")
        code = props.get("PCON24CD") or props.get("pcd24cd") or props.get("code") or ""
        name_welsh = props.get("PCON24NMW") or props.get("pcd24nmw") or ""
        if not geometry or not name:
            if not rows and not skipped:
                log.warning("Feature without geometry or name; property keys: %s", list(props))
            skipped += 1
            continue
        rows.append((code, name, name_welsh, json.dumps(geometry)))
    if skipped:
        log.warning("Skipped %d features (missing geometry or name)", skipped)
    return rows


async def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FILE
    if not path.is_file():
        raise ImportFailed(f"{path} not found")
    with path.open(encoding="utf-8") as f:
        rows = parse_constituencies(json.load(f))
    log.info("Parsed %d constituencies from %s", len(rows), path)
    if len(rows) != EXPECTED_COUNT:
        log.warning("Expected %d constituencies, got %d", EXPECTED_COUNT, len(rows))

    conn = await connect()
    try:
        await replace_rows(conn, "uk_parliamentary_constituencies", INSERT_SQL, rows)
    finally:
        await conn.close()


if __name__ == "__main__":
    run(main)
