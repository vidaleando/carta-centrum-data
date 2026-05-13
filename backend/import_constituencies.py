import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
GEOJSON_FILE = os.path.join(os.path.dirname(__file__), "constituencies.geojson")

async def main():
    print("🚀 Starting ONS Constituency Import...")
    
    if not os.path.exists(GEOJSON_FILE):
        print(f"❌ Error: File '{GEOJSON_FILE}' not found.")
        return

    try:
        conn = await asyncpg.connect(DB_URL)
        print("🗄️ Connected to database.")
    except Exception as e:
        print(f"❌ DB Connection failed: {e}")
        return

    # 1. Create Table
    create_table_query = """
        DROP TABLE IF EXISTS public.uk_parliamentary_constituencies;
        CREATE TABLE public.uk_parliamentary_constituencies (
            id SERIAL PRIMARY KEY,
            ons_code TEXT,
            name TEXT NOT NULL,
            name_welsh TEXT,
            geometry GEOMETRY(MultiPolygon, 4326)
        );
        CREATE INDEX idx_uk_constituencies_geom ON public.uk_parliamentary_constituencies USING GIST(geometry);
        CREATE INDEX idx_uk_constituencies_name ON public.uk_parliamentary_constituencies(lower(name));
    """
    
    print("🗄️ Creating table 'uk_parliamentary_constituencies'...")
    await conn.execute(create_table_query)
    print("✅ Table created with spatial index.")

    # 2. Load GeoJSON
    print(f"📂 Loading {GEOJSON_FILE}...")
    with open(GEOJSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    features = data.get('features', [])
    print(f"📦 Found {len(features)} constituencies. Inserting...")

    # FIX: Wrap ST_GeomFromGeoJSON with ST_Multi to handle both Polygon and MultiPolygon
    insert_query = """
        INSERT INTO public.uk_parliamentary_constituencies 
        (ons_code, name, name_welsh, geometry)
        VALUES ($1, $2, $3, ST_Multi(ST_GeomFromGeoJSON($4)))
    """

    batch = []
    batch_size = 100
    count = 0
    skipped = 0

    for feature in features:
        props = feature.get('properties', {})
        geom = feature.get('geometry')
        
        if not geom:
            skipped += 1
            continue

        # Handle 2024 Field Names (PCON24...)
        name = props.get('PCON24NM') or props.get('pcd24nm') or props.get('name', 'Unknown')
        code = props.get('PCON24CD') or props.get('pcd24cd') or props.get('code', '')
        name_welsh = props.get('PCON24NMW') or props.get('pcd24nmw') or ''

        if name == 'Unknown':
            if count == 0:
                print(f"⚠️ Warning: Could not find name. Available keys: {list(props.keys())}")
            skipped += 1
            continue

        batch.append((code, name, name_welsh, json.dumps(geom)))
        count += 1

        if len(batch) >= batch_size:
            await conn.executemany(insert_query, batch)
            print(f"   ...Inserted {count} / {len(features)}")
            batch = []

    # Insert remaining
    if batch:
        await conn.executemany(insert_query, batch)

    print(f"✅ Successfully imported {count} constituencies!")
    if skipped > 0:
        print(f"⚠️ Skipped {skipped} features (missing geometry or name).")
    
    # Verification
    row = await conn.fetchrow("SELECT count(*) FROM public.uk_parliamentary_constituencies")
    print(f"🔍 Database verify: {row[0]} rows total.")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())