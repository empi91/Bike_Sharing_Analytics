# Product Requirements Document (PRD)
## Bike Station Reliability Lookup

---

## 1. Function Goal
This function helps daily bike commuters who are considering relocating by providing reliable historical data about bike availability at stations near their potential new homes, enabling informed housing decisions.

---

## 2. User Flow (Happy Path)

1. User enters potential home address in search bar
2. App shows nearest 5 stations with distance + reliability scores  
3. User clicks on most promising station
4. Sees detailed timeline: "Mon-Fri 7am: 12/15 bikes available (avg)"
5. Toggles between weekdays/weekends view

---

## 3. Database Schema (Supabase)

### `bike_stations`
| Field | Type | Description |
|-------|------|-------------|
| `id` | BIGSERIAL PRIMARY KEY | Unique station identifier (Supabase auto-generated) |
| `external_station_id` | VARCHAR(100) | Station ID from city API |
| `name` | VARCHAR(255) | Station display name |
| `latitude` | DECIMAL(10,8) | Station latitude coordinate |
| `longitude` | DECIMAL(11,8) | Station longitude coordinate |
| `total_docks` | INTEGER | Total number of bike docks |
| `is_active` | BOOLEAN | Whether station is currently operational |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | Record creation time (Supabase auto-generated) |
| `updated_at` | TIMESTAMPTZ DEFAULT NOW() | Last update from city API |

### `availability_snapshots`
| Field | Type | Description |
|-------|------|-------------|
| `id` | BIGSERIAL PRIMARY KEY | Unique snapshot identifier (Supabase auto-generated) |
| `station_id` | BIGINT REFERENCES bike_stations(id) | Foreign key to bike_stations |
| `available_bikes` | INTEGER | Number of available bikes |
| `available_docks` | INTEGER | Number of available docks |
| `is_renting` | BOOLEAN | Station accepting bike rentals |
| `is_returning` | BOOLEAN | Station accepting bike returns |
| `timestamp` | TIMESTAMPTZ | When snapshot was taken |
| `day_of_week` | SMALLINT | 1=Monday, 7=Sunday |
| `hour` | SMALLINT | Hour of day (0-23) |
| `minute_slot` | SMALLINT | 15-minute slot (0, 15, 30, 45) |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | Record creation time (Supabase auto-generated) |

### `reliability_scores`
| Field | Type | Description |
|-------|------|-------------|
| `id` | BIGSERIAL PRIMARY KEY | Unique score identifier (Supabase auto-generated) |
| `station_id` | BIGINT REFERENCES bike_stations(id) | Foreign key to bike_stations |
| `hour` | SMALLINT | Hour of day (0-23) |
| `day_type` | TEXT CHECK (day_type IN ('weekday', 'weekend')) | Type of day |
| `reliability_percentage` | DECIMAL(5,2) | Percentage of time bikes available |
| `avg_available_bikes` | DECIMAL(4,2) | Average bikes available during this hour |
| `sample_size` | INTEGER | Number of data points used for calculation |
| `calculated_at` | TIMESTAMPTZ DEFAULT NOW() | When scores were last calculated |
| `data_period_start` | DATE | Start of data period used |
| `data_period_end` | DATE | End of data period used |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | Record creation time (Supabase auto-generated) |

### `api_sync_logs`
| Field | Type | Description |
|-------|------|-------------|
| `id` | BIGSERIAL PRIMARY KEY | Unique log identifier (Supabase auto-generated) |
| `sync_timestamp` | TIMESTAMPTZ | When sync was attempted |
| `sync_status` | TEXT CHECK (sync_status IN ('success', 'failed', 'partial')) | Result of sync |
| `stations_updated` | INTEGER | Number of stations processed |
| `snapshots_created` | INTEGER | Number of new snapshots |
| `error_message` | TEXT | Error details if sync failed |
| `response_time_ms` | INTEGER | API response time |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | Record creation time (Supabase auto-generated) |

