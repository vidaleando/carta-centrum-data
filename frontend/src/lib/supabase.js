import { createClient } from '@supabase/supabase-js';

const url = import.meta.env.VITE_SUPABASE_URL;
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

/**
 * Invite-only sign-in. Without the two env vars (e.g. local dev against a backend
 * with AUTH_ENABLED off) there is no sign-in screen and API calls carry no token.
 */
export const authEnabled = Boolean(url && key);

export const supabase = authEnabled ? createClient(url, key) : null;
