<script>
  import { onMount, onDestroy } from 'svelte';
  import maplibregl from 'maplibre-gl';
  import 'maplibre-gl/dist/maplibre-gl.css';

  import DataCenterInfo from './components/DataCenterInfo.svelte';


  let map;
  let mapWrapper;
  let geojsonData = [];
  let loading = true;
  let error = null;

  let dataCenters;
  let showDataCenters = false;
  let dataCentersLoaded = false;
  let dataCentersLoading = false;
  let dataCentersError = null;

  let showCounties = false;
  let countiesLoaded = false;
  let countyData = [];

  let showParliamentary = false;
  let parliamentaryLoaded = false;
  let parliamentaryLoading = false;

  let highlightedConstituencyName = null;

  onMount(async () => {
    const mapDiv = document.createElement('div');
    mapDiv.style.cssText = 'width:100%;height:100%;';
    mapWrapper.appendChild(mapDiv);

    try {
      map = new maplibregl.Map({
        container: mapDiv,
        style: 'https://demotiles.maplibre.org/style.json',
        center: [-2.5, 54.0], // Moved slightly south and centered horizontally
        zoom: 5.2, // Zoomed out slightly to fit the whole UK comfortably
        // center: [-3.4360, 55.3781],
        // zoom: 5.5,
        attributionControl: true
      });

      const response = await fetch('http://localhost:8001/api/geojson?source=sample');
      if (!response.ok) throw new Error('Failed to fetch base data');

      const data = await response.json();
      geojsonData = data.features || [];

      map.on('load', () => {
        if (map.getSource('geojson-data')) return;
        
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

  onDestroy(() => {
    if (map) map.remove();
  });

async function getMpInfo(lat, lon) {
  try {
    // Call the new local endpoint
    const response = await fetch(`http://localhost:8001/api/constituency-mp?lat=${lat}&lon=${lon}`);
    const data = await response.json();

    if (data.found) {
      return {
        constituency: data.constituency,
        mp: data.mp_name,
        party: data.party,
        source: data.source,
        colour: getPartyColor(data.party),
        current_position: data.current_position 
      };
    }
  } catch (e) {
    console.warn("Could not fetch MP data:", e);
  }
  return null;
}

// Helper: Map UK Party Names to Colors
function getPartyColor(partyName) {
  if (!partyName) return '#cccccc';
  
  const p = partyName.toLowerCase();
  
  if (p.includes('conservative')) return '#0087DC'; // Blue
  if (p.includes('labour')) return '#DC241F';       // Red
  if (p.includes('liberal')) return '#FDBB30';      // Yellow/Orange
  if (p.includes('green')) return '#6AB023';        // Green
  if (p.includes('scottish national') || p.includes('snp')) return '#FFF200'; // Yellow
  if (p.includes('plaid cymru')) return '#3FB637';  // Green
  if (p.includes('democratic unionist') || p.includes('dup')) return '#D46A28'; // Orange
  if (p.includes('sinn féin') || p.includes('sinn fein')) return '#326C29'; // Dark Green
  if (p.includes('social democratic') || p.includes('sdlp')) return '#008A51'; // Green
  if (p.includes('ukip')) return '#70147A';         // Purple
  if (p.includes('reform')) return '#12E0BA';       // Teal
  if (p.includes('independent')) return '#aaaaaa';  // Grey
  
  return '#cccccc'; // Default Grey
}

// Helper to generate consistent mock MP data based on constituency name
function generateMockMp(constituencyName) {
  // Simple hash to pick a random party/color consistently for the same name
  const hash = constituencyName.length; 
  const parties = [
    { name: "Labour", color: "#DC241f" },
    { name: "Conservative", color: "#0087DC" },
    { name: "Liberal Democrat", color: "#FDBB30" },
    { name: "Green", color: "#6AB023" },
    { name: "SNP", color: "#FFF200" }
  ];
  
  const party = parties[hash % parties.length];
  
  // Generate a fake name
  const firstNames = ["James", "Sarah", "David", "Emma", "Michael", "Lucy", "Robert", "Emily"];
  const lastNames = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"];
  
  return {
    name: `${firstNames[hash % firstNames.length]} ${lastNames[hash % lastNames.length]}`,
    party: party.name,
    color: party.color
  };
}
//  // Helper to render Svelte component to HTML string (Svelte 4 compatible)
//   function componentToHtml(Component, props) {
//     const div = document.createElement('div');
//     new Component({
//       target: div,
//       props: props
//     });
//     return div.innerHTML;
//   }

async function toggleDataCenters() {
  showDataCenters = !showDataCenters;

  if (showDataCenters) {
    if (dataCentersLoaded) {
      if (map.getLayer('data-centers-layer')) {
        map.setLayoutProperty('data-centers-layer', 'visibility', 'visible');
      }
    } else {
      dataCentersLoading = true;
      dataCentersError = null;
      
      try {
        const res = await fetch('http://localhost:8001/api/geojson?table_name=osm_data_centers');
        if (!res.ok) throw new Error("API Error");
        
        dataCenters = await res.json();
        const dcData = dataCenters;
        
        if (!dcData.features || dcData.features.length === 0) {
          dataCentersError = "No data centers found.";
          showDataCenters = false;
          dataCentersLoading = false;
          return;
        }

        if (map.getSource('data-centers-source')) {
            map.removeLayer('data-centers-layer');
            map.removeSource('data-centers-source');
        }

        map.addSource('data-centers-source', {
          type: 'geojson',
          data: dcData
        });

        map.addLayer({
          id: 'data-centers-layer',
          type: 'circle',
          source: 'data-centers-source',
          paint: {
            'circle-radius': 4,
            'circle-color': '#ff4d00',
            'circle-stroke-width': 1.5,
            'circle-stroke-color': '#ffffff'
          }
        });

        // Click Handler using Svelte Component (Direct Rendering)
        // map.on('click', 'data-centers-layer', async (e) => {
        //   const props = e.features[0].properties;
        //   const lat = e.lngLat.lat;
        //   const lon = e.lngLat.lng;

        //   // 1. Create Popup with a temporary container
        //   const popup = new maplibregl.Popup({ offset: 25, closeButton: true })
        //     .setLngLat(e.lngLat)
        //     .setHTML('<div style="padding:1rem; min-width:250px;">🔄 Fetching local MP...</div>')
        //     .addTo(map);

        //   // 2. Wait for popup to be in DOM, then replace content with Svelte Component
        //   setTimeout(async () => {
        //     const popupContentElement = popup.getElement().querySelector('.maplibregl-popup-content');
            
        //     if (popupContentElement) {
        //       // Clear loading text
        //       popupContentElement.innerHTML = '';
              
        //       // Mount Loading State Component
        //       // FIX: Pass properties directly inside the 'props' object, not nested
        //       const loadingComponent = new DataCenterInfo({
        //         target: popupContentElement,
        //         props: {
        //           name: props.name || 'Unknown',
        //           operator: props.operator || 'N/A',
        //           isLoadingMp: true
        //           // Do NOT wrap these in another { props: ... }
        //         }
        //       });

        //       // 3. Fetch MP Data
        //       const mpInfo = await getMpInfo(lat, lon);
              
        //       // 4. Update Component Props (Reactive Update)
        //       loadingComponent.$set({
        //         isLoadingMp: false,
        //         mpInfo: mpInfo
        //       });


        //       // 5. HIGHLIGHT CONSTITUENCY
        //       if (mpInfo && mpInfo.constituency) {
        //           const constName = mpInfo.constituency;
                  
        //           // Only fetch if it's a different constituency than currently highlighted
        //           if (highlightedConstituencyName !== constName) {
        //               try {
        //                   const constRes = await fetch(`http://localhost:8001/api/constituency/${encodeURIComponent(constName)}`);
        //                   const constData = await constRes.json();
                          
        //                   if (constData.features.length > 0) {
        //                       // Remove old highlight if exists
        //                       if (map.getSource('highlight-source')) {
        //                           map.removeLayer('highlight-layer');
        //                           map.removeSource('highlight-source');
        //                       }

        //                       // Add new highlight
        //                       map.addSource('highlight-source', {
        //                           type: 'geojson',
        //                           data: constData
        //                       });

        //                       map.addLayer({
        //                           id: 'highlight-layer',
        //                           type: 'fill',
        //                           source: 'highlight-source',
        //                           paint: {
        //                               'fill-color': '#ff9800', // Orange highlight
        //                               'fill-opacity': 0.3,
        //                               'fill-outline-color': '#e65100'
        //                           }
        //                       }, 'data-centers-layer'); // Insert below data centers

        //                       // Fit bounds to the constituency
        //                       const bounds = new maplibregl.LngLatBounds();
        //                       constData.features[0].geometry.coordinates.forEach(coord => {
        //                           // Handle MultiPolygon coordinates structure
        //                           if (Array.isArray(coord)) {
        //                               coord[0].forEach(point => bounds.extend(point));
        //                           }
        //                       });
                              
        //                       map.fitBounds(bounds, { padding: 50, duration: 1000 });
                              
        //                       highlightedConstituencyName = constName;
        //                   }
        //               } catch (err) {
        //                   console.warn("Could not highlight constituency:", err);
        //               }
        //           }
        //       }
              
        //       // Cleanup when popup closes
        //       popup.on('close', () => {
        //         loadingComponent.$destroy();
        //       });
        //     }
        //   }, 0);
        // });

        // Store reference to the current highlight to clean it up properly
        let currentHighlightSourceId = 'constituency-highlight-source';
        let currentHighlightLayerId = 'constituency-highlight-layer';

        map.on('click', 'data-centers-layer', async (e) => {
          const props = e.features[0].properties;
          const lat = e.lngLat.lat;
          const lon = e.lngLat.lng;

          // 1. Create Popup immediately with loading state
          const popup = new maplibregl.Popup({ offset: 25, closeButton: true, maxWidth: '300px' })
            .setLngLat(e.lngLat)
            .setHTML('<div style="padding:1rem; text-align:center;">🔄 Finding MP & Boundary...</div>')
            .addTo(map);

          // Cleanup function for when popup closes
          const cleanupHighlight = () => {
            if (map.getSource(currentHighlightSourceId)) {
              map.removeLayer(currentHighlightLayerId);
              map.removeSource(currentHighlightSourceId);
            }
          };
          
          popup.on('close', cleanupHighlight);

          try {
            // 2. Fetch MP Data (which includes constituency name)
            const mpResponse = await fetch(`http://localhost:8001/api/constituency-mp?lat=${lat}&lon=${lon}`);
            const mpData = await mpResponse.json();

            if (!mpData.found) {
              popup.setHTML('<div style="padding:1rem;">No MP data found for this location.</div>');
              return;
            }

            // 3. Render Svelte Component into Popup
            const popupContentElement = popup.getElement().querySelector('.maplibregl-popup-content');
            if (popupContentElement) {
              popupContentElement.innerHTML = '';
              
              const loadingComponent = new DataCenterInfo({
                target: popupContentElement,
                props: {
                  name: props.name || 'Unknown',
                  operator: props.operator || 'N/A',
                  isLoadingMp: true
                }
              });

              // Update component once MP data is ready
              loadingComponent.$set({
                isLoadingMp: false,
                mpInfo: {
                  constituency: mpData.constituency,
                  mp: mpData.mp_name,
                  party: mpData.party,
                  current_position: mpData.current_position,
                  color: getPartyColor(mpData.party) // Helper function needed in script
                }
              });
            }

            // 4. Highlight Constituency Boundary
            if (mpData.constituency && mpData.constituency !== "Unknown") {
              // Remove previous highlight if exists
              if (map.getSource(currentHighlightSourceId)) {
                map.removeLayer(currentHighlightLayerId);
                map.removeSource(currentHighlightSourceId);
              }

              // Fetch Geometry for the specific constituency
              // We encode URI component to handle spaces/special chars in names safely
              const geomUrl = `http://localhost:8001/api/constituency/${encodeURIComponent(mpData.constituency)}`;
              const geomRes = await fetch(geomUrl);
              
              if (geomRes.ok) {
                const geomData = await geomRes.json();
                
                if (geomData.features && geomData.features.length > 0) {
                  // Add Source
                  map.addSource(currentHighlightSourceId, {
                    type: 'geojson',
                    data: geomData
                  });

                  // Add Layer (Orange Fill, Red Outline)
                  map.addLayer({
                    id: currentHighlightLayerId,
                    type: 'fill',
                    source: currentHighlightSourceId,
                    paint: {
                      'fill-color': '#ff9800',
                      'fill-opacity': 0.4,
                      'fill-outline-color': '#e65100'
                    }
                  });

                  // Calculate Bounds
                  const bounds = new maplibregl.LngLatBounds();
                  geomData.features.forEach(feature => {
                    // Simple coordinate extraction for bounds
                    // Note: For complex MultiPolygons, a library like turf.js is better, 
                    // but this works for standard GeoJSON features from PostGIS
                    const coords = feature.geometry.coordinates;
                    // Flatten slightly to find min/max manually or rely on MapLibre's internal logic if available
                    // A robust way without Turf:
                    JSON.stringify(coords).match(/[-+]?\d*\.?\d+/g)?.forEach(num => {
                      const val = parseFloat(num);
                      // This regex approach is risky for mixed lat/lon. 
                      // Better: Use a simple loop or assume PostGIS returns valid Polygons
                    });
                    
                    // Robust manual bounds calculation for MultiPolygon
                    const traverse = (coord) => {
                        if (typeof coord[0] === 'number') {
                            bounds.extend([coord[0], coord[1]]);
                        } else {
                            coord.forEach(traverse);
                        }
                    };
                    traverse(coords);
                  });

                  // Only fit if bounds are valid
                  if (!bounds.isEmpty()) {
                    // Small delay to ensure layer render and popup stability
                    setTimeout(() => {
                      map.fitBounds(bounds, {
                        padding: { top: 50, bottom: 50, left: 50, right: 50 },
                        duration: 1500, // Smooth animation
                        maxZoom: 10 // Prevent zooming in too close
                      });
                    }, 100);
                  }
                }
              }
            }

          } catch (err) {
            console.error("Error fetching details:", err);
            popup.setHTML('<div style="padding:1rem; color:red;">Error loading data.</div>');
          }
        });

        // Helper for party colors (ensure this exists in your script scope)
        function getPartyColor(party) {
          if (!party) return '#ccc';
          const p = party.toLowerCase();
          if (p.includes('labour')) return '#DC241f';
          if (p.includes('conservative')) return '#0087DC';
          if (p.includes('liberal')) return '#FDBB30';
          if (p.includes('green')) return '#6AB023';
          if (p.includes('snp')) return '#FFF200';
          return '#999999';
        }

        map.on('mouseenter', 'data-centers-layer', () => {
          map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'data-centers-layer', () => {
          map.getCanvas().style.cursor = '';
        });

        dataCentersLoaded = true;
        dataCentersLoading = false;

      } catch (err) {
        console.error(err);
        dataCentersError = "Failed to load data centers.";
        showDataCenters = false;
        dataCentersLoading = false;
      }
    }
  } else {
    if (map.getLayer('data-centers-layer')) {
      map.setLayoutProperty('data-centers-layer', 'visibility', 'none');
    }
  }
}

  async function toggleCounties() {
    showCounties = !showCounties;
    
    if (showCounties) {
        if (!countiesLoaded) {
            try {
                const response = await fetch('http://localhost:8001/api/counties');
                const data = await response.json();
                
                if (data && Array.isArray(data.features)) {
                    countyData = data;
                    countiesLoaded = true;
                    
                    if (countyData.features.length === 0) {
                        showCounties = false;
                        return;
                    }

                    map.addSource('counties', {
                        type: 'geojson',
                        data: countyData
                    });

                    map.addLayer({
                        id: 'counties-fill',
                        type: 'fill',
                        source: 'counties',
                        paint: {
                            'fill-color': '#ffffff',
                            'fill-opacity': 0.1
                        }
                    });

                    map.addLayer({
                        id: 'counties-line',
                        type: 'line',
                        source: 'counties',
                        paint: {
                            'line-color': '#000000',
                            'line-width': 1,
                            'line-dasharray': [2, 2]
                        }
                    });
                } else {
                    showCounties = false;
                }
            } catch (err) {
                console.error("Error loading counties:", err);
                showCounties = false;
            }
        } else {
            map.setLayoutProperty('counties-fill', 'visibility', 'visible');
            map.setLayoutProperty('counties-line', 'visibility', 'visible');
        }
    } else {
        if (map.getLayer('counties-fill')) {
            map.setLayoutProperty('counties-fill', 'visibility', 'none');
            map.setLayoutProperty('counties-line', 'visibility', 'none');
        }
    }
}

// async function toggleConstituencies() {
//     showConstituencies = !showConstituencies;
    
//     if (showConstituencies) {
//         if (!constituenciesLoaded) {
//             try {
//                 const response = await fetch('http://localhost:8001/api/parliamentary-constituencies');
//                 const data = await response.json();
                
//                 if (data && Array.isArray(data.features)) {
//                     if (data.features.length === 0) {
//                         showConstituencies = false;
//                         return;
//                     }

//                     map.addSource('constituencies', {
//                         type: 'geojson',
//                         data: data
//                     });

//                     // Style: Subtle white borders, very low opacity fill
//                     map.addLayer({
//                         id: 'constituencies-fill',
//                         type: 'fill',
//                         source: 'constituencies',
//                         paint: {
//                             'fill-color': '#ffffff',
//                             'fill-opacity': 0.05 // Very transparent
//                         }
//                     });

//                     map.addLayer({
//                         id: 'constituencies-line',
//                         type: 'line',
//                         source: 'constituencies',
//                         paint: {
//                             'line-color': '#ffffff',
//                             'line-width': 1,
//                             'line-dasharray': [2, 2], // Dashed line
//                             'line-opacity': 0.6
//                         }
//                     });
                    
//                     constituenciesLoaded = true;
//                 } else {
//                     showConstituencies = false;
//                 }
//             } catch (err) {
//                 console.error("Error loading constituencies:", err);
//                 showConstituencies = false;
//             }
//         } else {
//             // Just show existing layer
//             map.setLayoutProperty('constituencies-fill', 'visibility', 'visible');
//             map.setLayoutProperty('constituencies-line', 'visibility', 'visible');
//         }
//     } else {
//         // Hide layer
//         if (map.getLayer('constituencies-fill')) {
//             map.setLayoutProperty('constituencies-fill', 'visibility', 'none');
//             map.setLayoutProperty('constituencies-line', 'visibility', 'none');
//         }
//     }
// }

  async function toggleParliamentary() {
    showParliamentary = !showParliamentary;

    if (showParliamentary) {
      if (!parliamentaryLoaded) {
        parliamentaryLoading = true;
        try {
          const response = await fetch('http://localhost:8001/api/parliamentary-boundaries');
          const data = await response.json();

          if (data && Array.isArray(data.features)) {
            parliamentaryLoaded = true;
            
            if (data.features.length === 0) {
              showParliamentary = false;
              parliamentaryLoading = false;
              return;
            }

            map.addSource('parliamentary-boundaries', {
              type: 'geojson',
              data: data
            });

            // Add Fill Layer (Very subtle)
            map.addLayer({
              id: 'parliamentary-fill',
              type: 'fill',
              source: 'parliamentary-boundaries',
              paint: {
                'fill-color': '#ffffff',
                'fill-opacity': 0.05 // Very transparent
              }
            });

            // Add Line Layer (Clearer definition)
            map.addLayer({
              id: 'parliamentary-line',
              type: 'line',
              source: 'parliamentary-boundaries',
              paint: {
                'line-color': '#ffffff',
                'line-width': 1,
                'line-dasharray': [3, 2], // Dashed line
                'line-opacity': 0.6
              }
            });
          } else {
            showParliamentary = false;
          }
        } catch (err) {
          console.error("Error loading parliamentary boundaries:", err);
          showParliamentary = false;
        } finally {
          parliamentaryLoading = false;
        }
      } else {
        // Just show existing layer
        map.setLayoutProperty('parliamentary-fill', 'visibility', 'visible');
        map.setLayoutProperty('parliamentary-line', 'visibility', 'visible');
      }
    } else {
      // Hide layer
      if (map.getLayer('parliamentary-fill')) {
        map.setLayoutProperty('parliamentary-fill', 'visibility', 'none');
        map.setLayoutProperty('parliamentary-line', 'visibility', 'none');
      }
    }
  }
</script>

<main>
  <!-- Left Sidebar -->
  <aside class="sidebar">
    <header>
      <h1>Watershed Democracy</h1>
      <p class="subtitle">PostGIS + MapLibre PWA</p>
    </header>

    <div class="content">
      <p>
        Welcome to the Watershed Democracy platform. This interactive map visualizes geographical data stored in a PostGIS database, 
        rendered efficiently using MapLibre GL.
      </p>
      <p>
        Use the controls below to toggle additional data layers. You can view administrative boundaries 
        or explore infrastructure locations such as data centers across the United Kingdom.
      </p>

      <div class="controls">
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

        <div class="toggle-container">
          <label class="switch-label">
            <span>Counties</span>
            <div class="switch-wrapper">
              <input 
                type="checkbox" 
                checked={showCounties} 
                on:change={toggleCounties}
              >
              <span class="slider"></span>
            </div>
          </label>
        </div>

        <!-- <div class="toggle-container">
          <label class="switch-label">
            <span>Parliamentary Boundaries</span>
            <div class="switch-wrapper">
              <input 
                type="checkbox" 
                checked={showConstituencies} 
                on:change={toggleConstituencies}
              >
              <span class="slider"></span>
            </div>
          </label>
        </div> -->
        <div class="toggle-container">
          <label class="switch-label">
            <span>Parliamentary Constituencies</span>
            <div class="switch-wrapper">
              <input 
                type="checkbox" 
                checked={showParliamentary} 
                on:change={toggleParliamentary}
                disabled={parliamentaryLoading}
              >
              <span class="slider"></span>
            </div>
          </label>
          {#if parliamentaryLoading}
            <span class="loading-text">Loading...</span>
          {/if}
        </div>
      </div>
    </div>
  </aside>

  <!-- Right Map Area -->
  <div class="map-container" bind:this={mapWrapper}>
    {#if loading}
      <div class="overlay">Loading map...</div>
    {:else if error}
      <div class="overlay error">Error: {error}</div>
    {/if}
    
    {#if !loading && !error}
      <div class="info-panel">
        <h3>Data Centers: {dataCenters?.features?.length || 0}</h3>
      </div>
    {/if}
  </div>
</main>

<style>
  :global(body) { 
    margin: 0; 
    padding: 0; 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
    box-sizing: border-box;
  }

  *, *:before, *:after {
    box-sizing: inherit;
  }

  main { 
    display: flex; 
    height: 100vh; 
    width: 100vw;
    overflow: hidden;
  }

  /* Sidebar Styles */
  .sidebar {
    width: 400px;
    background: #f8f9fa;
    border-right: 1px solid #ddd;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    z-index: 10;
    box-shadow: 2px 0 5px rgba(0,0,0,0.05);
  }

  header {
    background: linear-gradient(135deg, #4a90d9, #2c5aa0);
    color: white;
    padding: 1.5rem;
    flex-shrink: 0;
  }

  h1 { 
    margin: 0; 
    font-size: 1.5rem; 
    line-height: 1.2;
  }

  .subtitle { 
    margin: 0.5rem 0 0; 
    opacity: 0.9; 
    font-size: 0.9rem; 
    font-weight: normal;
  }

  .content {
    padding: 1.5rem;
    overflow-y: auto;
    flex: 1;
  }

  .content p {
    line-height: 1.6;
    color: #333;
    margin-bottom: 1.5rem;
    font-size: 0.95rem;
  }

  .controls {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 1px solid #e0e0e0;
  }

  /* Toggle Styles */
  .toggle-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .switch-label {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    font-size: 1rem;
    font-weight: 500;
    color: #444;
    flex: 1;
  }

  .switch-wrapper {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 24px;
    flex-shrink: 0;
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
    transition: .3s;
    border-radius: 24px;
  }

  .slider:before {
    position: absolute;
    content: "";
    height: 20px;
    width: 20px;
    left: 2px;
    bottom: 2px;
    background-color: white;
    transition: .3s;
    border-radius: 50%;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  }

  input:checked + .slider {
    background-color: #2c5aa0;
  }

  input:checked + .slider:before {
    transform: translateX(20px);
  }

  input:disabled + .slider {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .loading-text { font-size: 0.8rem; font-style: italic; color: #666; }
  .error-text { font-size: 0.8rem; color: #d32f2f; font-weight: 500; }

  /* Map Container Styles */
  .map-container {
    flex: 1;
    position: relative;
    min-width: 0; /* Prevents flex item overflow */
    background: #eee;
  }

  .overlay {
    position: absolute; 
    top: 0; left: 0; right: 0; bottom: 0;
    display: flex; 
    align-items: center; 
    justify-content: center;
    font-size: 1.2rem; 
    background: rgba(255,255,255,0.9);
    z-index: 5; 
    pointer-events: none;
  }
  
  .error { 
    color: #d32f2f; 
    background: rgba(255, 235, 238, 0.95); 
    pointer-events: auto; 
    font-weight: 500;
  }
  
  .info-panel {
    position: absolute;
    bottom: 20px;
    right: 20px;
    background: white;
    padding: 0.75rem 1rem;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    font-size: 0.9rem;
    z-index: 5;
    pointer-events: none;
  }

  .info-panel h3 { 
    margin: 0; 
    color: #333; 
    font-weight: 600;
  }

  /* Responsive Design */
  @media (max-width: 768px) {
    main {
      flex-direction: column;
    }
    
    .sidebar {
      width: 100%;
      height: auto;
      max-height: 40vh;
      border-right: none;
      border-bottom: 1px solid #ddd;
    }

    .content {
      padding: 1rem;
    }

    .content p {
      font-size: 0.9rem;
      margin-bottom: 1rem;
    }

    header {
      padding: 1rem;
    }

    h1 {
      font-size: 1.25rem;
    }
  }
</style>