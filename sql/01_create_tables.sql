-- Bike Station Reliability Database Schema
-- Create all required tables for the bike sharing analytics system

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- =====================================================
-- 1. BIKE_STATIONS TABLE
-- =====================================================
CREATE TABLE bike_stations (
    id BIGSERIAL PRIMARY KEY,
    external_station_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    total_docks INTEGER NOT NULL CHECK (total_docks > 0),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_bike_stations_external_id ON bike_stations(external_station_id);
CREATE INDEX idx_bike_stations_location ON bike_stations(latitude, longitude);
CREATE INDEX idx_bike_stations_active ON bike_stations(is_active) WHERE is_active = true;

-- Add spatial index using PostGIS (for distance calculations)
-- Convert lat/lng to geometry for efficient spatial queries
ALTER TABLE bike_stations ADD COLUMN location GEOMETRY(POINT, 4326);

-- Create function to automatically update location from lat/lng
CREATE OR REPLACE FUNCTION update_station_location()
RETURNS TRIGGER AS $$
BEGIN
    NEW.location = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create trigger to automatically update location
CREATE TRIGGER trigger_update_station_location
    BEFORE INSERT OR UPDATE ON bike_stations
    FOR EACH ROW
    EXECUTE FUNCTION update_station_location();

-- Create spatial index for efficient distance queries
CREATE INDEX idx_bike_stations_location_gist ON bike_stations USING GIST(location);

-- =====================================================
-- 2. AVAILABILITY_SNAPSHOTS TABLE
-- =====================================================
CREATE TABLE availability_snapshots (
    id BIGSERIAL PRIMARY KEY,
    station_id BIGINT NOT NULL REFERENCES bike_stations(id) ON DELETE CASCADE,
    available_bikes INTEGER NOT NULL CHECK (available_bikes >= 0),
    available_docks INTEGER NOT NULL CHECK (available_docks >= 0),
    is_renting BOOLEAN NOT NULL DEFAULT true,
    is_returning BOOLEAN NOT NULL DEFAULT true,
    timestamp TIMESTAMPTZ NOT NULL,
    day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7), -- 1=Monday, 7=Sunday
    hour SMALLINT NOT NULL CHECK (hour BETWEEN 0 AND 23),
    minute_slot SMALLINT NOT NULL CHECK (minute_slot IN (0, 15, 30, 45)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX idx_availability_snapshots_station ON availability_snapshots(station_id);
CREATE INDEX idx_availability_snapshots_timestamp ON availability_snapshots(timestamp);
CREATE INDEX idx_availability_snapshots_time_analysis ON availability_snapshots(station_id, day_of_week, hour);
-- Note: Removed WHERE clause with NOW() as it's not allowed in index predicates
-- Will use time-based filtering in queries instead
CREATE INDEX idx_availability_snapshots_recent ON availability_snapshots(timestamp DESC);

-- Create composite index for reliability calculations
CREATE INDEX idx_availability_snapshots_reliability ON availability_snapshots(station_id, timestamp, available_bikes) 
WHERE available_bikes > 0;

-- =====================================================
-- 3. RELIABILITY_SCORES TABLE
-- =====================================================
CREATE TABLE reliability_scores (
    id BIGSERIAL PRIMARY KEY,
    station_id BIGINT NOT NULL REFERENCES bike_stations(id) ON DELETE CASCADE,
    hour SMALLINT NOT NULL CHECK (hour BETWEEN 0 AND 23),
    day_type TEXT NOT NULL CHECK (day_type IN ('weekday', 'weekend')),
    reliability_percentage DECIMAL(5,2) NOT NULL CHECK (reliability_percentage BETWEEN 0 AND 100),
    avg_available_bikes DECIMAL(4,2) NOT NULL CHECK (avg_available_bikes >= 0),
    sample_size INTEGER NOT NULL CHECK (sample_size > 0),
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_period_start DATE NOT NULL,
    data_period_end DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure we don't have duplicate scores for same station/hour/day_type
    UNIQUE(station_id, hour, day_type)
);

-- Create indexes for efficient querying
CREATE INDEX idx_reliability_scores_station ON reliability_scores(station_id);
CREATE INDEX idx_reliability_scores_lookup ON reliability_scores(station_id, hour, day_type);
CREATE INDEX idx_reliability_scores_calculated ON reliability_scores(calculated_at);

-- =====================================================
-- 4. API_SYNC_LOGS TABLE
-- =====================================================
CREATE TABLE api_sync_logs (
    id BIGSERIAL PRIMARY KEY,
    sync_timestamp TIMESTAMPTZ NOT NULL,
    sync_status TEXT NOT NULL CHECK (sync_status IN ('success', 'failed', 'partial')),
    stations_updated INTEGER NOT NULL DEFAULT 0 CHECK (stations_updated >= 0),
    snapshots_created INTEGER NOT NULL DEFAULT 0 CHECK (snapshots_created >= 0),
    error_message TEXT,
    response_time_ms INTEGER CHECK (response_time_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for monitoring and debugging
CREATE INDEX idx_api_sync_logs_timestamp ON api_sync_logs(sync_timestamp);
CREATE INDEX idx_api_sync_logs_status ON api_sync_logs(sync_status);
-- Note: Removed WHERE clause with NOW() as it's not allowed in index predicates
-- Will use time-based filtering in queries instead
CREATE INDEX idx_api_sync_logs_recent ON api_sync_logs(sync_timestamp DESC);

-- =====================================================
-- 5. HOURLY_AVAILABILITY_AVERAGES TABLE
-- =====================================================
CREATE TABLE hourly_availability_averages (
    id BIGSERIAL PRIMARY KEY,
    station_id BIGINT NOT NULL REFERENCES bike_stations(id) ON DELETE CASCADE,
    hour SMALLINT NOT NULL CHECK (hour BETWEEN 0 AND 23),
    day_type TEXT NOT NULL CHECK (day_type IN ('weekday', 'weekend')),
    avg_bikes_available DECIMAL(4,2) NOT NULL CHECK (avg_bikes_available >= 0),
    total_snapshots INTEGER NOT NULL CHECK (total_snapshots > 0),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure we don't have duplicate averages for same station/hour/day_type
    UNIQUE(station_id, hour, day_type)
);

-- Create indexes for efficient querying
CREATE INDEX idx_hourly_averages_station ON hourly_availability_averages(station_id);
CREATE INDEX idx_hourly_averages_lookup ON hourly_availability_averages(station_id, hour, day_type);
CREATE INDEX idx_hourly_averages_updated ON hourly_availability_averages(last_updated);

-- =====================================================
-- FUNCTIONS FOR DATA MANAGEMENT
-- =====================================================

-- Function to calculate hourly averages efficiently
CREATE OR REPLACE FUNCTION calculate_hourly_averages(station_id_param BIGINT)
RETURNS TABLE (
    hour SMALLINT,
    day_type TEXT,
    avg_bikes DECIMAL(4,2),
    total_snapshots INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.hour,
        CASE 
            WHEN s.day_of_week IN (1, 2, 3, 4, 5) THEN 'weekday'
            ELSE 'weekend'
        END as day_type,
        AVG(s.available_bikes) as avg_bikes,
        COUNT(*)::INTEGER as total_snapshots
    FROM availability_snapshots s
    WHERE s.station_id = station_id_param
    GROUP BY s.hour, 
        CASE 
            WHEN s.day_of_week IN (1, 2, 3, 4, 5) THEN 'weekday'
            ELSE 'weekend'
        END
    ORDER BY s.hour;
END;
$$ LANGUAGE plpgsql;

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql VOLATILE;

-- Create trigger for bike_stations updated_at
CREATE TRIGGER trigger_bike_stations_updated_at
    BEFORE UPDATE ON bike_stations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate distance between two points (helper for API)
CREATE OR REPLACE FUNCTION calculate_distance_km(lat1 DECIMAL, lng1 DECIMAL, lat2 DECIMAL, lng2 DECIMAL)
RETURNS DECIMAL AS $$
BEGIN
    RETURN ST_Distance(
        ST_SetSRID(ST_MakePoint(lng1, lat1), 4326)::geography,
        ST_SetSRID(ST_MakePoint(lng2, lat2), 4326)::geography
    ) / 1000.0; -- Convert meters to kilometers
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT;

-- =====================================================
-- DATA VALIDATION AND CONSTRAINTS
-- =====================================================

-- Add constraint to ensure total docks makes sense with availability
-- (This will be enforced in application logic, but good to document)
COMMENT ON TABLE bike_stations IS 'Core bike station information with location data';
COMMENT ON TABLE availability_snapshots IS 'Historical snapshots of bike/dock availability at each station';
COMMENT ON TABLE reliability_scores IS 'Calculated reliability metrics for each station by hour and day type';
COMMENT ON TABLE api_sync_logs IS 'Audit log of external API synchronization attempts';

-- Add helpful comments on key columns
COMMENT ON COLUMN bike_stations.external_station_id IS 'Station ID from the external bike sharing API';
COMMENT ON COLUMN bike_stations.location IS 'PostGIS point geometry for efficient spatial queries';
COMMENT ON COLUMN availability_snapshots.day_of_week IS '1=Monday through 7=Sunday';
COMMENT ON COLUMN availability_snapshots.minute_slot IS 'Rounded to nearest 15-minute interval (0, 15, 30, 45)';
COMMENT ON COLUMN reliability_scores.reliability_percentage IS 'Percentage of time bikes were available during this hour';
COMMENT ON COLUMN reliability_scores.day_type IS 'weekday (Mon-Fri) or weekend (Sat-Sun)';

-- Grant permissions (optional, for future use)
-- These would be configured based on your specific security needs
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