**Supabase Benefits for this Schema:**
- Automatic `id`, `created_at`, and `updated_at` fields
- Built-in Row Level Security (RLS) for future user features
- Real-time subscriptions for live station updates
- PostgREST API generation for rapid prototyping
- Built-in database functions and triggers

---

## 4. API Endpoints

### User-Facing Endpoints (FastAPI)

#### `GET /api/stations/nearby`
**Description:** Find nearest bike stations to given address
- **Query Parameters:**
  - `address` (required): Address to search from
  - `limit` (optional): Number of stations to return (default: 5, max: 20)
- **Response:** Array of stations with distance and reliability scores
- **Performance Target:** < 3 seconds response time
- **Example:** `GET /api/stations/nearby?address=123%20Main%20St&limit=5`

#### `GET /api/stations/{station_id}/reliability`
**Description:** Get detailed reliability timeline for specific station
- **Path Parameters:**
  - `station_id` (required): Station ID
- **Query Parameters:**
  - `day_type` (optional): 'weekday' or 'weekend' (default: both)
  - `hours` (optional): Comma-separated hours to filter (e.g., "7,8,9" for morning rush)
- **Response:** Hourly reliability data and average bike availability
- **Example:** `GET /api/stations/42/reliability?day_type=weekday&hours=7,8,9`

#### `GET /api/stations/{station_id}`
**Description:** Get basic station information
- **Path Parameters:**
  - `station_id` (required): Station ID
- **Response:** Station details including name, location, total capacity
- **Example:** `GET /api/stations/42`

#### `GET /api/health`
**Description:** Health check endpoint
- **Response:** API status and database connectivity

### Background System Endpoints (FastAPI Internal)

#### `POST /api/internal/sync/stations`
**Description:** Trigger manual sync of station data from city API
- **Authentication:** API key required (`X-API-Key` header)
- **Response:** Sync status and statistics
- **Supabase Integration:** Uses Supabase client for bulk inserts/updates

#### `POST /api/internal/sync/availability`
**Description:** Trigger manual collection of current availability data
- **Authentication:** API key required
- **Response:** Collection status and number of snapshots created
- **Scheduling:** APScheduler every 5 minutes

#### `POST /api/internal/calculate/reliability`
**Description:** Trigger recalculation of reliability scores
- **Query Parameters:**
  - `days_back` (optional): Number of days to include (default: 30)
- **Authentication:** API key required
- **Response:** Calculation status and stations processed
- **Supabase Integration:** Uses database functions for efficient calculations

#### `GET /api/internal/health/sync`
**Description:** Check status of background data collection
- **Authentication:** API key required
- **Response:** Last sync times, error counts, data freshness metrics

### Technology Integration Notes

**FastAPI Benefits:**
- Automatic OpenAPI/Swagger documentation at `/docs`
- Pydantic models for request/response validation
- Async support for concurrent API calls to city bike services
- High performance for the 3-second response requirement
- Minimal boilerplate compared to Django

**Supabase Integration:**
- Python client: `supabase-py` for database operations
- Real-time subscriptions for future live updates
- Built-in authentication for future user accounts
- Edge functions for complex database operations
- Automatic API generation via PostgREST (backup option)

**Environemnt**
- Project will be developed using WSL on Windows
- All terminal commands, configs and functions have to work properly from WSL
- Project will be hosted from Linux-based server

---

## 5. DONE Criteria

1. **Address Search Works:** User can enter any valid city address and receive 5 nearest stations with reliability scores within 3 seconds, based on data collected continuously from the city API via FastAPI endpoints connected to Supabase.

2. **Reliability Data Displays:** Clicking any station shows hourly timeline with clear percentages and average bike counts, with functional weekday/weekend toggle, using historical data spanning at least 30 days stored in Supabase.

3. **Background Data Collection:** FastAPI application automatically fetches station availability data from city API every 5 minutes using APScheduler, stores snapshots in Supabase, and recalculates reliability scores daily without user intervention.

4. **Technical Performance:** FastAPI + Supabase stack delivers sub-3-second response times, handles concurrent users, and maintains 99%+ uptime for data collection processes.
