"""
FastAPI backend for serving GeoJSON data from PostGIS database.
"""
import os
import json
import httpx   

from typing import Optional
from contextlib import asynccontextmanager
from urllib.parse import urlparse


from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# --- FIX: Parse DATABASE_URL correctly ---
database_url = os.getenv("DATABASE_URL")

if database_url:
    # Parse the URL: postgresql://user:pass@host:port/dbname
    parsed = urlparse(database_url)
    DB_CONFIG = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": parsed.username or "postgres",
        "password": parsed.password or "postgres",
        "database": parsed.path.lstrip("/") or "pwa_map_db",
    }
else:
    # Fallback if no DATABASE_URL is set
    DB_CONFIG = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "database": os.getenv("POSTGRES_DB", "pwa_map_db"), # Changed default to pwa_map_db
    }

# Global database pool
db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database connection pool lifecycle."""
    global db_pool
    print(f"Attempting to connect to DB with config: {DB_CONFIG}") # Debug log
    try:
        db_pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)
        print("✅ Database pool created successfully")
        
        # Verify table exists
        async with db_pool.acquire() as conn:
            count = await conn.fetchval("SELECT count(*) FROM public.basic_bounds")
            print(f"✅ Found {count} rows in basic_bounds table")
            
    except Exception as e:
        print("❌ Warning: Could not connect to database: {e}")
        print("Running in demo mode with sample data")
        db_pool = None
    yield
    if db_pool:
        await db_pool.close()
        print("Database pool closed")

# Database configuration
# DB_CONFIG = {
#     "host": os.getenv("POSTGRES_HOST", "localhost"),
#     "port": int(os.getenv("POSTGRES_PORT", 5432)),
#     "user": os.getenv("POSTGRES_USER", "postgres"),
#     "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
#     "database": os.getenv("POSTGRES_DB", "gisdb"),
# }

# # Global database pool
# db_pool = None


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Manage database connection pool lifecycle."""
#     global db_pool
#     try:
#         db_pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)
#         print("Database pool created successfully")
#     except Exception as e:
#         print(f"Warning: Could not connect to database: {e}")
#         print("Running in demo mode with sample data")
#         db_pool = None
#     yield
#     if db_pool:
#         await db_pool.close()
#         print("Database pool closed")


app = FastAPI(
    title="Watershed Democracy API",
    description="API for serving geographical data from PostGIS to MapLibre",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # In production, specify your frontend URL
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "PWA Map API is running",
        "endpoints": {
            "geojson": "/api/geojson",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Check database connectivity."""
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return {"status": "unhealthy", "database": f"error: {str(e)}"}
    else:
        return {"status": "demo_mode", "database": "not_connected"}


def get_sample_geojson():
    """Return sample GeoJSON data for demo purposes."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Sample Point 1",
                    "description": "This is a sample point",
                    "category": "point"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-74.0060, 40.7128]  # New York
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name": "Sample Point 2",
                    "description": "Another sample point",
                    "category": "point"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-0.1276, 51.5074]  # London
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name": "Sample Point 3",
                    "description": "Third sample point",
                    "category": "point"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [139.6917, 35.6895]  # Tokyo
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name": "Sample Polygon",
                    "description": "A sample polygon area",
                    "category": "polygon"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [2.3522, 48.8566],  # Paris area
                        [2.3622, 48.8566],
                        [2.3622, 48.8666],
                        [2.3522, 48.8666],
                        [2.3522, 48.8566]
                    ]]
                }
            }
        ]
    }

