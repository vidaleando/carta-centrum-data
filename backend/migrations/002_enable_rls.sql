-- Supabase exposes the public schema through its auto-generated REST API.
-- With row level security on and no policies, that API can't read or write
-- these tables. The app connects as the table owner, which bypasses RLS, so
-- it is unaffected (as is every other Postgres host).
ALTER TABLE public.uk_parliamentary_constituencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.uk_mps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.osm_data_centers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.schema_migrations ENABLE ROW LEVEL SECURITY;
-- Loaded outside migrations, so it may not exist yet. Enable RLS on it by
-- hand after loading it.
ALTER TABLE IF EXISTS public.basic_bounds ENABLE ROW LEVEL SECURITY;
