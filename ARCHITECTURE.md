# Carta Centrum Data: Architecture & Overview

> An open, map-based tool that shows where the UK's data centres are and who represents those areas in Parliament. Future versions will also show their growing energy demand and environmental footprint.

**Status:** early prototype (v0.0.1), under active development · **License:** GPL-3.0 · **Repo:** [github.com/vidaleando/carta-centrum-data](https://github.com/vidaleando/carta-centrum-data)

---

## 1. What it does

Data centres are physical, energy- and water-intensive facilities, but it's hard for the public to see where they are or who is accountable for them locally. Carta Centrum Data puts both on one map:

1. **Plots UK data centres and telecom infrastructure** sourced from OpenStreetMap.
2. **Overlays political geography**: the 2024 UK parliamentary constituencies and sub-national administrative boundaries.
3. **Links infrastructure to representation**: click any data centre and the app finds the constituency it sits in, shows the sitting MP and their party, and highlights that constituency's boundary on the map.

The in-app working title is **"Watershed Democracy"**.

## 2. Main features

| Feature | Description |
|---|---|
| Interactive map | Pan/zoom vector map (MapLibre GL) centred on the UK |
| Data-centre layer | UK-wide points for OSM features tagged as data centres, telecom exchanges, server rooms, data halls, etc. |
| Constituency layer | All 650 UK parliamentary constituencies (ONS 2024 boundaries), simplified for fast rendering |
| Counties / admin layer | Sub-national administrative divisions |
| MP lookup | Point-in-polygon lookup (PostGIS `ST_Contains`) from a clicked location to its constituency and MP, party and current role |
| Boundary highlight | The selected data centre's constituency is fetched and highlighted |
| Party colouring | MPs are shown with their party's colour |
| PWA | Installable, with a service worker for asset caching |

## 3. System architecture

```
                         ┌──────────────────────────────────────────┐
                         │           Single Docker container         │
┌──────────────────┐     │  ┌──────────────────────────────────────┐ │     ┌───────────────────────┐
│  Browser (PWA)   │────▶│  │ FastAPI (uvicorn), backend/app        │ │────▶│ PostgreSQL + PostGIS  │
│  Svelte 4        │◀────│  │  • /api/*  JSON / GeoJSON endpoints   │ │◀────│ (Neon, managed)       │
│  MapLibre GL 4   │     │  │  • static files + SPA fallback →      │ │     └───────────▲───────────┘
└──────────────────┘     │  │    Svelte build (frontend/build)      │ │                 │
         │               │  └──────────────────────────────────────┘ │                 │ atomic reload
         ▼               └──────────────────────────────────────────┘                 │
  MapLibre demo basemap tiles                                                         │
                         ┌──────────────────────────────────────────┐                 │
                         │ Batch importers (python -m importers.*)  │─────────────────┘
                         │  osm_datacentres · constituencies · mps  │
                         └─────────────────────┬────────────────────┘
                                               ▼
                         Overpass API (OSM) · TheyWorkForYou API · ONS boundary GeoJSON
```

**Key design choices**

- **One deployable unit.** The Svelte app is compiled at image-build time, and FastAPI serves both the API and the static frontend from the same origin. That means no CORS configuration in production and one service to host.
- **Spatial work happens in the database.** Point-in-polygon lookups, geometry simplification (`ST_SimplifyPreserveTopology`) and GeoJSON serialisation (`ST_AsGeoJSON`, `json_agg`) all run in PostGIS, which returns each FeatureCollection as a single JSON value that the API passes straight through.
- **Data is pre-loaded.** Slow or rate-limited sources (Overpass, TheyWorkForYou, large boundary files) are pulled by batch importers into PostGIS, so map requests never wait on third parties. Each importer validates its input first, then replaces the table's rows in a single transaction, so a failed import never leaves a half-empty table.
- **Explicit failure modes.** If the database is unreachable, the API returns `503` (and `/health` reports it) rather than silently serving empty data. It reconnects automatically. A separate `DEMO_MODE=true` setting serves static sample data with no database at all, for offline demos.

## 4. Tech stack

| Layer | Technology | Version |
|---|---|---|
| UI framework | Svelte | 4.x |
| Build tool | Vite | 5.x |
| Map rendering | MapLibre GL JS | 4.7 |
| API | FastAPI on uvicorn | 0.109 / 0.27 |
| DB driver | asyncpg (connection pool, 1–10 conns) | 0.29 |
| Config | pydantic-settings | 2.1 |
| HTTP client | httpx (importers: Overpass, TheyWorkForYou) | 0.27 |
| Tests | pytest | 8.3 |
| Database | PostgreSQL + PostGIS | PG 15 / PostGIS 3.3 (local), Neon (hosted) |
| Container | `python:3.11-slim` + Node (build-time) | n/a |

## 5. Repository layout

```
carta-centrum-data/
├── Dockerfile                 # Production image: builds frontend, runs FastAPI on :8000
├── docker-compose.yml         # Local stack: PostGIS + backend (auto-migrates) + Vite dev server
├── backend/
│   ├── app/
│   │   ├── main.py            # create_app(): middleware, lifespan, routers (SPA catch-all last)
│   │   ├── config.py          # Settings from env / backend/.env (pydantic-settings)
│   │   ├── db.py              # Connection pool; 503 when the database is unreachable
│   │   ├── geojson.py         # Build FeatureCollections in PostGIS, return them untouched
│   │   ├── routers/           # datacentres, constituencies, boundaries, health, demo, spa
│   │   └── queries/           # SQL, one module per domain
│   ├── importers/             # python -m importers.{osm_datacentres,constituencies,mps}
│   ├── migrations/            # Numbered .sql files; python -m migrations
│   ├── tests/                 # pytest; DB tests run against a disposable PostGIS
│   └── requirements.txt
└── frontend/
    ├── src/App.svelte         # Map, layer toggles, popups, sidebar
    ├── src/components/DataCenterInfo.svelte  # Data-centre + MP popup card
    ├── public/{manifest.json, sw.js}         # PWA
    └── vite.config.js         # Dev server :3000, /api proxy → :8001, build → build/
```

## 6. Data model

| Table | Source | Key columns | Notes |
|---|---|---|---|
| `osm_data_centers` | OSM via Overpass (`importers.osm_datacentres`) | `osm_id` (`node/123`, `way/456`, …), `name`, `operator`, `source`, `geom` (Point) | Bounding box covers Great Britain and Northern Ireland (49–61°N, 10°W–2°E). Ways and relations are stored as their centre point. ~4,800 features. |
| `uk_parliamentary_constituencies` | ONS 2024 boundaries GeoJSON (`importers.constituencies`) | `ons_code`, `name`, `name_welsh`, `geometry` (MultiPolygon, 4326) | GiST index on `geometry`, index on `lower(name)` |
| `uk_mps` | TheyWorkForYou API (`importers.mps`) | `member_id`, `name`, `party`, `constituency`, `current_position`, `office_json` | Joined to constituencies by lower-cased name |
| `basic_bounds` | GADM-style admin boundaries (loaded externally, e.g. `ogr2ogr`) | `ogc_fid`, `wkb_geometry`, `name_0..2`, `type_2`, `iso` | Powers the counties layer. Not covered by migrations. |

All geometry is stored in **WGS84 (EPSG:4326)**. The schema lives in `backend/migrations/` and is applied with `python -m migrations`.

## 7. API reference

Base URL is the same origin as the app (e.g. `http://localhost:8000`). Interactive docs are at `/docs` (FastAPI/OpenAPI).

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | DB connectivity: `200 healthy`, `503 unhealthy`, or `200 demo_mode` |
| GET | `/api/datacentres?limit=` | Data centres as a GeoJSON FeatureCollection (`limit` 1–10000, default 1000) |
| GET | `/api/geojson?source=sample` | *Deprecated.* Static sample data (no database needed); without `source=sample`, same as `/api/datacentres` |
| GET | `/api/constituency-mp?lat=&lon=` | Constituency, MP, party and role for a point |
| GET | `/api/constituency/{name}` | Single constituency geometry (simplified to ~100 m) |
| GET | `/api/parliamentary-boundaries` | All constituencies (simplified to ~50 m) |
| GET | `/api/counties` | Up to 300 admin divisions from `basic_bounds` |
| GET | `/api/constituency?lat=&lon=` | Admin division lookup against `basic_bounds` |
| GET | `/*` | Files from the frontend build (`sw.js`, `manifest.json`, `/assets/*`), otherwise the SPA's `index.html` |

If the database is unreachable, data endpoints return `503 {"detail": "Database unavailable"}`.

Example:

```bash
curl "http://localhost:8000/api/constituency-mp?lat=51.5115&lon=-0.0005"
# {"found": true, "constituency": "...", "mp_name": "...", "party": "...", "current_position": ..., "source": "Local DB (ONS 2024 Boundaries)"}
```

## 8. Getting started (local development)

**Prerequisites:** Python 3.11+, Node 20+, and a PostGIS database (local Docker `postgis/postgis:15-3.3` or a free Neon project).

```bash
# 1. Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # then set DATABASE_URL (and THEYWORKFORYOU_KEY for MP import)
python -m migrations              # create the schema
uvicorn app.main:app --reload --port 8001
# No database handy? DEMO_MODE=true uvicorn app.main:app --port 8001

# 2. Load data (one-off)
python -m importers.constituencies   # requires backend/constituencies.geojson (ONS download)
python -m importers.mps              # requires a TheyWorkForYou API key
python -m importers.osm_datacentres

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev                       # http://localhost:3000, /api is proxied to :8001

# 4. Tests (database tests need a disposable PostGIS; they wipe its tables)
docker run -d -e POSTGRES_PASSWORD=test -e POSTGRES_DB=carta_test -p 55432:5432 postgis/postgis:15-3.3
cd backend && TEST_DATABASE_URL=postgresql://postgres:test@localhost:55432/carta_test pytest
```

Or run the whole stack with `docker compose up` (PostGIS on :5432, API on :8000, Vite on :3000).

**Production build:**

```bash
docker build -t carta-centrum .
docker run -p 8000:8000 -e DATABASE_URL="postgresql://…" carta-centrum
docker run --rm -e DATABASE_URL="postgresql://…" carta-centrum python -m migrations   # schema changes
```

## 9. Data sources & attribution

- **OpenStreetMap** contributors, via the Overpass API. Data is © OpenStreetMap contributors under ODbL.
- **Office for National Statistics**: Westminster Parliamentary Constituencies (July 2024) boundaries, under the Open Government Licence.
- **TheyWorkForYou** (mySociety): MP data (API key required).
- **MapLibre** demo basemap tiles.

OSM tagging for data centres is inconsistent, so the import casts a wide net (`man_made`/`building`/`telecom=data_center`, telecom exchanges, server rooms, data halls). Expect both false positives and gaps.

## 10. Known limitations & where help is welcome

This is an honest snapshot of the current state:

- **No CI or linting** yet. The backend has a pytest suite; the frontend has no tests.
- **Monolithic frontend.** `App.svelte` holds almost everything and would benefit from being split into components and modules.
- **Payload size.** Full boundary layers are sent as GeoJSON. Vector tiles (e.g. `ST_AsMVT` or PMTiles) would scale better.
- **Name-based joins.** MPs are matched to constituencies by name rather than ONS code.
- **Stale README.** The root README predates the current architecture.
- **Basemap.** The app uses the MapLibre demo style. A proper UK-focused basemap is needed.

**Good first contributions:** frontend tests, splitting `App.svelte` into components, a vector-tile endpoint for boundaries, better data-centre identification (e.g. cross-referencing operator lists), and new context layers (power grid, water stress, planning applications).
