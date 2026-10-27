from fastapi import APIRouter, Query

from app.db import Conn
from app.geojson import CACHE_LAYER, GeoJSONResponse, fetch_feature_collection
from app.queries import constituencies as q
from app.schemas import ConstituencyMP, ConstituencyMPFound, ConstituencyMPNotFound

router = APIRouter(prefix="/api", tags=["constituencies"])

NOT_IN_CONSTITUENCY = (
    "Location is not within a valid UK parliamentary constituency "
    "(e.g., offshore or international waters)."
)


@router.get("/constituency-mp", response_model=ConstituencyMP)
async def get_constituency_mp(
    conn: Conn,
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """The parliamentary constituency (ONS 2024 boundaries) and MP for a point."""
    row = await conn.fetchrow(q.CONSTITUENCY_MP_AT_POINT, lon, lat)
    if row is None:
        return ConstituencyMPNotFound(message=NOT_IN_CONSTITUENCY)
    return ConstituencyMPFound(
        constituency=row["constituency_name"],
        mp_name=row["mp_name"] or "MP Data Unavailable",
        party=row["party"] or "Unknown",
        current_position=row["current_position"],
        source="Local DB (ONS 2024 Boundaries)",
    )


@router.get("/constituency/{name}", response_class=GeoJSONResponse)
async def get_constituency_by_name(conn: Conn, name: str):
    """A single constituency boundary by name (case-insensitive), simplified to ~100 m."""
    return await fetch_feature_collection(conn, q.CONSTITUENCY_BY_NAME_FEATURES, name, headers=CACHE_LAYER)


@router.get("/parliamentary-boundaries", response_class=GeoJSONResponse)
async def get_parliamentary_boundaries(conn: Conn):
    """All constituency boundaries, simplified to ~50 m."""
    return await fetch_feature_collection(conn, q.ALL_CONSTITUENCY_FEATURES, headers=CACHE_LAYER)
