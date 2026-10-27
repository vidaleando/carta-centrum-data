<script>
  import { createEventDispatcher } from 'svelte';
  import { dcLabel } from '../lib/geo.js';
  import { textOn } from '../lib/party.js';

  /**
   * null, or { dc, status: 'loading'|'ready'|'outside'|'error', mp?, message?, neighbours? }
   * where neighbours are the other loaded data-centre features in the same constituency.
   */
  export let selected = null;

  const dispatch = createEventDispatcher();
  const MAX_NEIGHBOURS = 10;
  let showAllNeighbours = false;

  $: dc = selected?.dc;
  $: if (dc) showAllNeighbours = false;
  $: osmUrl = dc?.id && /^(node|way|relation)\/\d+$/.test(dc.id) ? `https://www.openstreetmap.org/${dc.id}` : null;
  $: neighbours = selected?.neighbours ?? [];
  $: visibleNeighbours = showAllNeighbours ? neighbours : neighbours.slice(0, MAX_NEIGHBOURS);
</script>

{#if !selected}
  <section class="empty">
    <p>Select a data centre on the map, or search for one by name, to see which constituency it sits in and who represents it.</p>
  </section>
{:else}
  <section class="detail" aria-live="polite">
    <header>
      <div>
        <p class="kicker">Data centre</p>
        <h2>{dcLabel(dc)}</h2>
      </div>
      <button class="close" type="button" on:click={() => dispatch('close')} aria-label="Clear selection">×</button>
    </header>

    <dl class="facts">
      <dt>Operator</dt>
      <dd>{dc.operator || 'Not recorded'}</dd>
      <dt>Location</dt>
      <dd>{dc.coordinates[1].toFixed(4)}, {dc.coordinates[0].toFixed(4)}</dd>
      {#if osmUrl}
        <dt>Source</dt>
        <dd><a href={osmUrl} target="_blank" rel="noopener">OpenStreetMap {dc.id}</a></dd>
      {/if}
    </dl>

    <div class="block">
      <h3>Representation</h3>
      {#if selected.status === 'loading'}
        <p class="muted">Finding constituency and MP…</p>
      {:else if selected.status === 'outside'}
        <p class="muted">{selected.message || 'This location is not inside a UK parliamentary constituency.'}</p>
      {:else if selected.status === 'error'}
        <p class="error">Couldn’t load representation data. Try again in a moment.</p>
      {:else}
        <p class="constituency">{selected.mp.constituency}</p>
        <div class="mp">
          <span class="mp-name">{selected.mp.mp_name}</span>
          {#if selected.mp.party}
            <span class="party" style="background: {selected.mp.color}; color: {textOn(selected.mp.color)}">{selected.mp.party}</span>
          {/if}
        </div>
        {#if selected.mp.current_position && selected.mp.current_position !== 'Member'}
          <p class="muted role">{selected.mp.current_position}</p>
        {/if}
      {/if}
    </div>

    {#if selected.status === 'ready' && selected.neighbours}
      <div class="block">
        <h3>Same constituency</h3>
        {#if neighbours.length === 0}
          <p class="muted">No other mapped data centres in this constituency.</p>
        {:else}
          <p class="muted">
            {neighbours.length} other mapped data centre{neighbours.length === 1 ? '' : 's'} in {selected.mp.constituency}:
          </p>
          <ul class="neighbours">
            {#each visibleNeighbours as feature}
              <li>
                <button type="button" on:click={() => dispatch('select', feature)}>
                  {dcLabel(feature.properties || {})}
                </button>
              </li>
            {/each}
          </ul>
          {#if neighbours.length > MAX_NEIGHBOURS && !showAllNeighbours}
            <button class="more" type="button" on:click={() => (showAllNeighbours = true)}>
              Show all {neighbours.length}
            </button>
          {/if}
        {/if}
      </div>
    {/if}
  </section>
{/if}

<style>
  .empty p { margin: 0; font-size: 0.9rem; line-height: 1.5; color: var(--muted); }

  header { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; }
  .kicker {
    margin: 0;
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--accent);
    font-weight: 700;
  }
  h2 { margin: 0.15rem 0 0; font-size: 1.15rem; line-height: 1.3; color: var(--ink); overflow-wrap: anywhere; }

  .close {
    flex-shrink: 0;
    width: 30px; height: 30px;
    border: 0;
    border-radius: 6px;
    background: var(--surface-2);
    font-size: 1.2rem;
    line-height: 1;
    color: var(--muted);
    cursor: pointer;
  }
  .close:hover { color: var(--ink); }

  .facts {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.3rem 0.75rem;
    margin: 0.85rem 0 0;
    font-size: 0.85rem;
  }
  dt { color: var(--muted); }
  dd { margin: 0; color: var(--ink); overflow-wrap: anywhere; }
  a { color: var(--brand); }

  .block { margin-top: 1rem; padding-top: 0.85rem; border-top: 1px solid var(--line); }
  h3 {
    margin: 0 0 0.45rem;
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--muted);
  }
  .block p { margin: 0; font-size: 0.85rem; line-height: 1.45; }

  .constituency { font-size: 1rem !important; font-weight: 600; color: var(--ink); }
  .mp { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem; margin-top: 0.3rem; }
  .mp-name { font-size: 0.92rem; color: var(--ink); }
  .party { font-size: 0.75rem; font-weight: 600; padding: 0.1rem 0.45rem; border-radius: 4px; }
  .role { margin-top: 0.3rem !important; }

  .muted { color: var(--muted); }
  .error { color: var(--danger); }

  .neighbours { list-style: none; margin: 0.4rem 0 0; padding: 0; }
  .neighbours button, .more {
    border: 0;
    background: none;
    padding: 0.25rem 0;
    font: inherit;
    font-size: 0.85rem;
    color: var(--brand);
    text-align: left;
    cursor: pointer;
  }
  .neighbours button:hover, .more:hover { text-decoration: underline; }
  .more { font-weight: 600; }
</style>
