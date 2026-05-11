"""
FastAPI backend for serving GeoJSON data from PostGIS database.
"""
import os
import json
from typing import Optional
from contextlib import asynccontextmanager
from urllib.parse import urlparse


from fastapi import FastAPI, HTTPException
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
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    source: Optional[str] = "db",  # New parameter: 'db' or 'sample'
    table_name: Optional[str] = "basic_bounds",
    limit: Optional[int] = 1000
):
    # Force sample data if requested
    if source == "sample":
        print("📝 Returning sample data as requested.")
        return get_sample_geojson()
    
    if not db_pool:
        print("⚠️ Database pool not initialized.")
        return get_sample_geojson()
    
    try:
        async with db_pool.acquire() as conn:
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
            
            rows = await conn.fetch(query)
            
            if not rows:
                print("⚠️ No rows found in database.")
                return get_sample_geojson()
            
            # CRITICAL FIX: Parse JSON strings into objects
            features = []
            for row in rows:
                geojson_val = row['geojson']
                if isinstance(geojson_val, str):
                    features.append(json.loads(geojson_val))
                else:
                    features.append(geojson_val)
            
            # Apply limit in Python
            features = features[:limit]
            
            print(f"✅ Successfully fetched {len(features)} features from DB.")
            
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

# @app.get("/api/osm/{layer_type}")
# async def get_osm_data(layer_type: str, bounds: str = "-10.0,49.0,2.0,61.0"):
    """
    Fetch data from OpenStreetMap via Overpass API.
    bounds default is roughly UK: min_lon,min_lat,max_lon,max_lat
    """
    
    # Define tags for different layer types
    tag_map = {
        "school": {"amenity": "school"},
        "hospital": {"amenity": "hospital"},
        "data_center": {
            "man_made": "data_center", 
            "building": "data_center",
            "office": "data_center"
        },
        # Fallback for generic search if needed
    }

    if layer_type not in tag_map:
        # Try to support direct tag queries like "man_made=data_center" if passed creatively
        # But for now, strict map
        raise HTTPException(status_code=400, detail=f"Unknown layer type: {layer_type}. Available: {list(tag_map.keys())}")

    tags = tag_map[layer_type]
    
    # Construct Overpass QL query
    # We create a union of queries for each potential tag match
    sub_queries = []
    for k, v in tags.items():
        sub_queries.append(f'node["{k}"="{v}"]({bounds});')
        sub_queries.append(f'way["{k}"="{v}"]({bounds});')
        sub_queries.append(f'relation["{k}"="{v}"]({bounds});')

    query = f"""
        [out:json][timeout:25];
        (
          {''.join(sub_queries)}
        );
        out geom;
    """

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data=query,
                timeout=30.0
            )
            response.raise_for_status()
            osm_data = response.json()

        features = []
        for element in osm_data.get("elements", []):
            if "type" not in element:
                continue
            
            props = element.get("tags", {})
            feature = {
                "type": "Feature",
                "properties": {
                    "id": element.get("id"),
                    "name": props.get("name", props.get("operator", "Unnamed Data Center")),
                    "source": "OpenStreetMap",
                    "layer": layer_type,
                    **props
                }
            }

            if element["type"] == "node":
                feature["geometry"] = {
                    "type": "Point",
                    "coordinates": [element["lon"], element["lat"]]
                }
            elif element["type"] == "way":
                coords = [[n["lon"], n["lat"]] for n in element.get("geometry", [])]
                if len(coords) < 2: continue
                
                if coords[0] == coords[-1]:
                    feature["geometry"] = {"type": "Polygon", "coordinates": [coords]}
                else:
                    feature["geometry"] = {"type": "LineString", "coordinates": coords}
            elif element["type"] == "relation":
                continue # Skip complex relations for simplicity

            features.append(feature)

        return {"type": "FeatureCollection", "features": features}

    except Exception as e:
        print(f"Overpass error: {e}")
        raise HTTPException(status_code=500, detail=f"Overpass API error: {str(e)}")


