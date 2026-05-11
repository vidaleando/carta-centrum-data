"""
FastAPI backend for serving GeoJSON data from PostGIS database.
"""
import os
import json
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "database": os.getenv("POSTGRES_DB", "gisdb"),
}

# Global database pool
db_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database connection pool lifecycle."""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)
        print("Database pool created successfully")
    except Exception as e:
        print(f"Warning: Could not connect to database: {e}")
        print("Running in demo mode with sample data")
        db_pool = None
    yield
    if db_pool:
        await db_pool.close()
        print("Database pool closed")


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
    table_name: Optional[str] = "basic_bounds",
    limit: Optional[int] = 1000
):
    """
    Fetch geographical data from PostGIS and return as GeoJSON.
    
    Args:
        table_name: Name of the PostGIS table containing geometries
        limit: Maximum number of features to return
    
    Returns:
        GeoJSON FeatureCollection
    """
    if not db_pool:
        # Return sample data if database is not connected
        return get_sample_geojson()
    
    try:
        async with db_pool.acquire() as conn:
            # Query to fetch GeoJSON from PostGIS
            # Assumes table has a 'geom' column with geometry data
            # and optionally other columns for properties
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
            
            rows = await conn.fetch(query, limit)
            
            if not rows:
                print("⚠️  No rows found in database. Returning sample data.")
                return get_sample_geojson()
            
            features = [row['geojson'] for row in rows]
            
            print(f"✅ Successfully fetched {len(features)} features from DB.")
            
            return {
                "type": "FeatureCollection",
                "features": features
            }
    
    except Exception as e:
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
