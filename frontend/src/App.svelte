<script>
  import { onMount, onDestroy } from 'svelte';
  import maplibregl from 'maplibre-gl';
  import 'maplibre-gl/dist/maplibre-gl.css';

  import SearchBox from './components/SearchBox.svelte';
  import LayerList from './components/LayerList.svelte';
  import DetailPanel from './components/DetailPanel.svelte';
  import { EMPTY, boundsOf, containsPoint, dcLabel, pointFeature, toDc } from './lib/geo.js';
  import { getPartyColor } from './lib/party.js';

  const DC_COLOR = '#ff4d00';
  const DC_LAYER = 'data-centers-layer';

  // Toggleable layers. Polygons go under the selection highlight; data centres
  // go under the selected-point marker, so the selection always draws on top.
  const LAYERS = [
    {
      key: 'datacentres',
      label: 'Data centres',
      swatch: 'dot',
      color: DC_COLOR,
      cap: 1000, // /api/datacentres default limit
      url: '/api/datacentres',
      beforeId: 'selected-dc',
      style: [{
        id: DC_LAYER,
        type: 'circle',
        filter: ['==', ['geometry-type'], 'Point'],
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 5, 3.5, 10, 6],
          'circle-color': DC_COLOR,
          'circle-stroke-width': 1.5,
          'circle-stroke-color': '#ffffff'
        }
      }]
    },
    {
      key: 'constituencies',
      label: 'Parliamentary constituencies',
      swatch: 'line',
      color: '#5b4fc4',
      url: '/api/parliamentary-boundaries',
      beforeId: 'highlight-fill',
      style: [
        { id: 'parliamentary-fill', type: 'fill', paint: { 'fill-color': '#5b4fc4', 'fill-opacity': 0.04 } },
        { id: 'parliamentary-line', type: 'line', paint: { 'line-color': '#5b4fc4', 'line-width': 1, 'line-dasharray': [3, 2], 'line-opacity': 0.6 } }
      ]
    },
    {
      key: 'counties',
      label: 'Counties',
      swatch: 'dash',
      color: '#333333',
      url: '/api/counties',
      beforeId: 'highlight-fill',
      style: [
        { id: 'counties-fill', type: 'fill', paint: { 'fill-color': '#ffffff', 'fill-opacity': 0.1 } },
        { id: 'counties-line', type: 'line', paint: { 'line-color': '#000000', 'line-width': 1, 'line-dasharray': [2, 2] } }
      ]
    }
  ];

  let map;
  let mapEl;
  let aboutDialog;
  let loading = true;
  let error = null;

  let layerState = Object.fromEntries(
    LAYERS.map((l) => [l.key, { visible: false, loading: false, error: null, count: null }])
  );

  /** Data-centre point features, for search and "same constituency" lookups. */
  let dataCentres = [];

  /** See DetailPanel for the shape. */
  let selected = null;
  let selectToken = 0;

  /** Mobile bottom-sheet height: 'peek' | 'half' | 'full'. Ignored on desktop. */
  let sheet = 'peek';
  const mobileQuery = window.matchMedia('(max-width: 768px)');

  let hoverPopup;

  onMount(async () => {
    map = new maplibregl.Map({
      container: mapEl,
      style: 'https://tiles.openfreemap.org/styles/positron',
      center: [-2.5, 54.0],
      zoom: 5.2,
      attributionControl: false
    });
    // Top-right keeps the controls clear of the mobile bottom sheet.
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'top-right');
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    const mapReady = new Promise((resolve) => map.once('load', resolve));

    hoverPopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10, className: 'dc-tooltip' });

    try {
      // Startup contract: this works without a database (see CLAUDE.md).
      const response = await fetch('/api/geojson?source=sample');
      if (!response.ok) {
        console.error(`API Error ${response.status}:`, await response.text());
        throw new Error(`Failed to fetch base data: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      await mapReady;

      map.addSource('geojson-data', { type: 'geojson', data: { type: 'FeatureCollection', features: data.features || [] } });
      map.addLayer({ id: 'data-fill', type: 'fill', source: 'geojson-data', paint: { 'fill-color': '#4a90d9', 'fill-opacity': 0.4 } });
      map.addLayer({ id: 'data-outline', type: 'line', source: 'geojson-data', paint: { 'line-color': '#2c5aa0', 'line-width': 1 } });

      // Selection layers exist from the start (empty) so toggleable layers can be inserted beneath them.
      map.addSource('highlight', { type: 'geojson', data: EMPTY });
      map.addLayer({ id: 'highlight-fill', type: 'fill', source: 'highlight', paint: { 'fill-color': '#ff9800', 'fill-opacity': 0.25 } });
      map.addLayer({ id: 'highlight-line', type: 'line', source: 'highlight', paint: { 'line-color': '#e65100', 'line-width': 2 } });
      map.addSource('selected-dc', { type: 'geojson', data: EMPTY });
      map.addLayer({
        id: 'selected-dc',
        type: 'circle',
        source: 'selected-dc',
        paint: { 'circle-radius': 9, 'circle-color': DC_COLOR, 'circle-stroke-width': 3, 'circle-stroke-color': '#ffffff' }
      });

      loading = false;
      toggleLayer('datacentres');
    } catch (err) {
      error = err.message;
      loading = false;
      console.error('Map Load Error:', err);
    }
  });

  onDestroy(() => {
    if (map) map.remove();
  });

  async function toggleLayer(key) {
    const def = LAYERS.find((l) => l.key === key);
    const visible = !layerState[key].visible;

    if (map.getSource(key)) {
      for (const layer of def.style) map.setLayoutProperty(layer.id, 'visibility', visible ? 'visible' : 'none');
      layerState[key] = { ...layerState[key], visible };
      return;
    }

    layerState[key] = { ...layerState[key], loading: true, error: null };
    try {
      const res = await fetch(def.url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (!data.features?.length) {
        layerState[key] = { visible: false, loading: false, error: 'No data available.', count: null };
        return;
      }

      map.addSource(key, { type: 'geojson', data });
      for (const layer of def.style) map.addLayer({ ...layer, source: key }, def.beforeId);
      layerState[key] = { visible: true, loading: false, error: null, count: data.features.length };

      if (key === 'datacentres') {
        dataCentres = data.features.filter((f) => f.geometry?.type === 'Point');
        bindDataCentreEvents();
      }
    } catch (err) {
      console.error(`Error loading ${key}:`, err);
      layerState[key] = { visible: false, loading: false, error: 'Couldn’t load this layer.', count: null };
    }
  }

  function bindDataCentreEvents() {
    map.on('mousemove', DC_LAYER, (e) => {
      map.getCanvas().style.cursor = 'pointer';
      const f = e.features[0];
      hoverPopup.setLngLat(f.geometry.coordinates).setText(dcLabel(f.properties)).addTo(map);
    });
    map.on('mouseleave', DC_LAYER, () => {
      map.getCanvas().style.cursor = '';
      hoverPopup.remove();
    });
    map.on('click', DC_LAYER, (e) => selectDataCentre(e.features[0]));
  }

  const isMobile = () => mobileQuery.matches;

  // On mobile the half-open sheet covers the bottom half of the map.
  function fitPadding() {
    if (!isMobile()) return 48;
    return { top: 32, left: 24, right: 24, bottom: mapEl.clientHeight * 0.5 + 16 };
  }

  async function selectDataCentre(feature) {
    const dc = toDc(feature);
    const token = ++selectToken;
    selected = { dc, status: 'loading' };
    sheet = 'half';
    hoverPopup.remove();
    map.getSource('selected-dc').setData(pointFeature(dc.coordinates));
    map.getSource('highlight').setData(EMPTY);

    const [lon, lat] = dc.coordinates;
    try {
      const res = await fetch(`/api/constituency-mp?lat=${lat}&lon=${lon}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const mp = await res.json();
      if (token !== selectToken) return;

      if (!mp.found) {
        selected = { dc, status: 'outside', message: mp.message };
        map.flyTo({
          center: dc.coordinates,
          zoom: Math.max(map.getZoom(), 9),
          offset: isMobile() ? [0, -mapEl.clientHeight * 0.25] : [0, 0]
        });
        return;
      }

      selected = { dc, status: 'ready', mp: { ...mp, color: getPartyColor(mp.party) }, neighbours: null };

      const geomRes = await fetch(`/api/constituency/${encodeURIComponent(mp.constituency)}`);
      if (!geomRes.ok) throw new Error(`HTTP ${geomRes.status}`);
      const geom = await geomRes.json();
      if (token !== selectToken || !geom.features?.length) return;

      map.getSource('highlight').setData(geom);
      const area = geom.features[0].geometry;
      selected = {
        ...selected,
        neighbours: dataCentres.filter(
          (f) => containsPoint(area, f.geometry.coordinates) && !sameDc(toDc(f), dc)
        )
      };

      const bounds = boundsOf(geom);
      if (bounds) map.fitBounds(bounds, { padding: fitPadding(), duration: 1200, maxZoom: 11 });
    } catch (err) {
      console.error('Error fetching details:', err);
      // Keep MP details if only the boundary failed.
      if (token === selectToken && selected.status !== 'ready') selected = { dc, status: 'error' };
    }
  }

  function sameDc(a, b) {
    if (a.id != null && b.id != null) return a.id === b.id;
    return a.coordinates[0] === b.coordinates[0] && a.coordinates[1] === b.coordinates[1];
  }

  function clearSelection() {
    selectToken++;
    selected = null;
    sheet = 'peek';
    map?.getSource('selected-dc')?.setData(EMPTY);
    map?.getSource('highlight')?.setData(EMPTY);
  }

  function cycleSheet() {
    sheet = { peek: 'half', half: 'full', full: 'peek' }[sheet];
  }

  function onKeydown(e) {
    if (e.key === 'Escape' && !e.defaultPrevented && selected && !aboutDialog?.open) clearSelection();
  }
</script>

<svelte:window on:keydown={onKeydown} />

<main>
  <header class="topbar">
    <div class="brand">
      <h1>Carta Magna</h1>
      <p class="subtitle">UK data centres and who represents them</p>
    </div>
    <div class="search-slot">
      <SearchBox items={dataCentres} on:select={(e) => selectDataCentre(e.detail)} />
    </div>
    <button class="icon-btn" type="button" on:click={() => aboutDialog.showModal()} aria-label="About this map">i</button>
  </header>

  <aside class="panel sheet-{sheet}" class:has-selection={selected}>
    <button class="sheet-handle" type="button" on:click={cycleSheet} aria-label="Resize panel">
      <span class="grip" aria-hidden="true"></span>
      <span class="sheet-title">
        {selected ? dcLabel(selected.dc) : 'Layers · tap a data centre'}
      </span>
    </button>

    <div class="panel-body">
      <div class="panel-section layers-section">
        <LayerList layers={LAYERS} state={layerState} on:toggle={(e) => toggleLayer(e.detail)} />
      </div>
      <div class="panel-section detail-section">
        <DetailPanel
          {selected}
          on:close={clearSelection}
          on:select={(e) => selectDataCentre(e.detail)}
        />
      </div>
    </div>
  </aside>

  <div class="map-container">
    <div class="map" bind:this={mapEl}></div>
    {#if loading}
      <div class="overlay">Loading map…</div>
    {:else if error}
      <div class="overlay error">Error: {error}</div>
    {/if}
  </div>

  <dialog bind:this={aboutDialog} class="about">
    <h2>About Carta Magna</h2>
    <p>
      This map places UK data-centre infrastructure next to democratic representation. Select a data centre to
      see the parliamentary constituency it sits in, the sitting MP, and the constituency boundary.
    </p>
    <p>
      Data centres come from OpenStreetMap, constituency boundaries from the ONS (2024), and MPs from
      TheyWorkForYou. The map currently shows at most 1,000 data centres.
    </p>
    <form method="dialog"><button type="submit">Close</button></form>
  </dialog>
</main>

<style>
  :global(:root) {
    --brand: #2c5aa0;
    --brand-2: #4a90d9;
    --ink: #1f2933;
    --muted: #5f6b7a;
    --line: #e3e7ec;
    --surface: #ffffff;
    --surface-2: #f3f5f8;
    --accent: #e04400;
    --danger: #c62828;
  }

  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--surface);
    color: var(--ink);
  }

  :global(*), :global(*::before), :global(*::after) { box-sizing: border-box; }

  main {
    display: grid;
    grid-template-columns: 340px minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
    grid-template-areas:
      'top top'
      'panel map';
    height: 100vh;
    height: 100dvh;
    width: 100vw;
    overflow: hidden;
  }

  /* Top bar */
  .topbar {
    grid-area: top;
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.6rem 1rem;
    background: linear-gradient(135deg, var(--brand-2), var(--brand));
    color: #fff;
    z-index: 15;
  }
  .brand { flex-shrink: 0; width: calc(340px - 2rem); }
  h1 { margin: 0; font-size: 1.15rem; line-height: 1.2; }
  .subtitle { margin: 0.1rem 0 0; font-size: 0.78rem; opacity: 0.9; }
  .search-slot { flex: 1; max-width: 480px; }

  .icon-btn {
    margin-left: auto;
    flex-shrink: 0;
    width: 32px; height: 32px;
    border-radius: 50%;
    border: 1.5px solid rgba(255,255,255,0.8);
    background: transparent;
    color: #fff;
    font: italic 700 0.95rem Georgia, serif;
    cursor: pointer;
  }
  .icon-btn:hover { background: rgba(255,255,255,0.15); }

  /* Side panel (bottom sheet on mobile) */
  .panel {
    grid-area: panel;
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: var(--surface);
    border-right: 1px solid var(--line);
    z-index: 10;
  }
  .panel-body { flex: 1; overflow-y: auto; overscroll-behavior: contain; }
  .panel-section { padding: 1rem 1.1rem; }
  .layers-section { border-bottom: 1px solid var(--line); }
  .sheet-handle { display: none; }

  /* Map */
  .map-container { grid-area: map; position: relative; background: #eee; }
  .map { position: absolute; inset: 0; }

  .overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    background: rgba(255,255,255,0.9);
    z-index: 5;
    pointer-events: none;
  }
  .error {
    color: var(--danger);
    background: rgba(255, 235, 238, 0.95);
    pointer-events: auto;
    font-weight: 500;
  }

  :global(.dc-tooltip) { pointer-events: none; }
  :global(.dc-tooltip .maplibregl-popup-content) {
    padding: 0.3rem 0.55rem;
    font-size: 0.8rem;
    font-weight: 600;
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  }

  /* About dialog */
  .about {
    max-width: min(480px, calc(100vw - 32px));
    border: 0;
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    box-shadow: 0 12px 40px rgba(0,0,0,0.25);
    color: var(--ink);
  }
  .about::backdrop { background: rgba(15, 23, 42, 0.45); }
  .about h2 { margin: 0 0 0.6rem; font-size: 1.1rem; }
  .about p { margin: 0 0 0.8rem; font-size: 0.92rem; line-height: 1.55; color: var(--muted); }
  .about form { text-align: right; }
  .about button {
    font: inherit;
    padding: 0.4rem 1rem;
    border: 0;
    border-radius: 6px;
    background: var(--brand);
    color: #fff;
    cursor: pointer;
  }

  /* Mobile: map fills the screen; the panel becomes a bottom sheet over it. */
  @media (max-width: 768px) {
    main {
      grid-template-columns: minmax(0, 1fr);
      grid-template-areas:
        'top'
        'map';
    }

    .topbar { flex-wrap: wrap; gap: 0.5rem 0.75rem; padding: 0.5rem 16px; }
    .brand { width: auto; flex: 1; }
    h1 { font-size: 1.05rem; }
    .subtitle { display: none; }
    .icon-btn { margin-left: 0; }
    .search-slot { order: 3; flex-basis: 100%; max-width: none; }

    .panel {
      grid-area: map;
      align-self: end;
      border-right: 0;
      border-radius: 14px 14px 0 0;
      box-shadow: 0 -4px 20px rgba(0,0,0,0.15);
      transition: height 0.25s ease;
    }
    .sheet-peek { height: 56px; }
    .sheet-half { height: 50%; }
    .sheet-full { height: 100%; border-radius: 0; }

    .sheet-handle {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.35rem;
      flex-shrink: 0;
      width: 100%;
      padding: 0.45rem 16px 0.6rem;
      border: 0;
      background: none;
      font: inherit;
      cursor: pointer;
    }
    .grip { width: 36px; height: 4px; border-radius: 2px; background: #c7ccd3; }
    .sheet-title {
      max-width: 100%;
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--ink);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .sheet-peek .panel-body { display: none; }
    .panel-body { display: flex; flex-direction: column; }
    .panel-section { padding: 0.75rem 16px; }
    /* Details first when something is selected. */
    .has-selection .detail-section { order: -1; border-bottom: 1px solid var(--line); }
    .has-selection .layers-section { border-bottom: 0; }
  }
</style>
