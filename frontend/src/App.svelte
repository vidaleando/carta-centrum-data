<script>
  import { onMount } from 'svelte';
  import Map from 'maplibre-gl';
  import 'maplibre-gl/dist/maplibre-gl.css';

  let map;
  let geojsonData = [];
  let loading = true;
  let error = null;

  onMount(async () => {
    try {
      // Initialize the map
      map = new Map({
        container: 'map',
        style: 'https://demotiles.maplibre.org/style.json',
        center: [0, 20],
        zoom: 2,
        attributionControl: true
      });

      // Fetch geographical data from backend
      const response = await fetch('/api/geojson');
      if (!response.ok) throw new Error('Failed to fetch data');
      
      const data = await response.json();
      geojsonData = data.features || [];
      
      map.on('load', () => {
        // Add GeoJSON source
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

        loading = false;
      });
    } catch (err) {
      error = err.message;
      loading = false;
    }

    return () => {
      if (map) map.remove();
    };
  });
</script>

<main>
  <header>
    <h1>🗺️ PWA Map Application</h1>
    <p>Displaying PostGIS data with MapLibre</p>
  </header>

  {#if loading}
    <div class="loading">Loading map...</div>
  {:else if error}
    <div class="error">Error: {error}</div>
  {:else}
    <div id="map"></div>
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
  }

  header {
    background: linear-gradient(135deg, #4a90d9, #2c5aa0);
    color: white;
    padding: 1rem;
    text-align: center;
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
  }

  .loading, .error {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
  }

  .error {
    color: #e74c3c;
    background: #fce4e4;
  }

  .info-panel {
    background: white;
    padding: 0.5rem 1rem;
    border-top: 1px solid #ddd;
    font-size: 0.9rem;
  }

  .info-panel h3 {
    margin: 0;
    color: #333;
  }
</style>
