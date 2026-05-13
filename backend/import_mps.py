import asyncio
import asyncpg
import os
import httpx
from dotenv import load_dotenv
import json

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("THEYWORKFORYOU_KEY")

if not API_KEY:
    print("❌ THEYWORKFORYOU_KEY not found in .env")
    exit(1)

async def main():
    print("🚀 Starting Robust MP Import...")
    
    try:
        conn = await asyncpg.connect(DB_URL)
        print("🗄️ Connected to database.")
    except Exception as e:
        print(f"❌ DB Connection failed: {e}")
        return

    # 1. Create Table with all necessary fields
    create_table_query = """
        DROP TABLE IF EXISTS public.uk_mps;
        CREATE TABLE public.uk_mps (
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
        CREATE INDEX idx_uk_mps_constituency ON public.uk_mps(lower(constituency));
    """
    
    print("🗄️ Creating table 'uk_mps'...")
    await conn.execute(create_table_query)
    print("✅ Table ready.")

    # 2. Fetch Data
    url = f"https://www.theyworkforyou.com/api/getMPs?key={API_KEY}&output=json"
    
    print(f"📡 Fetching MPs from {url}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            mps_data = resp.json()
            
            if isinstance(mps_data, dict) and 'error' in mps_data:
                print(f"❌ API Error: {mps_data['error']}")
                return
            
            if not isinstance(mps_data, list):
                print(f"⚠️ Unexpected response format: {type(mps_data)}")
                return

            print(f"📦 Found {len(mps_data)} MPs. Inserting...")

            insert_query = """
                INSERT INTO public.uk_mps 
                (member_id, person_id, name, party, constituency, current_position, office_json)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """

            for mp in mps_data:
                # Extract primary position from office list
                current_position = None
                office_json = None
                
                if 'office' in mp and isinstance(mp['office'], list) and len(mp['office']) > 0:
                    office_json = json.dumps(mp['office'])
                    # Take the first office as current position, or search for highest ranking
                    current_position = mp['office'][0].get('position', 'MP')

                try:
                    await conn.execute(
                        insert_query,
                        str(mp.get('member_id')),
                        int(mp.get('person_id', 0)),
                        mp.get('name', 'Unknown'),
                        mp.get('party', 'Unknown'),
                        mp.get('constituency', 'Unknown'),
                        current_position,
                        office_json
                    )
                except Exception as e:
                    print(f"⚠️ Failed to insert {mp.get('name')}: {e}")

            print("✅ Import complete!")

    except Exception as e:
        print(f"❌ Fetch/Insert failed: {e}")
    
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())