# import httpx
# from urllib.parse import quote

# @app.get("/api/osm/{layer_type}")
# async def get_osm_data(layer_type: str, bounds: str = "-10.0,49.0,2.0,61.0"):
    """
    Fetch data from OpenStreetMap via Overpass API with robust error handling.
    """
    # Map friendly names to OSM tags
    # For data centers, we try multiple possible tags as OSM tagging is inconsistent
    tag_map = {
        "data_center": [
            {"man_made": "data_center"},
            {"building": "data_center"},
            {"office": "data_center"},
            {"telecom": "data_center"}
        ],
        "school": [{"amenity": "school"}],
        "hospital": [{"amenity": "hospital"}],
        "pub": [{"amenity": "pub"}],
        "windmill": [{"man_made": "windmill"}], # Good for testing!
        "cafe": [{"amenity": "cafe"}]
    }

    if layer_type not in tag_map:
        raise HTTPException(status_code=400, detail=f"Unknown layer type: {layer_type}. Try: {list(tag_map.keys())}")

    tags_list = tag_map[layer_type]
    
    # Build the query parts for each tag option
    query_parts = []
    for tags in tags_list:
        # Construct filter string e.g. ["amenity":"school"]
        filters = "".join([f'["{k}"="{v}"]' for k, v in tags.items()])
        query_parts.append(f"node{filters}({bounds});")
        query_parts.append(f"way{filters}({bounds});")

    if not query_parts:
        return {"type": "FeatureCollection", "features": []}

    # Construct final Overpass QL query
    # Increased timeout to 60s for large areas
    query = f"""
        [out:json][timeout:60];
        (
          {''.join(query_parts)}
        );
        out geom;
    """

    print(f"🔍 Querying Overpass for {layer_type}...")
    # print(f"Query:\n{query}") # Uncomment to debug exact query sent

    try:
        async with httpx.AsyncClient(timeout=65.0) as client: # Client timeout > Query timeout
            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data=query,
                headers={"User-Agent": "WatershedDemocracyApp/1.0"} # Polite user agent
            )
            
            if response.status_code != 200:
                print(f"❌ Overpass API returned status {response.status_code}: {response.text[:200]}")
                raise HTTPException(status_code=502, detail=f"Overpass API error: {response.status_code}")

            osm_data = response.json()

        # Convert OSM JSON to GeoJSON
        features = []
        elements = osm_data.get("elements", [])
        print(f"✅ Received {len(elements)} elements from Overpass.")

        for element in elements:
            if "type" not in element:
                continue
            
            tags = element.get("tags", {})
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
                if len(coords) < 2: continue
                
                if coords[0] == coords[-1]:
                    feature["geometry"] = {"type": "Polygon", "coordinates": [coords]}
                else:
                    feature["geometry"] = {"type": "LineString", "coordinates": coords}
            
            features.append(feature)

        print(f"✨ Converted to {len(features)} GeoJSON features.")
        return {"type": "FeatureCollection", "features": features}

    except httpx.TimeoutException:
        print("⏰ Overpass API request timed out.")
        raise HTTPException(status_code=504, detail="OpenStreetMap query timed out. Try zooming in to a smaller area.")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
import httpx
import json

@app.get("/api/osm/{layer_type}")
async def get_osm_data(layer_type: str, bounds: str = "49.0,-10.0,61.0,2.0"):
    """
    Fetch data from OpenStreetMap via Overpass API.
    """
    # Define tags for different layers
    # Data centers are rare, so we include related infrastructure tags
    tag_map = {
        "data_center": [
            {"man_made": "data_center"},
            {"building": "data_center"},
            {"telecom": "data_center"},
            #{"office": "it"}, # Fallback for IT offices which might be DCs
            #{"landuse": "industrial"} # Very broad fallback if needed, but risky
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
