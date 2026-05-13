<script>
  export let name = "Unknown Data Center";
  export let operator = "N/A";
  export let mpInfo = null;
  export let isLoadingMp = false;

</script>

<div class="popup-content">
  <div class="popup-image-container">
    <img src="https://placehold.co/300x150/2c5aa0/ffffff?text=Data+Center" alt="Data Center" />
  </div>
  
  <div class="popup-body">
    <h3>{name}</h3>
    <p class="popup-operator"><strong>Operator:</strong> {operator}</p>
    <p class="popup-desc">
      Critical infrastructure node providing cloud computing and storage services.
    </p>

    {#if isLoadingMp}
      <div class="popup-mp-section loading">
        🔄 Fetching local MP...
      </div>
    {:else if mpInfo}
      <div class="popup-mp-section">
      <h4>🏛️ Representation</h4>
      <p><strong>Constituency:</strong> {mpInfo.constituency}</p>
      <p><strong>MP:</strong> {mpInfo.mp}</p>
      
      {#if mpInfo.party}
        <p>
          <strong>Party:</strong> 
          <span style="background-color: {mpInfo.colour || '#ccc'}; color: #333; padding: 2px 6px; border-radius: 4px; font-size: 0.85rem;">
            {mpInfo.party}
          </span>
        </p>
        {#if mpInfo.current_position}
            <p class="mp-role"><small>🏅 {mpInfo.current_position}</small></p>
          {/if}
      {/if}
    </div>
    {:else}
      <div class="popup-mp-section">
        <h4>🏛️ Representation</h4>
        <p><em>MP data not available for this location.</em></p>
      </div>
    {/if}

    <div class="popup-stats">
      <span>🔌 Redundant Power</span>
      <span>❄️ Cooling</span>
      <span>🛡️ Secure</span>
    </div>
  </div>
</div>

<style>
  /* Scoped styles for the popup content */
  .popup-content { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
  .popup-image-container { width: 100%; height: 150px; background: #eee; overflow: hidden; }
  .popup-image-container img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .popup-body { padding: 1rem; background: white; }
  .popup-body h3 { margin: 0 0 0.5rem 0; font-size: 1.1rem; color: #2c5aa0; line-height: 1.3; }
  .popup-operator { font-size: 0.85rem; color: #666; margin-bottom: 0.75rem; }
  .popup-desc { font-size: 0.9rem; color: #444; line-height: 1.5; margin-bottom: 1rem; }
  
  .popup-mp-section {
    background: #f8f9fa; border: 1px solid #e9ecef;
    border-radius: 6px; padding: 0.75rem; margin: 1rem 0;
  }
  .popup-mp-section.loading { text-align: center; color: #666; font-style: italic; }
  .popup-mp-section h4 { margin: 0 0 0.5rem 0; font-size: 0.9rem; color: #2c5aa0; border-bottom: 1px solid #dee2e6; padding-bottom: 0.25rem; }
  .popup-mp-section p { margin: 0.25rem 0; font-size: 0.85rem; color: #333; }
  .mp-note { margin-top: 0.5rem !important; color: #888 !important; font-style: italic; }
  
  .popup-stats { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
  .popup-stats span { font-size: 0.75rem; background: #f0f4f8; color: #2c5aa0; padding: 0.25rem 0.5rem; border-radius: 12px; font-weight: 600; }
</style>