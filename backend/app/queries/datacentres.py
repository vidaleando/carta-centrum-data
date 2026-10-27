"""Data centre queries (osm_data_centers, loaded by importers/osm_datacentres.py)."""

# $1: max number of features
DATACENTRE_FEATURES = """
    SELECT
        'Feature' AS type,
        ST_AsGeoJSON(t.geom, 6)::json AS geometry,
        json_build_object(
            'id', t.osm_id,
            'name', t.name,
            'operator', t.operator,
            'source', t.source
        ) AS properties
    FROM public.osm_data_centers AS t
    WHERE t.geom IS NOT NULL
    ORDER BY t.id
    LIMIT $1
"""
