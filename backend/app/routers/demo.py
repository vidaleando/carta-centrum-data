"""DEMO_MODE=true: the same API surface backed by static data, with no database.

Included instead of the database-backed routers, so those never need a demo branch.
Keep the paths here in sync with health, datacentres, constituencies and boundaries.
"""
from fastapi import APIRouter

from app.geojson import EMPTY_FEATURE_COLLECTION, GeoJSONResponse
from app.sample_data import SAMPLE_FEATURE_COLLECTION
from app.schemas import AdminArea, ConstituencyMPNotFound, Health

router = APIRouter(tags=["demo"])

DEMO_MESSAGE = "Demo mode: no database connected."


@router.get("/health", response_model=Health)
async def health():
    return Health(status="demo_mode", database="not_connected")


@router.get("/api/datacentres")
@router.get("/api/geojson", deprecated=True)
async def datacentres():
    return SAMPLE_FEATURE_COLLECTION


@router.get("/api/constituency-mp", response_model=ConstituencyMPNotFound)
async def constituency_mp(lat: float, lon: float):
    return ConstituencyMPNotFound(message=DEMO_MESSAGE)


@router.get("/api/constituency/{name}", response_class=GeoJSONResponse)
@router.get("/api/parliamentary-boundaries", response_class=GeoJSONResponse)
@router.get("/api/counties", response_class=GeoJSONResponse)
async def empty_layer():
    return GeoJSONResponse(EMPTY_FEATURE_COLLECTION)


@router.get("/api/constituency", response_model=AdminArea, response_model_exclude_none=True)
async def admin_area(lat: float, lon: float):
    return AdminArea(found=False)
