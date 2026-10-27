<script>
  import { createEventDispatcher } from 'svelte';
  import { dcLabel } from '../lib/geo.js';

  /** Point features to search (data centres). */
  export let items = [];

  const dispatch = createEventDispatcher();
  const MAX_RESULTS = 8;

  let query = '';
  let open = false;
  let active = 0;

  $: q = query.trim().toLowerCase();
  $: results = q.length < 2 ? [] : items
    .filter((f) => {
      const p = f.properties || {};
      return (p.name || '').toLowerCase().includes(q) || (p.operator || '').toLowerCase().includes(q);
    })
    .slice(0, MAX_RESULTS);
  $: if (results) active = 0;

  function choose(feature) {
    dispatch('select', feature);
    query = '';
    open = false;
  }

  function onKeydown(e) {
    if (e.key === 'ArrowDown' && results.length) {
      e.preventDefault();
      active = (active + 1) % results.length;
    } else if (e.key === 'ArrowUp' && results.length) {
      e.preventDefault();
      active = (active - 1 + results.length) % results.length;
    } else if (e.key === 'Enter' && results[active]) {
      e.preventDefault();
      choose(results[active]);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      query = '';
      open = false;
    }
  }
</script>

<div class="search">
  <input
    type="search"
    placeholder={items.length ? 'Search data centres by name or operator…' : 'Loading data centres…'}
    disabled={!items.length}
    bind:value={query}
    on:focus={() => (open = true)}
    on:input={() => (open = true)}
    on:blur={() => setTimeout(() => (open = false), 150)}
    on:keydown={onKeydown}
    role="combobox"
    aria-expanded={open && q.length >= 2}
    aria-controls="search-results"
    aria-autocomplete="list"
    autocomplete="off"
  />
  {#if open && q.length >= 2}
    <ul id="search-results" role="listbox">
      {#each results as feature, i}
        <li role="option" aria-selected={i === active}>
          <button
            type="button"
            class:active={i === active}
            on:mousedown|preventDefault={() => choose(feature)}
            on:mouseenter={() => (active = i)}
          >
            <span class="name">{dcLabel(feature.properties || {})}</span>
            {#if feature.properties?.operator && feature.properties?.name}
              <span class="meta">{feature.properties.operator}</span>
            {/if}
          </button>
        </li>
      {:else}
        <li class="empty">No mapped data centres match “{query.trim()}”.</li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .search { position: relative; width: 100%; }

  input {
    width: 100%;
    font: inherit;
    font-size: 0.95rem;
    padding: 0.55rem 0.8rem;
    border: 1px solid transparent;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.95);
    color: var(--ink);
  }
  input:focus { outline: 2px solid var(--brand-2); outline-offset: 1px; background: #fff; }
  input:disabled { opacity: 0.7; }

  ul {
    position: absolute;
    top: calc(100% + 4px);
    left: 0; right: 0;
    margin: 0; padding: 4px;
    list-style: none;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    z-index: 20;
    max-height: 60vh;
    overflow-y: auto;
  }

  button {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    width: 100%;
    padding: 0.45rem 0.6rem;
    border: 0;
    border-radius: 6px;
    background: none;
    font: inherit;
    text-align: left;
    cursor: pointer;
    color: var(--ink);
  }
  button.active { background: var(--surface-2); }
  .name { font-size: 0.9rem; font-weight: 600; }
  .meta { font-size: 0.8rem; color: var(--muted); }
  .empty { padding: 0.6rem; font-size: 0.85rem; color: var(--muted); }
</style>
