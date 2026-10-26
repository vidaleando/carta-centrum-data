from typing import Literal

from fastapi import APIRouter, Query, Request

from app.db import Conn, connection
from app.geojson import GeoJSONResponse, fetch_feature_collection
from app.queries import datacentres as q
from app.sample_data import SAMPLE_FEATURE_COLLECTION

router = APIRouter(prefix="/api", tags=["data centres"])

Limit = Query(1000, ge=1, le=10000, description="Maximum number of features")


@router.get("/datacentres", response_class=GeoJSONResponse)
async def get_datacentres(conn: Conn, limit: int = Limit):
    """UK data centres and related telecom infrastructure from OpenStreetMap."""
    return await fetch_feature_collection(conn, q.DATACENTRE_FEATURES, limit)


@router.get("/geojson", deprecated=True)
async def get_geojson_legacy(
    request: Request,
    source: Literal["db", "sample"] = "db",
    table_name: Literal["osm_data_centers"] = "osm_data_centers",
    limit: int = Limit,
):
    """Legacy endpoint. `?source=sample` returns static sample data without touching
    the database (the frontend loads it on startup); otherwise same as /api/datacentres.
    """
    if source == "sample":
        return SAMPLE_FEATURE_COLLECTION
    # Connection acquired here, not as a dependency, so ?source=sample works without a database.
    async with connection(request) as conn:
        return await fetch_feature_collection(conn, q.DATACENTRE_FEATURES, limit)
