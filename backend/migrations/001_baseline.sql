-- Baseline schema: the tables the API reads, matching what the original import
-- scripts created. Everything is IF NOT EXISTS so this is a no-op on databases
-- that were set up by those scripts.
--
-- Not managed here: public.basic_bounds (GADM-style admin boundaries loaded
-- externally with ogr2ogr; columns ogc_fid, wkb_geometry, name_0..2, type_2, iso).

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS public.uk_parliamentary_constituencies (
    id SERIAL PRIMARY KEY,
    ons_code TEXT,
    name TEXT NOT NULL,
    name_welsh TEXT,
    geometry GEOMETRY(MultiPolygon, 4326)
);
CREATE INDEX IF NOT EXISTS idx_uk_constituencies_geom
    ON public.uk_parliamentary_constituencies USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_uk_constituencies_name
    ON public.uk_parliamentary_constituencies (lower(name));

CREATE TABLE IF NOT EXISTS public.uk_mps (
    member_id TEXT PRIMARY KEY,
    person_id INTEGER,
    name TEXT NOT NULL,
    party TEXT,
    constituency TEXT,
    current_position TEXT,
    office_json JSONB,
    email TEXT,
    phone TEXT,
    website TEXT
);
CREATE INDEX IF NOT EXISTS idx_uk_mps_constituency
    ON public.uk_mps (lower(constituency));

CREATE TABLE IF NOT EXISTS public.osm_data_centers (
    id SERIAL PRIMARY KEY,
    osm_id TEXT UNIQUE,
    name TEXT,
    operator TEXT,
    source TEXT,
    geom GEOMETRY(Point, 4326)
);
CREATE INDEX IF NOT EXISTS idx_osm_data_centers_geom
    ON public.osm_data_centers USING GIST (geom);