@app.get("/api/geojson")
async def get_geojson(
    source: Optional[str] = "db",
    table_name: Optional[str] = "basic_bounds",
    limit: Optional[int] = 1000
):
    # 1. Force sample data if requested (Highest Priority)
    if source == "sample":
        print("📝 Returning sample data as requested.")
        return get_sample_geojson()
    
    # 2. Check database connection
    if not db_pool:
        print("⚠️ Database pool not initialized.")
        return get_sample_geojson()
    
    try:
        async with db_pool.acquire() as conn:
            # 3. Select the correct query based on table_name
            if table_name == "osm_data_centers":
                print(f"🗺️ Fetching data from table: {table_name}")
                query = """
                    SELECT 
                        row_to_json(feature) as geojson
                    FROM (
                        SELECT 
                            'Feature' as type,
                            ST_AsGeoJSON(t.geom)::json as geometry, 
                            json_build_object(
                                'id', t.osm_id,
                                'name', t.name,
                                'operator', t.operator,
                                'source', t.source
                            ) as properties
                        FROM public.osm_data_centers as t
                        WHERE t.geom IS NOT NULL
                    ) as feature
                """
            else:
                # Default to basic_bounds for any other table name (or if missing)
                print(f"🗺️ Fetching data from default table: basic_bounds")
                query = """
                    SELECT 
                        row_to_json(feature) as geojson
                    FROM (
                        SELECT 
                            'Feature' as type,
                            ST_AsGeoJSON(t.wkb_geometry)::json as geometry, 
                            json_build_object(
                                'id', t.ogc_fid,       
                                'name', t.name_0,      
                                'iso', t.iso,
                                'admin_level', t.type_2
                            ) as properties
                        FROM public.basic_bounds as t
                        WHERE t.wkb_geometry IS NOT NULL
                    ) as feature
                """
            
            # 4. Execute the selected query
            rows = await conn.fetch(query)
            
            if not rows:
                print(f"⚠️ No rows found in table {table_name}.")
                # Optionally return sample data or empty collection
                return {"type": "FeatureCollection", "features": []}
            
            # 5. Parse JSON strings into objects
            features = []
            for row in rows:
                geojson_val = row['geojson']
                if isinstance(geojson_val, str):
                    features.append(json.loads(geojson_val))
                else:
                    features.append(geojson_val)
            
            # Apply limit
            features = features[:limit]
            
            print(f"✅ Successfully fetched {len(features)} features from {table_name}.")
            
            return {
                "type": "FeatureCollection",
                "features": features
            }
    
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    
@app.post("/api/geojson")
async def create_geojson_feature(feature: dict):
    """
    Create a new geographical feature in the database.
    
    This is a placeholder - implement based on your specific schema.
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    try:
        async with db_pool.acquire() as conn:
            # Extract geometry and properties
            geometry = feature.get('geometry', {})
            properties = feature.get('properties', {})
            
            # Convert GeoJSON geometry to WKT for PostGIS
            geom_type = geometry.get('type', '').upper()
            coords = geometry.get('coordinates', [])
            
            # This is a simplified example - you'll need to adapt
            # based on your actual database schema
            query = """
                INSERT INTO geo_data (geom, name, description, category)
                VALUES (ST_GeomFromGeoJSON($1), $2, $3, $4)
                RETURNING id
            """
            
            geojson_geom = json.dumps(geometry)
            name = properties.get('name', 'Unnamed')
            description = properties.get('description', '')
            category = properties.get('category', 'general')
            
            result = await conn.fetchrow(
                query,
                geojson_geom,
                name,
                description,
                category
            )
            
            return {
                "id": result['id'],
                "message": "Feature created successfully"
            }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

@app.get("/api/osm/{layer_type}")
async def get_osm_data(layer_type: str, bounds: str = "49.0,-10.0,61.0,2.0"):
    """
    Fetch data from OpenStreetMap via Overpass API.
    """
    # Define tags for different layers
    # Data centers are rare, so we include related infrastructure tags
    tag_map = {
        "data_center": [
           # 1. Explicit Data Center tags
            {"man_made": "data_center"},
            {"building": "data_center"},
            {"telecom": "data_center"},
            
            # 2. Telecommunications Infrastructure (High probability)
            {"telecom": "exchange"},
            {"telecom": "connection_point"},
            #{"office": "telecommunication"},
            #{"building": "telephone_exchange"},
            
            # 3. Technical/Server Rooms (Medium probability)
            {"building": "server_room"},
            {"building": "technical"},
            {"building": "data_hall"},
            
            # 4. Industrial/Commercial (Low probability, high volume - use with caution)
            # We filter these later by name if possible, but Overpass can't do complex text filtering efficiently on all nodes
            # {"landuse": "industrial"}, 
            # {"building": "warehouse"},
            # {"building": "commercial"}
        ],
        "pub": [{"amenity": "pub"}],
        "school": [{"amenity": "school"}],
        "hospital": [{"amenity": "hospital"}],
        "windmill": [{"man_made": "windmill"}, {"historic": "windmill"}]
    }

    if layer_type not in tag_map:
        # Default to searching by name if specific tag not found
        # This allows flexible queries like ?layer_type=restaurant
        tag_map[layer_type] = [{"amenity": layer_type}]

    target_tags = tag_map[layer_type]
    
    # Construct Overpass QL query parts
    # We build a union of queries for each possible tag set
    query_parts = []
    
    for tags in target_tags:
        # Build filter string e.g. ["man_made"="data_center"]
        filter_str = "".join([f'["{k}"="{v}"]' for k, v in tags.items()])
        
        # Add node, way, and relation queries for this tag set
        query_parts.append(f"node{filter_str}({bounds});")
        query_parts.append(f"way{filter_str}({bounds});")
        # Relations are complex, often skipped for simple point maps, but included here
        query_parts.append(f"relation{filter_str}({bounds});")
    
    # SPECIAL HACK FOR DATA CENTERS: 
    # Also try to find nodes/ways with specific keywords in their NAME or OPERATOR tag
    # This catches "Equinix LD8" even if it's just tagged as building=warehouse
    # if layer_type == "data_center":
    #     keywords = ["Data Center", "Colocation", "Equinix", "Digital Realty", "Interxion", "NTT", "Telehouse", "Global Switch", "CyrusOne", "Iron Mountain", "AWS", "Google", "Microsoft Azure", "Oracle Cloud"]
        
    #     # Note: Overpass regex is powerful but slow. We do a simple 'name~"keyword"' for top providers
    #     # We limit this to 'node' and 'way' to prevent timeout
    #     for kw in keywords:
    #         # Escape quotes in keyword if any
    #         safe_kw = kw.replace('"', '\\"')
    #         query_parts.append(f'node["name"~"{safe_kw}",i]({bounds});')
    #         query_parts.append(f'way["name"~"{safe_kw}",i]({bounds});')
    #         query_parts.append(f'node["operator"~"{safe_kw}",i]({bounds});')
    #         query_parts.append(f'way["operator"~"{safe_kw}",i]({bounds});')

    if not query_parts:
        raise HTTPException(status_code=400, detail="No valid tags configured for this layer")

    # Join all parts into a single union query
    # Timeout increased to 60s for large areas or complex polygons
    overpass_query = f"""
        [out:json][timeout:60];
        (
            {"".join(query_parts)}
        );
        out geom;
    """

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": overpass_query},
                headers={
                    "Accept-Encoding": "gzip, deflate",
                    "User-Agent": "curl/7.88.0",
                },
                timeout=65.0
            )

            print("Status:", response.status_code)
            print("Body:", response.text[:500])
            
            if response.status_code == 400:
                print(f"Overpass Query Error: {overpass_query}")
                print(f"Response: {response.text}")
                raise HTTPException(status_code=400, detail=f"Invalid Overpass Query: {response.text[:200]}")
            
            response.raise_for_status()
            osm_data = response.json()

        features = []
        elements = osm_data.get("elements", [])
        
        print(f"Found {len(elements)} elements for {layer_type}")

        for element in elements:
            if "type" not in element:
                continue
            
            tags = element.get("tags", {})
            
            # Skip if it doesn't have a name and isn't a critical infrastructure type
            # (Optional: Remove this filter if you want unnamed features)
            # if "name" not in tags and layer_type != "data_center":
            #     continue

            feature = {
                "type": "Feature",
                "properties": {
                    "id": element.get("id"),
                    "name": tags.get("name", tags.get("operator", "Unnamed")),
                    "source": "OpenStreetMap",
                    "layer": layer_type,
                    **tags
                }
            }

            if element["type"] == "node":
                feature["geometry"] = {
                    "type": "Point",
                    "coordinates": [element["lon"], element["lat"]]
                }
            elif element["type"] == "way":
                coords = [[n["lon"], n["lat"]] for n in element.get("geometry", [])]
                if len(coords) < 2: 
                    continue
                
                # Close polygon if first and last match
                if coords[0] == coords[-1]:
                    feature["geometry"] = {"type": "Polygon", "coordinates": [coords]}
                else:
                    feature["geometry"] = {"type": "LineString", "coordinates": coords}
            
            elif element["type"] == "relation":
                # Skipping complex relations for this simple example
                continue

            features.append(feature)

        return {"type": "FeatureCollection", "features": features}

    except httpx.HTTPStatusError as e:
        print(f"HTTP Error from Overpass: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Overpass API error: {e.response.status_code}")
    except Exception as e:
        print(f"General Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch OSM data: {str(e)}")

@app.get("/api/constituency-mp")
async def get_constituency_mp(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude")
):
    """
    Find the constituency and MP for a given lat/lon using the new ONS boundaries table.
    """
    if not db_pool:
        return {"found": False, "error": "Database not connected"}
    
    try:
        async with db_pool.acquire() as conn:
            # Query the new uk_parliamentary_constituencies table
            # We join directly on the name which should now match perfectly
            query = """
                SELECT 
                    c.name as constituency_name,
                    m.name as mp_name,
                    m.party,
                    m.current_position,
                    m.office_json
                FROM public.uk_parliamentary_constituencies as c
                LEFT JOIN public.uk_mps as m 
                    ON LOWER(c.name) = LOWER(m.constituency)
                WHERE ST_Contains(
                    c.geometry, 
                    ST_SetSRID(ST_MakePoint($1, $2), 4326)
                )
                LIMIT 1
            """
            
            row = await conn.fetchrow(query, lon, lat)
            
            if row:
                mp_name = row['mp_name'] or "MP Data Unavailable"
                party = row['party'] or "Unknown"

                return {
                    "found": True,
                    "constituency": row['constituency_name'],
                    "mp_name": mp_name,
                    "party": party,
                    "current_position": row['current_position'],
                    "source": "Local DB (ONS 2024 Boundaries)"
                }
            else:
                return {
                    "found": False, 
                    "message": "Location is not within a valid UK parliamentary constituency (e.g., offshore or international waters)."
                }
                
    except Exception as e:
        print(f"❌ Error fetching constituency MP: {e}")
        return {"found": False, "error": str(e)}

@app.get("/api/parliamentary-constituencies")
async def get_parliamentary_constituencies():
    """
    Fetch all parliamentary constituency boundaries for visualization.
    Uses simplification to keep the payload size manageable.
    """
    if not db_pool:
        return {"type": "FeatureCollection", "features": []}
    
    try:
        async with db_pool.acquire() as conn:
            # Simplify geometry (0.0005 ~ 50m) to reduce data transfer
            query = """
                SELECT 
                    row_to_json(feature) as geojson
                FROM (
                    SELECT 
                        'Feature' as type,
                        ST_AsGeoJSON(ST_SimplifyPreserveTopology(c.geometry, 0.0005))::json as geometry,
                        json_build_object(
                            'name', c.name,
                            'code', c.ons_code,
                            'type', 'Parliamentary Constituency'
                        ) as properties
                    FROM public.uk_parliamentary_constituencies as c
                ) as feature
            """
            
            rows = await conn.fetch(query)
            
            features = []
            for row in rows:
                val = row['geojson']
                features.append(json.loads(val) if isinstance(val, str) else val)
            
            print(f"✅ Fetched {len(features)} parliamentary constituencies.")
            return {"type": "FeatureCollection", "features": features}
    
    except Exception as e:
        print(f"❌ Error fetching constituencies: {e}")
        return {"type": "FeatureCollection", "features": []}
                
@app.get("/api/constituency")
async def get_constituency_by_location(lat: float, lon: float):
    """
    Find the constituency name and ID for a given lat/lon using PostGIS.
    """
    if not db_pool:
        return {"error": "Database not connected"}
    
    try:
        async with db_pool.acquire() as conn:
            # ST_Contains checks if the point is inside the polygon
            # We use ST_MakePoint(lon, lat) - note: X (lon) comes first!
            query = """
                SELECT 
                    ogc_fid,
                    name_2 as constituency_name,
                    type_2
                FROM public.basic_bounds
                WHERE ST_Contains(
                    wkb_geometry, 
                    ST_SetSRID(ST_MakePoint($1, $2), 4326)
                )
                AND (type_2 ILIKE '%constituency%' OR type_2 ILIKE '%county%' OR type_2 ILIKE '%borough%')
                LIMIT 1
            """
            
            row = await conn.fetchrow(query, lon, lat)
            
            if row:
                return {
                    "found": True,
                    "constituency": row['constituency_name'],
                    "type": row['type_2']
                }
            else:
                return {"found": False}
                
    except Exception as e:
        print(f"Error fetching constituency: {e}")
        return {"error": str(e)}
    
@app.get("/api/counties")
async def get_counties():
    if not db_pool:
        return {"type": "FeatureCollection", "features": []}
    
    try:
        async with db_pool.acquire() as conn:
            # Fetch all subdivisions available in basic_bounds
            # We rely on name_2 and type_2 being present to identify a division
            query = """
                SELECT 
                    row_to_json(feature) as geojson
                FROM (
                    SELECT 
                        'Feature' as type,
                        -- Simplify geometry heavily for performance (0.0005 ~ 50m)
                        ST_AsGeoJSON(ST_SimplifyPreserveTopology(t.wkb_geometry, 0.0005))::json as geometry, 
                        json_build_object(
                            'id', t.ogc_fid,
                            'name', t.name_2, 
                            'type', t.type_2,
                            'parent_name', t.name_1
                        ) as properties
                    FROM public.basic_bounds as t
                    WHERE t.name_2 IS NOT NULL 
                      AND t.type_2 IS NOT NULL
                      AND t.wkb_geometry IS NOT NULL
                    LIMIT 300
                ) as feature
            """
            
            rows = await conn.fetch(query)
            
            features = []
            for row in rows:
                val = row['geojson']
                if val:
                    features.append(json.loads(val) if isinstance(val, str) else val)
            
            print(f"✅ Fetched {len(features)} simplified county/division boundaries.")
            return {"type": "FeatureCollection", "features": features}
    
    except Exception as e:
        print(f"❌ Error fetching counties: {str(e)}")
        # Return empty GeoJSON instead of raising HTTPException to prevent frontend crash
        return {"type": "FeatureCollection", "features": []}
    
@app.get("/api/parliamentary-boundaries")
async def get_parliamentary_boundaries():
    """
    Fetch simplified parliamentary constituency boundaries for map rendering.
    Uses ST_SimplifyPreserveTopology to reduce data size significantly.
    """
    if not db_pool:
        return {"type": "FeatureCollection", "features": []}
    
    try:
        async with db_pool.acquire() as conn:
            # Tolerance 0.0005 is approx 50 meters. 
            # This reduces file size from ~5MB to ~200KB usually.
            query = """
                SELECT 
                    row_to_json(feature) as geojson
                FROM (
                    SELECT 
                        'Feature' as type,
                        ST_AsGeoJSON(
                            ST_SimplifyPreserveTopology(c.geometry, 0.0005)
                        )::json as geometry,
                        json_build_object(
                            'name', c.name,
                            'code', c.ons_code
                        ) as properties
                    FROM public.uk_parliamentary_constituencies as c
                ) as feature
            """
            
            rows = await conn.fetch(query)
            
            features = []
            for row in rows:
                val = row['geojson']
                # Handle potential string vs object return from DB
                features.append(json.loads(val) if isinstance(val, str) else val)
            
            print(f"✅ Fetched {len(features)} simplified constituencies.")
            return {"type": "FeatureCollection", "features": features}
            
    except Exception as e:
        print(f"Error fetching boundaries: {e}")
        return {"type": "FeatureCollection", "features": []}
    
@app.get("/api/constituency/{name}")
async def get_constituency_by_name(name: str):
    """Fetch a single constituency geometry by name."""
    if not db_pool:
        return {"type": "FeatureCollection", "features": []}
    
    try:
        async with db_pool.acquire() as conn:
            # Simplify heavily for fast rendering (0.001 ~ 100m)
            query = """
                SELECT 
                    row_to_json(feature) as geojson
                FROM (
                    SELECT 
                        'Feature' as type,
                        ST_AsGeoJSON(ST_SimplifyPreserveTopology(c.geometry, 0.001))::json as geometry,
                        json_build_object(
                            'name', c.name,
                            'ons_code', c.ons_code
                        ) as properties
                    FROM public.uk_parliamentary_constituencies as c
                    WHERE LOWER(c.name) = LOWER($1)
                ) as feature
            """
            
            row = await conn.fetchrow(query, name)
            
            if row and row['geojson']:
                feature = row['geojson']
                if isinstance(feature, str):
                    feature = json.loads(feature)
                return {"type": "FeatureCollection", "features": [feature]}
            else:
                return {"type": "FeatureCollection", "features": []}
                
    except Exception as e:
        print(f"Error fetching constituency: {e}")
        return {"type": "FeatureCollection", "features": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
