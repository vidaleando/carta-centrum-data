import asyncio
import asyncpg
import httpx
import json
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# --- Database Configuration (Same as main.py) ---
database_url = os.getenv("DATABASE_URL")
if database_url:
    parsed = urlparse(database_url)
    DB_CONFIG = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": parsed.username or "postgres",
        "password": parsed.password or "postgres",
        "database": parsed.path.lstrip("/") or "pwa_map_db",
    }
else:
    DB_CONFIG = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "postgres",
        "database": "pwa_map_db",
    }

# --- Overpass Logic (Exact copy from your working main.py) ---
async def fetch_osm_data_centers():
    layer_type = "data_center"
    # UK Bounds: min_lat, min_lon, max_lat, max_lon
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

    print(f"📡 Sending request to Overpass API (Query length: {len(overpass_query)} chars)...")
    
    try:
        async with httpx.AsyncClient() as client:
            # EXACT same request structure as your working main.py
            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": overpass_query}, # Send as dict/form-data
                headers={
                    "Accept-Encoding": "gzip, deflate",
                    "User-Agent": "curl/7.88.0",
                },
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
                
                # Calculate centroid for ways to store as Point in DB for simplicity
                # Or store as Polygon if you prefer. Let's store as Point (centroid) for easy mapping.
                lon = sum(c[0] for c in coords) / len(coords)
                lat = sum(c[1] for c in coords) / len(coords)
                feature["geometry"] = {
                    "type": "Point",
                    "coordinates": [lon, lat]
                }
            elif element["type"] == "relation":
                # Skip complex relations for this import
                continue

            features.append(feature)
            
        return features

    except Exception as e:
        print(f"❌ Network/Error: {str(e)}")
        return None

# --- Database Import Logic ---
async def save_to_db(features):
    if not features:
        print("⚠️ No features to save.")
        return

    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        print("🔗 Connected to database.")

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

async def main():
    print("🚀 Starting Data Center Import Script...")
    
    # 1. Fetch
    features = await fetch_osm_data_centers()
    
    # 2. Save
    if features:
        await save_to_db(features)
    else:
        print("⚠️ Skipped database save due to fetch failure.")

if __name__ == "__main__":
    asyncio.run(main())