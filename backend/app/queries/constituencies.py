"""Parliamentary constituency and MP queries (uk_parliamentary_constituencies, uk_mps)."""

# $1: lon, $2: lat. MPs are matched to constituencies by lower-cased name.
CONSTITUENCY_MP_AT_POINT = """
    SELECT
        c.name AS constituency_name,
        m.name AS mp_name,
        m.party,
        m.current_position
    FROM public.uk_parliamentary_constituencies AS c
    LEFT JOIN public.uk_mps AS m
        ON LOWER(c.name) = LOWER(m.constituency)
    WHERE ST_Contains(c.geometry, ST_SetSRID(ST_MakePoint($1, $2), 4326))
    LIMIT 1
"""

# $1: constituency name (case-insensitive). Simplified to ~100 m for fast rendering.
CONSTITUENCY_BY_NAME_FEATURES = """
    SELECT
        'Feature' AS type,
        ST_AsGeoJSON(ST_SimplifyPreserveTopology(c.geometry, 0.001))::json AS geometry,
        json_build_object(
            'name', c.name,
            'ons_code', c.ons_code
        ) AS properties
    FROM public.uk_parliamentary_constituencies AS c
    WHERE LOWER(c.name) = LOWER($1)
    LIMIT 1
"""

# All constituencies, simplified to ~50 m to keep the payload manageable.
ALL_CONSTITUENCY_FEATURES = """
    SELECT
        'Feature' AS type,
        ST_AsGeoJSON(ST_SimplifyPreserveTopology(c.geometry, 0.0005))::json AS geometry,
        json_build_object(
            'name', c.name,
            'code', c.ons_code
        ) AS properties
    FROM public.uk_parliamentary_constituencies AS c
    ORDER BY c.id
"""
