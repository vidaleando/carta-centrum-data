import asyncio
import asyncpg
import httpx
import json
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# --- FIXED: Robust Database Configuration for Neon ---
database_url = os.getenv("DATABASE_URL")

if database_url:
    # Neon URLs often look like: postgresql://user:pass@host/dbname?sslmode=require
    # We need to preserve the SSL mode if present
    parsed = urlparse(database_url)
    
    # Extract query params to ensure sslmode is passed if needed
    query_params = parsed.query
    
    DB_CONFIG = {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": parsed.username,
        "password": parsed.password,
        "database": parsed.path.lstrip("/") or "pwa_map_db",
        "ssl": "require" # Force SSL for Neon
    }
    
    # If there are specific query params in the URL (like sslmode=require), 
    # asyncpg usually handles the 'ssl' key, but let's be explicit for Neon
    print(f"🔗 Connecting to Neon DB at {parsed.hostname}...")
else:
    print("⚠️ No DATABASE_URL found. Falling back to localhost.")
    DB_CONFIG = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "postgres",
        "database": "pwa_map_db",
        "ssl": False
    }

# --- Overpass Logic (Fixed URL and Headers) ---
async def fetch_osm_data_centers():
    layer_type = "data_center"
    bounds = "49.0,-10.0,61.0,2.0"
    
    tag_map = {
        "data_center": [
            {"man_made": "data_center"},
            {"building": "data_center"},
            {"telecom": "data_center"},
            {"telecom": "exchange"},
            {"telecom": "connection_point"},
            {"building": "server_room"},
            {"building": "technical"},
            {"building": "data_hall"},
        ]
    }

    target_tags = tag_map[layer_type]
    query_parts = []
    
    for tags in target_tags:
        filter_str = "".join([f'["{k}"="{v}"]' for k, v in tags.items()])
        query_parts.append(f"node{filter_str}({bounds});")
        query_parts.append(f"way{filter_str}({bounds});")
        query_parts.append(f"relation{filter_str}({bounds});")

    overpass_query = f"""
        [out:json][timeout:60];
        (
            {"".join(query_parts)}
        );
        out geom;
    """

    print(f"📡 Sending request to Overpass API...")
    
    try:
        async with httpx.AsyncClient() as client:
            # FIX 1: Removed trailing space in URL
            url = "https://overpass-api.de/api/interpreter"
            
            # FIX 2: Added Content-Type header required by some environments
            headers = {
                "Accept-Encoding": "gzip, deflate",
                "User-Agent": "carta-centrum-data-import/1.0",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            response = await client.post(
                url,
                data={"data": overpass_query},
                headers=headers,
                timeout=65.0
            )
            
            if response.status_code == 400:
                print(f"❌ Overpass Query Error: {response.text[:200]}")
                return None
            
            response.raise_for_status()
            osm_data = response.json()

        elements = osm_data.get("elements", [])
        print(f"✅ Found {len(elements)} elements in OSM.")

        features = []
        for element in elements:
            if "type" not in element:
                continue
            
            tags = element.get("tags", {})
            feature = {
                "type": "Feature",
                "properties": {
                    "id": str(element.get("id")),
                    "name": tags.get("name", tags.get("operator", "Unnamed")),
                    "source": "OpenStreetMap",
                    "layer": layer_type,
                    "osm_type": element["type"],
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
                
                lon = sum(c[0] for c in coords) / len(coords)
                lat = sum(c[1] for c in coords) / len(coords)
                feature["geometry"] = {
                    "type": "Point",
                    "coordinates": [lon, lat]
                }
            elif element["type"] == "relation":
                continue

            features.append(feature)
            
        return features

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        print(f"❌ Network/Error: {str(e)}")
        return None

# --- Database Import Logic ---
async def save_to_db(features):
    if not features:
        print("⚠️ No features to save.")
        return

    try:
        # Use the robust DB_CONFIG defined at the top
        conn = await asyncpg.connect(**DB_CONFIG)
        print("🔗 Connected to database successfully.")

        # Create table if not exists
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS osm_data_centers (
                id SERIAL PRIMARY KEY,
                osm_id TEXT UNIQUE,
                name TEXT,
                operator TEXT,
                source TEXT,
                geom GEOMETRY(Point, 4326)
            );
        """)
        print("📋 Table 'osm_data_centers' ready.")

        # Clear existing data to avoid duplicates on re-run
        await conn.execute("TRUNCATE TABLE osm_data_centers RESTART IDENTITY;")
        
        # Insert features
        print(f"💾 Inserting {len(features)} features...")
        for f in features:
            props = f['properties']
            coords = f['geometry']['coordinates']
            
            await conn.execute("""
                INSERT INTO osm_data_centers (osm_id, name, operator, source, geom)
                VALUES ($1, $2, $3, $4, ST_SetSRID(ST_MakePoint($5, $6), 4326))
                ON CONFLICT (osm_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    operator = EXCLUDED.operator,
                    geom = EXCLUDED.geom
            """, 
                props['id'],
                props['name'],
                props.get('operator'),
                props['source'],
                coords[0], # Lon
                coords[1]  # Lat
            )
            
        print(f"✨ Successfully imported {len(features)} data centers!")
        await conn.close()

    except Exception as e:
        print(f"❌ Database Error: {str(e)}")
        import traceback
        traceback.print_exc()

async def main():
    print("🚀 Starting Data Center Import Script...")
    print(f"🌍 Target DB: {DB_CONFIG['host']}")
    
    # 1. Fetch
    features = await fetch_osm_data_centers()
    
    # 2. Save
    if features:
        await save_to_db(features)
    else:
        print("⚠️ Skipped database save due to fetch failure.")

if __name__ == "__main__":
    asyncio.run(main())