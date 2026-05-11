-- Database setup script for PostGIS
-- This script runs automatically when the Docker container starts

-- Enable PostGIS extension (requires PostGIS to be installed)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create a sample table for geographical data
CREATE TABLE IF NOT EXISTS geo_data (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    geom GEOMETRY(Geometry, 4326) NOT NULL,  -- WGS84 coordinate system
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create spatial index for better query performance
CREATE INDEX IF NOT EXISTS idx_geo_data_geom ON geo_data USING GIST (geom);

-- Create index on category for filtering
CREATE INDEX IF NOT EXISTS idx_geo_data_category ON geo_data (category);

-- Insert some sample data (only if table is empty)
INSERT INTO geo_data (name, description, category, geom)
SELECT * FROM (VALUES
    ('New York City', 'Major city in USA', 'city', ST_GeomFromText('POINT(-74.0060 40.7128)', 4326)),
    ('London', 'Capital of UK', 'city', ST_GeomFromText('POINT(-0.1276 51.5074)', 4326)),
    ('Tokyo', 'Capital of Japan', 'city', ST_GeomFromText('POINT(139.6917 35.6895)', 4326)),
    ('Paris', 'Capital of France', 'city', ST_GeomFromText('POINT(2.3522 48.8566)', 4326)),
    ('Central Park Area', 'Large public park in NYC', 'park', 
     ST_GeomFromText('POLYGON((-73.9819 40.7681, -73.9580 40.8006, -73.9493 40.7969, -73.9732 40.7644, -73.9819 40.7681))', 4326))
) AS v(name, description, category, geom)
WHERE NOT EXISTS (SELECT 1 FROM geo_data);

-- Create a view for easy GeoJSON export (optional)
CREATE OR REPLACE VIEW geo_data_geojson AS
SELECT 
    row_to_json(feature) as geojson
FROM (
    SELECT 
        'Feature' as type,
        ST_AsGeoJSON(t.geom)::json as geometry,
        json_build_object(
            'id', t.id,
            'name', t.name,
            'description', t.description,
            'category', t.category
        ) as properties
    FROM geo_data as t
    WHERE t.geom IS NOT NULL
) as feature;
