"""Import current MPs from the TheyWorkForYou API.

Usage (from backend/):  python -m importers.mps
Requires THEYWORKFORYOU_KEY.
"""
import json
import logging

import httpx

from app.config import get_settings
from importers.common import USER_AGENT, ImportFailed, connect, replace_rows, run

log = logging.getLogger("importers.mps")

API_URL = "https://www.theyworkforyou.com/api/getMPs"

INSERT_SQL = """
    INSERT INTO public.uk_mps
        (member_id, person_id, name, party, constituency, current_position, office_json)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
"""


async def fetch_mps(api_key: str) -> list[dict]:
    log.info("Fetching MPs from TheyWorkForYou")
    async with httpx.AsyncClient(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        resp = await client.get(API_URL, params={"key": api_key, "output": "json"})
    if resp.status_code != 200:
        raise ImportFailed(f"TheyWorkForYou returned HTTP {resp.status_code}")
    data = resp.json()
    if isinstance(data, dict) and "error" in data:
        raise ImportFailed(f"TheyWorkForYou error: {data['error']}")
    if not isinstance(data, list):
        raise ImportFailed(f"Unexpected response type: {type(data).__name__}")
    return data


def parse_mps(mps: list[dict]) -> list[tuple]:
    """TheyWorkForYou getMPs records -> uk_mps rows. Records without a member_id are skipped."""
    rows, seen = [], set()
    for mp in mps:
        member_id = mp.get("member_id")
        if member_id is None or str(member_id) in seen:
            log.warning("Skipping MP record without a unique member_id: %s", mp.get("name"))
            continue
        seen.add(str(member_id))

        offices = mp.get("office")
        has_offices = isinstance(offices, list) and offices
        rows.append((
            str(member_id),
            int(mp.get("person_id") or 0),
            mp.get("name") or "Unknown",
            mp.get("party") or "Unknown",
            mp.get("constituency") or "Unknown",
            # The first listed office is treated as the current position.
            offices[0].get("position", "MP") if has_offices else None,
            json.dumps(offices) if has_offices else None,
        ))
    return rows


async def main() -> None:
    api_key = get_settings().theyworkforyou_key
    if not api_key:
        raise ImportFailed("THEYWORKFORYOU_KEY is not set")
    rows = parse_mps(await fetch_mps(api_key))
    log.info("Parsed %d MPs", len(rows))

    conn = await connect()
    try:
        await replace_rows(conn, "uk_mps", INSERT_SQL, rows)
    finally:
        await conn.close()


if __name__ == "__main__":
    run(main)
