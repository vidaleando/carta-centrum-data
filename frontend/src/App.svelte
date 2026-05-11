<script>
  import { onMount, onDestroy } from 'svelte';
  import maplibregl from 'maplibre-gl';
  import 'maplibre-gl/dist/maplibre-gl.css';

  let map;
  let mapWrapper;
  let geojsonData = [];
  let loading = true;
  let error = null;

  let showDataCenters = false;
  let dataCentersLoaded = false;
  let dataCentersLoading = false;
  let dataCentersError = null;

  onMount(async () => {
    const mapDiv = document.createElement('div');
    mapDiv.style.cssText = 'width:100%;height:100%;';
    mapWrapper.appendChild(mapDiv);

    try {
      map = new maplibregl.Map({
        container: mapDiv,
        style: 'https://demotiles.maplibre.org/style.json',
        center: [-3.4360, 55.3781],
        zoom: 5.5,
        attributionControl: true
      });

      const response = await fetch('http://localhost:8001/api/geojson?source=sample');
      if (!response.ok) throw new Error('Failed to fetch base data');

      const data = await response.json();
      geojsonData = data.features || [];

      map.on('load', () => {
        map.addSource('geojson-data', {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: geojsonData }
        });
        map.addLayer({ id: 'data-fill', type: 'fill', source: 'geojson-data', paint: { 'fill-color': '#4a90d9', 'fill-opacity': 0.4 } });
        map.addLayer({ id: 'data-outline', type: 'line', source: 'geojson-data', paint: { 'line-color': '#2c5aa0', 'line-width': 1 } });
        loading = false;
      });
    } catch (err) {
      error = err.message;
      loading = false;
      console.error(err);
    }
  });

  // onDestroy is the correct place for cleanup — returning from async onMount doesn't work
  onDestroy(() => {
    if (map) map.remove();
  });


  // --- Toggle Logic ---
  async function toggleDataCenters() {
    // Flip state immediately for UI responsiveness
    showDataCenters = !showDataCenters;

    if (showDataCenters) {
      // If turning ON
      if (dataCentersLoaded) {
        // Already loaded, just show it
        if (map.getLayer('data-centers-layer')) {
          map.setLayoutProperty('data-centers-layer', 'visibility', 'visible');
        }
      } else {
        // Need to load it
        dataCentersLoading = true;
        dataCentersError = null;
        
        try {
          // Define UK Bounds for Overpass
          //const bounds = "-10.0,49.0,2.0,61.0"; 
          const bounds = "49.0,-10.0,61.0,2.0";
          //const res = await fetch(`http://localhost:8001/api/osm/data_center?bounds=${bounds}`);
          const res = await fetch(`http://localhost:8001/api/osm/data_center?bounds=${bounds}`);
          if (!res.ok) throw new Error("API Error");
          
          const dcData = await res.json();
          
          if (!dcData.features || dcData.features.length === 0) {
            dataCentersError = "No data centers found in OSM for this area.";
            showDataCenters = false; // Revert toggle
            dataCentersLoading = false;
            return;
          }

          // Add Source & Layer
          map.addSource('data-centers-source', {
            type: 'geojson',
            data: dcData
          });

          map.addLayer({
            id: 'data-centers-layer',
            type: 'circle',
            source: 'data-centers-source',
            paint: {
              'circle-radius': 8,
              'circle-color': '#ff0000',
              'circle-stroke-width': 2,
              'circle-stroke-color': '#ffffff'
            }
          });

          // Add Popup
          map.on('click', 'data-centers-layer', (e) => {
            const props = e.features[0].properties;
            new maplibregl.Popup()
              .setLngLat(e.lngLat)
              .setHTML(`<strong>${props.name || 'Data Center'}</strong><br>${props.operator || ''}`)
              .addTo(map);
          });

          dataCentersLoaded = true;
          dataCentersLoading = false;

        } catch (err) {
          console.error(err);
          dataCentersError = "Failed to load data centers.";
          showDataCenters = false; // Revert toggle on error
          dataCentersLoading = false;
        }
      }
    } else {
      // If turning OFF, just hide the layer
      if (map.getLayer('data-centers-layer')) {
        map.setLayoutProperty('data-centers-layer', 'visibility', 'none');
      }
    }
  }
</script>

<main>
  <header>
    <div class="header-content">
      <div>
        <h1>Watershed Democracy</h1>
        <p>PostGIS + MapLibre PWA</p>
      </div>
      
      <!-- Toggle Switch -->
      <div class="toggle-container">
        <label class="switch-label">
          <span>Data Centers</span>
          <div class="switch-wrapper">
            <input 
              type="checkbox" 
              checked={showDataCenters} 
              on:change={toggleDataCenters}
              disabled={dataCentersLoading}
            >
            <span class="slider"></span>
          </div>
        </label>
        {#if dataCentersLoading}
          <span class="loading-text">Loading...</span>
        {:else if dataCentersError}
          <span class="error-text">{dataCentersError}</span>
        {/if}
      </div>
    </div>
  </header>

  {#if loading}
    <div class="overlay">Loading map...</div>
  {:else if error}
    <div class="overlay error">Error: {error}</div>
  {/if}

  <!-- <div id="map"></div> -->
  <div id="map" bind:this={mapWrapper}></div>
  
  {#if !loading && !error}
    <div class="info-panel">
      <h3>Features: {geojsonData.length}</h3>
    </div>
  {/if}
</main>

<style>
  :global(body) { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
  main { display: flex; flex-direction: column; height: 100vh; position: relative; }
  
  header {
    background: linear-gradient(135deg, #4a90d9, #2c5aa0);
    color: white;
    padding: 1rem;
    z-index: 10;
    flex-shrink: 0;
  }
  
  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
  }

  h1 { margin: 0; font-size: 1.5rem; }
  p { margin: 0.2rem 0 0; opacity: 0.9; font-size: 0.9rem; }

  /* Toggle Styles */
  .toggle-container {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .switch-label {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    font-size: 0.9rem;
    user-select: none;
  }

  .switch-wrapper {
    position: relative;
    display: inline-block;
    width: 40px;
    height: 22px;
  }

  .switch-wrapper input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .slider {
    position: absolute;
    cursor: pointer;
    top: 0; left: 0; right: 0; bottom: 0;
    background-color: #ccc;
    transition: .4s;
    border-radius: 22px;
  }

  .slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 2px;
    bottom: 2px;
    background-color: white;
    transition: .4s;
    border-radius: 50%;
  }

  input:checked + .slider {
    background-color: #2196F3;
  }

  input:checked + .slider:before {
    transform: translateX(18px);
  }

  input:disabled + .slider {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .loading-text { font-size: 0.8rem; font-style: italic; opacity: 0.9; }
  .error-text { font-size: 0.8rem; color: #ffcccc; }

  #map { flex: 1; width: 100%; min-height: 400px; display: block; }
  
  .overlay {
    position: absolute; top: 60px; left: 0; right: 0; bottom: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem; background: rgba(255,255,255,0.8);
    z-index: 5; pointer-events: none;
  }
  .error { color: #e74c3c; background: rgba(252, 228, 228, 0.9); pointer-events: auto; }
  
  .info-panel {
    background: white; padding: 0.5rem 1rem;
    border-top: 1px solid #ddd; font-size: 0.9rem;
    z-index: 10; flex-shrink: 0;
  }
  .info-panel h3 { margin: 0; color: #333; }
</style>