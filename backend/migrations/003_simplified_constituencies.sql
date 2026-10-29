-- Precompute the ~50 m simplified constituency boundaries served by
-- /api/parliamentary-boundaries. Simplifying all 650 on every request took
-- ~20 s; reading the stored column takes well under a second. As a generated
-- column it stays in sync whenever the importer replaces the rows.
ALTER TABLE public.uk_parliamentary_constituencies
    ADD COLUMN IF NOT EXISTS geometry_simplified geometry
    GENERATED ALWAYS AS (ST_SimplifyPreserveTopology(geometry, 0.0005)) STORED;
