<script>
  import { createEventDispatcher } from 'svelte';

  /** [{ key, label, swatch: 'dot'|'line'|'dash', color, cap? }] */
  export let layers = [];
  /** { [key]: { visible, loading, error, count } } */
  export let state = {};

  const dispatch = createEventDispatcher();
</script>

<section class="layers" aria-labelledby="layers-heading">
  <h2 id="layers-heading">Layers</h2>
  <ul>
    {#each layers as layer (layer.key)}
      {@const s = state[layer.key]}
      <li>
        <label>
          <span class="swatch {layer.swatch}" style="--c: {layer.color}" aria-hidden="true"></span>
          <span class="text">
            <span class="label">{layer.label}</span>
            {#if s.loading}
              <span class="status">Loading…</span>
            {:else if s.error}
              <span class="status error">{s.error}</span>
            {:else if s.count != null}
              <span class="status">
                {s.count.toLocaleString()} shown{#if layer.cap && s.count >= layer.cap}&nbsp;(capped){/if}
              </span>
            {/if}
          </span>
          <span class="switch">
            <input
              type="checkbox"
              checked={s.visible}
              disabled={s.loading}
              on:change={() => dispatch('toggle', layer.key)}
            />
            <span class="slider"></span>
          </span>
        </label>
      </li>
    {/each}
  </ul>
</section>

<style>
  h2 {
    margin: 0 0 0.5rem;
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--muted);
  }

  ul { list-style: none; margin: 0; padding: 0; }
  li + li { border-top: 1px solid var(--line); }

  label {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    padding: 0.6rem 0;
    cursor: pointer;
  }

  .text { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  .label { font-size: 0.92rem; font-weight: 500; color: var(--ink); }
  .status { font-size: 0.78rem; color: var(--muted); }
  .status.error { color: var(--danger); }

  .swatch { flex-shrink: 0; width: 14px; height: 14px; }
  .swatch.dot { border-radius: 50%; background: var(--c); box-shadow: 0 0 0 2px #fff, 0 0 0 3px rgba(0,0,0,0.15); }
  .swatch.line { height: 0; border-top: 2px dashed var(--c); }
  .swatch.dash { height: 0; border-top: 2px dotted var(--c); }

  .switch { position: relative; width: 40px; height: 22px; flex-shrink: 0; }
  .switch input { position: absolute; opacity: 0; width: 100%; height: 100%; margin: 0; cursor: pointer; }
  .slider {
    position: absolute; inset: 0;
    background: #c7ccd3;
    border-radius: 22px;
    transition: background 0.2s;
    pointer-events: none;
  }
  .slider::before {
    content: '';
    position: absolute;
    width: 18px; height: 18px;
    left: 2px; top: 2px;
    background: #fff;
    border-radius: 50%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.25);
    transition: transform 0.2s;
  }
  input:checked + .slider { background: var(--brand); }
  input:checked + .slider::before { transform: translateX(18px); }
  input:focus-visible + .slider { outline: 2px solid var(--brand-2); outline-offset: 2px; }
  input:disabled + .slider { opacity: 0.5; }
</style>
