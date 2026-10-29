<script>
  import { onDestroy } from 'svelte';
  import App from './App.svelte';
  import SignIn from './components/SignIn.svelte';
  import { authEnabled, supabase } from './lib/supabase.js';

  // undefined: still checking for a session (e.g. arriving from an invite link).
  let session = authEnabled ? undefined : null;
  let unsubscribe = () => {};

  if (authEnabled) {
    supabase.auth.getSession().then(({ data }) => { session = data.session; });
    const { data } = supabase.auth.onAuthStateChange((_event, next) => { session = next; });
    unsubscribe = () => data.subscription.unsubscribe();
  }
  onDestroy(() => unsubscribe());

  const signOut = () => supabase.auth.signOut();
</script>

{#if !authEnabled}
  <App />
{:else if session}
  <App user={session.user} onSignOut={signOut} />
{:else if session === null}
  <SignIn />
{/if}
