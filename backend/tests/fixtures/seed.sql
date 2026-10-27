-- Small, fictional fixture data for API tests. Assumes migrations have run.
-- Two adjacent square "constituencies" in central London, one MP per
-- constituency, three data centres (one in each constituency, one outside both).

DELETE FROM public.osm_data_centers;
DELETE FROM public.uk_mps;
DELETE FROM public.uk_parliamentary_constituencies;

INSERT INTO public.uk_parliamentary_constituencies (ons_code, name, name_welsh, geometry) VALUES
    ('E14000001', 'Riverside North', '',
     ST_Multi(ST_GeomFromText('POLYGON((-0.20 51.48, -0.05 51.48, -0.05 51.53, -0.20 51.53, -0.20 51.48))', 4326))),
    ('E14000002', 'Hillside South', '',
     ST_Multi(ST_GeomFromText('POLYGON((-0.20 51.53, -0.05 51.53, -0.05 51.56, -0.20 51.56, -0.20 51.53))', 4326)));

-- Constituency name stored in a different case to exercise the case-insensitive join.
INSERT INTO public.uk_mps (member_id, person_id, name, party, constituency, current_position, office_json) VALUES
    ('1001', 2001, 'Alex Example', 'Labour', 'riverside north', NULL, NULL),
    ('1002', 2002, 'Sam Sample', 'Conservative', 'Hillside South', 'Shadow Minister',
     '[{"position": "Shadow Minister"}]'::jsonb);

INSERT INTO public.osm_data_centers (osm_id, name, operator, source, geom) VALUES
    ('node/1', 'Alpha DC', 'Alpha Ltd', 'OpenStreetMap', ST_SetSRID(ST_MakePoint(-0.10, 51.50), 4326)),
    ('way/1', 'Beta DC', NULL, 'OpenStreetMap', ST_SetSRID(ST_MakePoint(-0.10, 51.55), 4326)),
    ('node/2', 'Gamma DC', 'Gamma plc', 'OpenStreetMap', ST_SetSRID(ST_MakePoint(-0.60, 51.51), 4326));

DROP TABLE IF EXISTS public.basic_bounds;
CREATE TABLE public.basic_bounds (
    ogc_fid SERIAL PRIMARY KEY,
    iso TEXT,
    name_0 TEXT,
    name_1 TEXT,
    name_2 TEXT,
    type_2 TEXT,
    wkb_geometry GEOMETRY(MultiPolygon, 4326)
);
INSERT INTO public.basic_bounds (iso, name_0, name_1, name_2, type_2, wkb_geometry) VALUES
    ('GBR', 'United Kingdom', 'England', 'Westminster', 'London Borough',
     ST_Multi(ST_GeomFromText('POLYGON((-0.20 51.48, -0.05 51.48, -0.05 51.56, -0.20 51.56, -0.20 51.48))', 4326))),
    ('GBR', 'United Kingdom', 'England', 'Berkshire', 'County',
     ST_Multi(ST_GeomFromText('POLYGON((-0.80 51.40, -0.50 51.40, -0.50 51.60, -0.80 51.60, -0.80 51.40))', 4326))),
    ('GBR', 'United Kingdom', 'England', NULL, NULL,
     ST_Multi(ST_GeomFromText('POLYGON((1.00 52.00, 1.10 52.00, 1.10 52.10, 1.00 52.10, 1.00 52.00))', 4326)));
