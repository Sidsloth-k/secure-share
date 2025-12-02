-- Ensure authenticated users can work with public.users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.users TO authenticated;

-- (Optionally, for anon read-only access if needed)
GRANT USAGE ON SCHEMA public TO anon;
GRANT SELECT ON TABLE public.users TO anon;

-- If you keep using auth.users in RLS policies, also:
GRANT USAGE ON SCHEMA auth TO authenticated;
GRANT SELECT ON TABLE auth.users TO authenticated;