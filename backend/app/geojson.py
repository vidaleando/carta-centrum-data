"""Helpers for building GeoJSON FeatureCollections in PostGIS and returning them as-is."""
from typing import Optional

import asyncpg
from fastapi.responses import Response

EMPTY_FEATURE_COLLECTION = '{"type": "FeatureCollection", "features": []}'

# For layers that only change when an importer runs. "private": the API needs a
# signed-in user, so shared caches (e.g. Vercel's CDN) must not store them.
CACHE_LAYER = {"Cache-Control": "private, max-age=3600"}


class GeoJSONResponse(Response):
    """A JSON body that is already serialised (by PostGIS) and passed through untouched."""

    media_type = "application/json"


def feature_collection_sql(features_sql: str) -> str:
    """Wrap a query yielding (type, geometry, properties) rows into one FeatureCollection.

    The result is a single text value, so it can be returned without parsing
    and re-serialising every feature in Python.
    """
    return f"""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', coalesce(json_agg(feature), '[]'::json)
        )::text
        FROM ({features_sql}) AS feature
    """


async def fetch_feature_collection(
    conn: asyncpg.Connection, features_sql: str, *args, headers: Optional[dict] = None
) -> GeoJSONResponse:
    body = await conn.fetchval(feature_collection_sql(features_sql), *args)
    return GeoJSONResponse(body, headers=headers)
