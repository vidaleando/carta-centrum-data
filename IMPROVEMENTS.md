# Improvement Backlog

Findings from a backend and frontend code review (2026-10-03). Priorities: **P0** = fix now, **P1** = high, **P2** = nice to have.

**Status, 2026-10-06:** the backend was restructured into `backend/app/` (routers, queries, config, db), with migrations, transactional importers and a pytest suite. Items marked ✅ are resolved.

## P0: Critical

| # | Area | Issue | Fix |
|---|---|---|---|
| 1 | Security | Environment files must stay out of git and out of the Docker image (`.dockerignore` only matches a root `.env`) | Untrack env files, ignore `**/.env*` in both ignore files, and supply secrets through platform env vars |
| 2 | Repo hygiene | `.gitignore` is one line of stray prose that ignores nothing, so `backend/venv/` (~1.9k files), `frontend/node_modules/` (~2.5k files), `__pycache__` and `.DS_Store` are committed | Write real `.gitignore`/`.dockerignore` patterns, then `git rm -r --cached` those paths |
| 3 ✅ | Security | `main.py:56` prints `DB_CONFIG`, password included, on every startup. `import_mps.py` logs the API key in the URL | Log host and database name only |
| 4 ✅ | Prod/PWA | The SPA catch-all (`main.py:816`) returns `index.html` for `/sw.js`, `/manifest.json` and `/favicon.svg`, so service-worker registration fails in production | Serve the real file from `frontend/build/` when it exists, and fall back to `index.html` otherwise |
| 5 | PWA | `sw.js` has two `fetch` listeners that both call `respondWith`. Caching is cache-first under a fixed cache name, and it would cache `/api/*` and `index.html` forever | One handler: network-first for navigations, cache-first for `/assets/*` only, never `/api/`. Or switch to `vite-plugin-pwa` |
| 6 | Frontend | `App.svelte:57` registers `map.on('load')` after an `await fetch`. If the style loads first, the handler never fires and "Loading map…" hangs | Create `mapReady = new Promise(r => map.once('load', r))` before the fetch, and disable toggles until it resolves |
| 7 ✅ | Dev env | `docker-compose.yml` references a missing `backend/Dockerfile`. Vite listens on :3000 but compose maps :5173. The proxy targets `localhost:8001` inside the container. `VITE_API_URL` and `DEMO_MODE` are never read. DB name defaults disagree (`gisdb` vs `pwa_map_db`) | Point compose at the root Dockerfile, make the proxy target configurable (`backend:8000`), and use one DB name |

## P1: High

**Backend**
- ✅ **Unauthenticated `POST /api/geojson`** with no validation, plus CORS `*` with `allow_credentials=True`. The frontend is same-origin and never calls POST. Remove the route (or protect it) and restrict CORS.
- ✅ **Overpass injection and open proxy**: `/api/osm/{layer_type}` pastes `bounds` and `layer_type` into the QL query, holds a worker for up to 65 s, and spoofs a curl User-Agent. It's unused, so delete it, or allowlist layers and parse the bbox as floats.
- ✅ **Startup probe on `basic_bounds`**: if that one table is missing, the code sets `db_pool = None`, which disables every DB endpoint and leaks the pool. Keep the pool and only warn.
- ✅ **Schema drift**: `init.sql` and `database_setup.sql` define only `geo_data`. The four tables the app actually uses are created ad hoc by importers or not at all (`basic_bounds`). Move to one migrations source.
- ✅ **Destructive importers**: `DROP TABLE` runs before the fetch, with no transactions and per-row inserts. OSM node and way IDs can collide on `osm_id`, and relations are fetched and then dropped. Use fetch → validate → staging table → atomic swap, and key on `n123`/`w123`.
- ✅ **`/api/geojson` limit**: the limit is applied in Python after fetching every row. `table_name` is unchecked. Use `LIMIT $1` in SQL, `Literal[...]` for the table name, and a bbox filter.
- **Payloads** (partly done ✅: features are now aggregated in SQL with no JSON round-trip): boundaries are still re-simplified on every request, and there's no gzip or `Cache-Control`. Precompute simplified geometry, `json_agg` in SQL, add `GZipMiddleware` and cache headers, and later move to vector tiles (`ST_AsMVT`/Martin/PMTiles).
- ✅ **Errors returned as 200**: DB failures come back as empty collections, `/health` returns 200 when unhealthy, and the 500 responses leak SQL errors. Return proper 5xx codes and log server-side.

**Frontend**
- **Highlight race**: clicks share one highlight source ID. Fast clicks orphan layers or throw "source already exists". Add the highlight source once, then use `setData` plus an AbortController or sequence token. Better: `setFilter` on the already-loaded boundaries layer.
- **Popup mounting**: `innerHTML = ''` deletes MapLibre's close button, and the component is never destroyed. Mount into a detached element, then `popup.setDOMContent(el)` and `$destroy` on close.
- **Toggle bugs**: `countiesLoaded`/`parliamentaryLoaded` are set before the empty-data check, so the next toggle throws on a missing layer. Counties has no loading guard (a double `addSource`). There are no `res.ok` checks.
- **Split `App.svelte`** (916 lines, three near-duplicate toggle functions, about 200 lines of dead code) into `lib/api.js`, a layer config with one generic `setLayerVisible`, and `Map`/`Sidebar`/`LayerToggle`/`DataCenterPopup` components.
- **Map UX**: cluster data centres, insert layers below basemap labels (`beforeId`), use `setFeatureState` for highlights, add a party choropleth, and replace the demo basemap.
- **Accessibility**: no focus ring on the switches, no `role="switch"`, no live regions, data centres are mouse-only, and the party badge has low contrast.

## P2: Nice to have

- **Backend**:
  - ✅ Pass `DATABASE_URL` straight to asyncpg (hand parsing dropped `sslmode`).
  - ✅ Delete `main_buggy.py` and the duplicate or unused endpoints.
  - Join MPs on ONS code, and return geometry from `/api/constituency-mp` to save a round-trip.
  - Use `ST_Covers` instead of `ST_Contains`.
  - Multi-stage Dockerfile, non-root user, `$PORT`, pinned deps.
  - ✅ pytest against PostGIS and `logging` instead of `print`. Still to do: run the suite in CI.
- **Frontend**:
  - Add the missing manifest icons (192, 512 and maskable).
  - Use one product name across the manifest, title and favicon.
  - Use `100dvh` and a mobile bottom-sheet sidebar.
  - Turn off production sourcemaps.
  - Remove the placeholder image and the invented "Redundant Power/Cooling" claims from the popup.
  - Add ESLint rules banning `setHTML` and `{@html}` (the code is XSS-safe today).
  - Add `svelte-check`/TypeScript, Vitest and Playwright.
  - Prepare for Svelte 5 (`mount`/`unmount`, `$props`), ideally after the split above.

## New finding

- **Data-centre cap (P1):** `/api/datacentres` defaults to `limit=1000` and the frontend passes no limit, but OSM currently has about 4,800 matching features. The map silently shows only the first 1,000. Fix it by raising the default, or by clustering and passing an explicit limit from the frontend.

## Suggested order

1. Secret hygiene and repo cleanup (P0 #1–3)
2. Make production work: static file serving, service worker, map load race (P0 #4–6)
3. ~~Lock down the API: remove POST and the Overpass proxy, fix CORS and error codes~~ ✅
4. ~~Migrations and transactional importers~~ ✅
5. Split `App.svelte` while fixing the toggle and popup bugs
6. Performance: caching and gzip, then vector tiles
7. Tests and CI
