<script>
  import { supabase } from '../lib/supabase.js';

  let email = '';
  let state = 'idle'; // idle | sending | sent | error
  let message = '';

  // Supabase reports a used or expired link in the URL fragment.
  const params = new URLSearchParams(window.location.hash.slice(1));
  if (params.get('error')) {
    message = params.get('error_code') === 'otp_expired'
      ? 'That link has expired or was already used. Request a new one below.'
      : 'That link didn’t work. Request a new one below.';
    history.replaceState(null, '', window.location.pathname);
  }

  async function sendLink() {
    state = 'sending';
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      // Never create accounts here: only invited people can sign in.
      options: { shouldCreateUser: false, emailRedirectTo: window.location.origin }
    });
    // Don't reveal whether an address has been invited: same message either way,
    // unless Supabase is rate limiting.
    if (error && error.status === 429) {
      state = 'error';
      message = 'Too many requests. Please wait a few minutes and try again.';
    } else {
      state = 'sent';
    }
  }
</script>

<main class="signin">
  <div class="card">
    <h1>Carta Magna</h1>
    <p class="tagline">UK data centres and who represents them</p>

    {#if state === 'sent'}
      <p class="note">
        If <strong>{email.trim()}</strong> has been invited, a sign-in link is on its way. It’s valid for one hour.
      </p>
      <button class="link" type="button" on:click={() => { state = 'idle'; message = ''; }}>Use a different email</button>
    {:else}
      <p>Access is by invitation. Open the link in your invite email, or enter your email for a new sign-in link.</p>
      {#if message}<p class="note warn" role="alert">{message}</p>{/if}
      <form on:submit|preventDefault={sendLink}>
        <label for="email">Email</label>
        <input id="email" type="email" bind:value={email} required autocomplete="email" placeholder="you@example.com" />
        <button type="submit" disabled={state === 'sending'}>
          {state === 'sending' ? 'Sending…' : 'Email me a sign-in link'}
        </button>
      </form>
    {/if}
  </div>
</main>

<style>
  .signin {
    min-height: 100vh;
    display: grid;
    place-items: center;
    padding: 1rem;
    box-sizing: border-box;
    background: linear-gradient(135deg, #4a90d9, #2c5aa0);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #1f2933;
  }
  .card {
    width: 100%;
    max-width: 380px;
    padding: 1.75rem;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 12px 40px rgba(15, 23, 42, 0.25);
  }
  h1 { margin: 0; font-size: 1.5rem; color: #2c5aa0; }
  .tagline { margin: 0.2rem 0 1.25rem; font-size: 0.85rem; color: #5f6b7a; }
  p { font-size: 0.92rem; line-height: 1.5; }
  .note { padding: 0.6rem 0.75rem; border-radius: 8px; background: #f3f5f8; }
  .warn { background: #fff4e5; color: #8a4b00; }
  form { display: grid; gap: 0.5rem; margin-top: 1rem; }
  label { font-size: 0.8rem; font-weight: 600; color: #5f6b7a; }
  input {
    padding: 0.6rem 0.7rem;
    border: 1px solid #cfd6de;
    border-radius: 8px;
    font: inherit;
  }
  input:focus { outline: 2px solid #4a90d9; outline-offset: 1px; }
  button[type='submit'] {
    margin-top: 0.25rem;
    padding: 0.65rem;
    border: 0;
    border-radius: 8px;
    background: #2c5aa0;
    color: #fff;
    font: inherit;
    font-weight: 600;
    cursor: pointer;
  }
  button[type='submit']:disabled { opacity: 0.6; cursor: default; }
  .link {
    padding: 0;
    border: 0;
    background: none;
    color: #2c5aa0;
    font: inherit;
    font-size: 0.88rem;
    text-decoration: underline;
    cursor: pointer;
  }
</style>
