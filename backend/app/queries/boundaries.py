"""Administrative boundary queries (basic_bounds, loaded externally with ogr2ogr)."""

# Up to 300 named subdivisions, simplified to ~50 m.
COUNTY_FEATURES = """
    SELECT
        'Feature' AS type,
        ST_AsGeoJSON(ST_SimplifyPreserveTopology(t.wkb_geometry, 0.0005), 6)::json AS geometry,
        json_build_object(
            'id', t.ogc_fid,
            'name', t.name_2,
            'type', t.type_2,
            'parent_name', t.name_1
        ) AS properties
    FROM public.basic_bounds AS t
    WHERE t.name_2 IS NOT NULL
      AND t.type_2 IS NOT NULL
      AND t.wkb_geometry IS NOT NULL
    ORDER BY t.ogc_fid
    LIMIT 300
"""

# $1: lon, $2: lat
ADMIN_AREA_AT_POINT = """
    SELECT
        name_2 AS constituency_name,
        type_2
    FROM public.basic_bounds
    WHERE ST_Contains(wkb_geometry, ST_SetSRID(ST_MakePoint($1, $2), 4326))
      AND (type_2 ILIKE '%constituency%' OR type_2 ILIKE '%county%' OR type_2 ILIKE '%borough%')
    LIMIT 1
"""
