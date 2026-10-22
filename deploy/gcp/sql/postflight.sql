-- Runtime logins must not be owners, superusers or members of cloudsqlsuperuser.
DO $check$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relrowsecurity AND NOT c.relforcerowsecurity
    ) THEN RAISE EXCEPTION 'Application row security must remain forced after migrations'; END IF;
    IF EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname IN ('nexoruta_api_runtime', 'nexoruta_worker_runtime', 'nexoruta_bootstrap_runtime')
          AND (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole)
    ) THEN RAISE EXCEPTION 'Unsafe runtime role privileges'; END IF;
    IF EXISTS (
        SELECT 1 FROM pg_roles r
        WHERE r.rolname IN ('nexoruta_api_runtime', 'nexoruta_worker_runtime', 'nexoruta_bootstrap_runtime')
          AND pg_has_role(r.oid, 'cloudsqlsuperuser', 'MEMBER')
    ) THEN RAISE EXCEPTION 'Runtime role must not be a Cloud SQL administrator'; END IF;
END
$check$;
