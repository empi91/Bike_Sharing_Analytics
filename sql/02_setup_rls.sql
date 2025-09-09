-- Row Level Security (RLS) Setup
-- Configure security policies for future scalability and user access control

-- =====================================================
-- ENABLE ROW LEVEL SECURITY
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE bike_stations ENABLE ROW LEVEL SECURITY;
ALTER TABLE availability_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE reliability_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_sync_logs ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- PUBLIC READ ACCESS POLICIES
-- =====================================================

-- Allow public read access to bike stations (for public API)
CREATE POLICY "Public can view active bike stations" ON bike_stations
    FOR SELECT
    USING (is_active = true);

-- Allow public read access to availability snapshots (for public API)
CREATE POLICY "Public can view availability snapshots" ON availability_snapshots
    FOR SELECT
    USING (true);

-- Allow public read access to reliability scores (for public API)
CREATE POLICY "Public can view reliability scores" ON reliability_scores
    FOR SELECT
    USING (true);

-- Restrict public access to sync logs (admin only)
CREATE POLICY "No public access to sync logs" ON api_sync_logs
    FOR SELECT
    USING (false);

-- =====================================================
-- SERVICE ROLE (ADMIN) ACCESS POLICIES
-- =====================================================

-- Service role can do everything on bike_stations
CREATE POLICY "Service role full access to bike_stations" ON bike_stations
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Service role can do everything on availability_snapshots
CREATE POLICY "Service role full access to availability_snapshots" ON availability_snapshots
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Service role can do everything on reliability_scores
CREATE POLICY "Service role full access to reliability_scores" ON reliability_scores
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Service role can do everything on api_sync_logs
CREATE POLICY "Service role full access to api_sync_logs" ON api_sync_logs
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- =====================================================
-- AUTHENTICATED USER POLICIES (for future user features)
-- =====================================================

-- Authenticated users can view all public data (same as anonymous for now)
CREATE POLICY "Authenticated users can view bike stations" ON bike_stations
    FOR SELECT
    TO authenticated
    USING (is_active = true);

CREATE POLICY "Authenticated users can view availability snapshots" ON availability_snapshots
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Authenticated users can view reliability scores" ON reliability_scores
    FOR SELECT
    TO authenticated
    USING (true);

-- Future: Add policies for user preferences, favorites, etc.
-- CREATE POLICY "Users can manage their own preferences" ON user_preferences
--     FOR ALL
--     TO authenticated
--     USING (user_id = auth.uid())
--     WITH CHECK (user_id = auth.uid());

-- =====================================================
-- SECURITY NOTES AND COMMENTS
-- =====================================================

COMMENT ON POLICY "Public can view active bike stations" ON bike_stations IS 
    'Allows public API access to active bike station information';

COMMENT ON POLICY "Public can view availability snapshots" ON availability_snapshots IS 
    'Allows public API access to historical availability data';

COMMENT ON POLICY "Public can view reliability scores" ON reliability_scores IS 
    'Allows public API access to calculated reliability metrics';

COMMENT ON POLICY "No public access to sync logs" ON api_sync_logs IS 
    'Sync logs contain operational information and should only be accessible to service roles';

-- =====================================================
-- GRANT BASIC PERMISSIONS
-- =====================================================

-- Grant basic select permissions to anonymous users (public API)
GRANT SELECT ON bike_stations TO anon;
GRANT SELECT ON availability_snapshots TO anon;
GRANT SELECT ON reliability_scores TO anon;

-- Grant select permissions to authenticated users
GRANT SELECT ON bike_stations TO authenticated;
GRANT SELECT ON availability_snapshots TO authenticated;
GRANT SELECT ON reliability_scores TO authenticated;

-- Service role already has full access through Supabase configuration

-- =====================================================
-- SECURITY VALIDATION FUNCTIONS
-- =====================================================

-- Function to check if current user can access admin features
CREATE OR REPLACE FUNCTION is_admin_user()
RETURNS BOOLEAN AS $$
BEGIN
    -- For now, only service role is admin
    -- In future, could check user roles/permissions
    RETURN auth.role() = 'service_role';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to validate API key (for internal endpoints)
CREATE OR REPLACE FUNCTION validate_api_key(provided_key TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- This would validate against stored API keys
    -- For now, we'll handle this in the application layer
    RETURN true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- FUTURE ENHANCEMENTS
-- =====================================================

-- Ideas for future security enhancements:
-- 1. Rate limiting policies
-- 2. User-specific data access (favorites, preferences)
-- 3. API key management in database
-- 4. Audit logging for data changes
-- 5. Geographic restrictions for certain data
-- 6. Time-based access controls
