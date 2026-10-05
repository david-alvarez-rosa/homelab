CREATE OR REPLACE FUNCTION public.websearch_to_tsquery(cfg regconfig, q text) RETURNS tsquery
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
  SELECT CASE WHEN t::text = '' THEN t
         ELSE regexp_replace(t::text, '''((?:[^'']|'''')+)''', '''\1'':*', 'g')::tsquery END
  FROM pg_catalog.websearch_to_tsquery(cfg, q) t
$$;
ALTER ROLE synapse IN DATABASE synapse SET search_path = "$user", public, pg_catalog;
