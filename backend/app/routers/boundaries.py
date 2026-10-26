from fastapi import APIRouter

from app.db import Conn
from app.geojson import GeoJSONResponse, fetch_feature_collection
from app.queries import boundaries as q
from app.schemas import AdminArea

router = APIRouter(prefix="/api", tags=["admin boundaries"])


@router.get("/counties", response_class=GeoJSONResponse)
async def get_counties(conn: Conn):
    """Up to 300 administrative subdivisions, simplified to ~50 m."""
    return await fetch_feature_collection(conn, q.COUNTY_FEATURES)


@router.get("/constituency", response_model=AdminArea, response_model_exclude_none=True)
async def get_admin_area_at(conn: Conn, lat: float, lon: float):
    """The county/borough/constituency-type admin area containing a point (basic_bounds)."""
    row = await conn.fetchrow(q.ADMIN_AREA_AT_POINT, lon, lat)
    if row is None:
        return AdminArea(found=False)
    return AdminArea(found=True, constituency=row["constituency_name"], type=row["type_2"])
