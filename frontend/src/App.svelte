<script>
  import { onMount } from 'svelte';
  import maplibregl from 'maplibre-gl';
  import 'maplibre-gl/dist/maplibre-gl.css';

  let map;
  let mapContainer; // Bind this to the div
  let geojsonData = [];
  let loading = true;
  let error = null;

  onMount(async () => {
    // Safety check: ensure container exists before proceeding
    if (!mapContainer) {
      console.error("Map container not found in DOM");
      loading = false;
      error = "Map container missing";
      return;
    }

    try {
      // Initialize the map
      map = new maplibregl.Map({
        container: mapContainer, // Use the bound variable, not string ID
        style: 'https://demotiles.maplibre.org/style.json',
        center: [-3.4360, 55.3781], // UK Center
        zoom: 5.5,
        attributionControl: true
      });

      // Fetch geographical data from backend
      const response = await fetch('http://localhost:8000/api/geojson');
      
      if (!response.ok) {
        // If backend is down, we still show the map, just without data
        console.warn("Backend unavailable, showing empty map");
        loading = false;
        return;
      }
      
      const data = await response.json();
      geojsonData = data.features || [];
      
      map.on('load', () => {
        if (!map.getSource('geojson-data')) {
          map.addSource('geojson-data', {
            type: 'geojson',
            data: {
              type: 'FeatureCollection',
              features: geojsonData
            }
          });

          // Add fill layer for polygons
          map.addLayer({
            id: 'data-fill',
            type: 'fill',
            source: 'geojson-data',
            paint: {
              'fill-color': '#4a90d9',
              'fill-opacity': 0.6
            },
            filter: ['==', '$type', 'Polygon']
          });

          // Add line layer for polygon boundaries
          map.addLayer({
            id: 'data-outline',
            type: 'line',
            source: 'geojson-data',
            paint: {
              'line-color': '#2c5aa0',
              'line-width': 2
            },
            filter: ['==', '$type', 'Polygon']
          });

          // Add circle layer for points
          map.addLayer({
            id: 'data-points',
            type: 'circle',
            source: 'geojson-data',
            paint: {
              'circle-radius': 8,
              'circle-color': '#e74c3c',
              'circle-stroke-width': 2,
              'circle-stroke-color': '#ffffff'
            },
            filter: ['==', '$type', 'Point']
          });
        }
        loading = false;
      });
    } catch (err) {
      error = err.message;
      loading = false;
      console.error(err);
    }

    return () => {
      if (map) {
        map.remove();
        map = null;
      }
    };
  });
</script>

<main>
  <header>
    <h1>Watershed Democracy</h1>
    <p>Displaying PostGIS data with MapLibre (UK View)</p>
  </header>

  <!-- Loading/Error Overlays -->
  {#if loading}
    <div class="overlay">Loading map...</div>
  {:else if error}
    <div class="overlay error">Error: {error}</div>
  {/if}

  <!-- Map Container always exists, bound to variable -->
  <div bind:this={mapContainer} id="map"></div>
  
  {#if !loading && !error}
    <div class="info-panel">
      <h3>Data Points: {geojsonData.length}</h3>
    </div>
  {/if}
</main>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }

  main {
    display: flex;
    flex-direction: column;
    height: 100vh;
    position: relative;
  }

  header {
    background: linear-gradient(135deg, #4a90d9, #2c5aa0);
    color: white;
    padding: 1rem;
    text-align: center;
    z-index: 10;
  }

  header h1 {
    margin: 0;
    font-size: 1.5rem;
  }

  header p {
    margin: 0.5rem 0 0;
    opacity: 0.9;
    font-size: 0.9rem;
  }

  #map {
    flex: 1;
    width: 100%;
    min-height: 400px;
  }

  .overlay {
    position: absolute;
    top: 60px; /* Below header */
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    background: rgba(255,255,255,0.8);
    z-index: 5;
    pointer-events: none;
  }

  .error {
    color: #e74c3c;
    background: rgba(252, 228, 228, 0.9);
    pointer-events: auto;
  }

  .info-panel {
    background: white;
    padding: 0.5rem 1rem;
    border-top: 1px solid #ddd;
    font-size: 0.9rem;
    z-index: 10;
  }

  .info-panel h3 {
    margin: 0;
    color: #333;
  }
</style>