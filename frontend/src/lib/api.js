import { supabase } from './supabase.js';

/** fetch() for /api/*: adds the signed-in user's access token, and signs out if it's rejected. */
export async function apiFetch(path, options = {}) {
  if (!supabase) return fetch(path, options);

  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  const headers = { ...options.headers, ...(token && { Authorization: `Bearer ${token}` }) };
  const res = await fetch(path, { ...options, headers });
  // Expired or revoked: back to the sign-in screen.
  if (res.status === 401) await supabase.auth.signOut();
  return res;
}
