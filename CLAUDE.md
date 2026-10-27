# CLAUDE.md

This file guides Claude Code (claude.ai/code) when working in this repository.

## What this is

**Carta Centrum Data** (UI title: "Carta Magna") is a map-based PWA that places UK data-centre infrastructure next to democratic representation. Click a data centre and the app finds the parliamentary constituency it sits in, the sitting MP, and highlights the constituency boundary.

- **Frontend**: Svelte 4 + Vite 5 + MapLibre GL 4 (`frontend/`)
- **Backend**: FastAPI + asyncpg (`backend/app/`)
- **Database**: PostgreSQL + PostGIS. Production uses Supabase (London), reached through its transaction pooler.
- **Hosting**: Vercel (https://carta-centrum-data.vercel.app). The Svelte build is served as static files and FastAPI runs as a Python function (`api/index.py`). The Dockerfile still works for self-hosting.
- **External data**: OpenStreetMap (Overpass API), ONS 2024 constituency boundaries (GeoJSON), TheyWorkForYou API (MPs)

The root `README.md` is a leftover generic template and is partly out of date. Trust the code and `ARCHITECTURE.md` over it.

## Commands

All backend commands run from `backend/`.

```bash
# Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8001   # the Vite dev proxy targets :8001
DEMO_MODE=true uvicorn app.main:app --port 8001   # sample data, no database

# Schema and data
python -m migrations                  # apply pending backend/migrations/*.sql
python -m importers.constituencies    # needs backend/constituencies.geojson (gitignored; ONS boundaries)
python -m importers.mps               # needs THEYWORKFORYOU_KEY
python -m importers.osm_datacentres   # UK data centres from Overpass

# Tests (DB tests skip unless TEST_DATABASE_URL points at a disposable PostGIS)
docker run -d --name carta-test-db -e POSTGRES_PASSWORD=test -e POSTGRES_DB=carta_test -p 55432:5432 postgis/postgis:15-3.3
TEST_DATABASE_URL=postgresql://postgres:test@localhost:55432/carta_test pytest
pytest tests/test_spa.py::test_service_worker_is_not_cached   # single test

# Frontend (from frontend/)
npm install
npm run dev        # http://localhost:3000, proxies /api -> $VITE_PROXY_TARGET or http://localhost:8001
npm run build      # outputs to frontend/build/ (served by FastAPI in prod)

# Production-style single container (from repo root)
docker build -t carta-centrum . && docker run -p 8000:8000 -e DATABASE_URL=... carta-centrum

# Vercel (from repo root; project vidaleando1/carta-centrum-data, not Git-connected)
vercel deploy          # preview (behind Vercel login; test with `vercel curl /health --deployment <url>`)
vercel deploy --prod
```

There are no linters or type-checkers configured.

## Backend layout

- `app/main.py`: `create_app(settings)`. It wires middleware and the lifespan, includes the routers, and includes `routers/spa.py` **last** (it's a catch-all).
- `app/config.py`: `Settings` (pydantic-settings; reads env vars, then `backend/.env`). `app_settings` dependency.
- `app/db.py`: lazily created pool on `app.state.db`. The `Conn` dependency and the `connection(request)` context manager both raise **503** when the database is unreachable.
- `app/routers/`: one module per domain (`datacentres`, `constituencies`, `boundaries`, `health`), plus `demo` and `spa`.
- `app/queries/`: SQL strings only. GeoJSON endpoints build the whole FeatureCollection in PostGIS (`geojson.fetch_feature_collection`) and return the text as-is, with no per-feature parsing in Python.
- `importers/`: fetch, then parse and validate, then `common.replace_rows`, which does an atomic `DELETE` + insert in one transaction. Importers never run DDL.
- `migrations/`: numbered `.sql` files, recorded in `schema_migrations`. Add a new file; never edit an applied one.

## Conventions and behaviour

- **Demo mode is explicit.** With `DEMO_MODE=true`, `routers/demo.py` is mounted *instead of* the DB routers. Keep its paths in sync with the real ones. Without demo mode, a missing database means 503s, never silently empty data.
- **Errors:** let unexpected exceptions propagate (FastAPI returns a generic 500 and logs the traceback). Never put `str(e)` in a response.
- **Logging:** use `logging.getLogger(__name__)`, not `print`. Never log `DATABASE_URL` or API keys; use `settings.database_label`. Importers silence `httpx` INFO logs because those include full URLs.
- **Frontend contract:** the frontend calls `/api/geojson?source=sample` on startup. It must keep working without a database. `/api/geojson` is otherwise a deprecated alias of `/api/datacentres`.
- **Tests** build apps with `tests.conftest.client_for(**settings)`, which ignores `.env`. DB tests use only `TEST_DATABASE_URL`, because the fixtures wipe and reseed tables.
- **Data model notes:**
  - MPs are joined to constituencies by lower-cased name, not ONS code.
  - `osm_data_centers.osm_id` is `"<type>/<id>"` (e.g. `way/123`).
  - `basic_bounds` (counties layer) is loaded externally with ogr2ogr and isn't covered by migrations.

## Deployment (Vercel + Supabase)

- `vercel.json` builds `frontend/` and routes `/api/*`, `/health`, `/docs` and `/openapi.json` to the function. Everything else falls back to `index.html`.
- The function installs from the **root** `requirements.txt`. Vercel can't follow `-r`, so keep it in sync with `backend/requirements.txt`. `.python-version` pins 3.12 for the pinned pydantic and asyncpg.
- Env vars on Vercel: `DATABASE_URL` (Supabase transaction pooler, port 6543), `DB_STATEMENT_CACHE_SIZE=0` (required by the transaction pooler), `DB_POOL_MIN_SIZE=0`, `DB_POOL_MAX_SIZE=3`.
- Run migrations and importers against the **session** pooler (port 5432) from your machine.
- Function responses are limited to 4.5 MB. GZip plus 6-decimal coordinates keep `/api/parliamentary-boundaries` at about 2.3 MB.
- Building that layer takes about 20 s on Supabase's free tier. Boundary layers send `Cache-Control: s-maxage=86400`, so Vercel's CDN serves repeat requests. Hit the endpoint once after a deploy to warm the cache.
- Migration `002` enables RLS with no policies, so Supabase's auto-generated REST API exposes nothing. The app connects as the table owner, which bypasses RLS. Enable RLS on any new public table too.

## Gotchas

- Never print, log or commit the contents of `.env` files. `backend/venv/` and `frontend/node_modules/` are tracked by mistake. The committed `backend/venv` is broken (it points at a missing Python 3.12), so create a fresh one.
- `/api/datacentres` defaults to `limit=1000`, and the frontend doesn't pass a limit, so the map shows at most 1,000 points (OSM has ~4,800).
- `LICENSE` is GPL-3.0, while the README says MIT.
