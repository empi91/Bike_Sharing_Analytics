# ADR – Technical Decision Record

## Template:
[date] – [decision title]
- Decision:
- Rationale:
- Alternatives:
- Consequences:

## Record:

**2025-09-09** – Technology Stack Selection (FastAPI + Supabase)
- **Decision**: Use FastAPI as web framework with Supabase as database backend
- **Rationale**: 
  - FastAPI provides high performance (async), auto-documentation, type safety, and rapid development
  - Supabase offers instant PostgreSQL setup, built-in auth, real-time capabilities, PostGIS support, and free tier
  - Combined stack minimizes deployment complexity (only FastAPI needs hosting)
- **Alternatives**: 
  - Django + PostgreSQL (more complex setup, slower for MVP)
  - Flask + SQLite (limited scalability)
  - Node.js + MongoDB (different language, no spatial queries)
- **Consequences**: 
  - ✅ Faster MVP development and deployment
  - ✅ Built-in scalability and real-time features
  - ✅ Automatic API documentation
  - ⚠️ Vendor lock-in with Supabase (mitigated by standard PostgreSQL)

**2025-09-09** – Database Schema Design
- **Decision**: Implement 4-table normalized schema with spatial indexing
- **Rationale**:
  - `bike_stations`: Core station data with PostGIS location column for efficient spatial queries
  - `availability_snapshots`: Time-series data with 15-minute granularity for pattern analysis
  - `reliability_scores`: Pre-calculated hourly metrics for fast API responses
  - `api_sync_logs`: Operational monitoring and debugging capability
- **Alternatives**:
  - Single denormalized table (poor performance, data duplication)
  - NoSQL document store (limited spatial query capabilities)
- **Consequences**:
  - ✅ Optimized for both writes (snapshots) and reads (reliability queries)
  - ✅ Spatial indexing enables sub-second nearby station searches
  - ✅ Clear separation of operational vs. analytical data

**2025-09-09** – Repository Pattern Implementation
- **Decision**: Use Repository pattern for data access layer
- **Rationale**:
  - Separates business logic from database operations
  - Enables easy testing with mock repositories
  - Provides consistent interface for all database operations
  - Follows FastAPI dependency injection patterns
- **Alternatives**:
  - Direct database calls in route handlers (poor separation of concerns)
  - ORM-based approach (added complexity for read-heavy operations)
- **Consequences**:
  - ✅ Clean, testable code architecture
  - ✅ Easy to swap database implementations
  - ✅ Consistent error handling across all data operations
  - ⚠️ Additional abstraction layer (justified by maintainability gains)

**2025-09-09** – API Security Model
- **Decision**: Row Level Security (RLS) + API Key authentication for internal endpoints
- **Rationale**:
  - RLS provides database-level security for future user features
  - Public read access for bike station data (appropriate for public API)
  - API key auth for admin operations (simple, secure for internal use)
  - 11 security policies provide granular access control
- **Alternatives**:
  - JWT tokens for all endpoints (overkill for public data)
  - No authentication (insecure for admin operations)
- **Consequences**:
  - ✅ Secure by default with granular permissions
  - ✅ Ready for future user authentication features
  - ✅ Simple admin access for operational endpoints
  - ✅ Database-level security enforcement

**2025-09-09** – Testing Framework Selection (unittest)
- **Decision**: Use Python's built-in unittest framework instead of pytest
- **Rationale**:
  - User specifically requested unittest over pytest
  - No external dependencies required
  - Standard library ensures compatibility
  - Sufficient for project testing needs
- **Alternatives**:
  - pytest (more features, fixtures, but additional dependency)
  - Custom testing framework (unnecessary complexity)
- **Consequences**:
  - ✅ Zero additional dependencies
  - ✅ Standard Python testing approach
  - ⚠️ More verbose test setup compared to pytest
  - ✅ Meets user requirements exactly

**2025-09-09** – API Response Model Strategy
- **Decision**: Comprehensive Pydantic models for all request/response schemas
- **Rationale**:
  - Type safety at API boundaries
  - Automatic validation and serialization
  - Self-documenting API through OpenAPI generation
  - Consistent error handling with proper HTTP status codes
- **Alternatives**:
  - Raw dictionaries (no validation, poor documentation)
  - Manual JSON serialization (error-prone, more code)
- **Consequences**:
  - ✅ Type-safe API with automatic validation
  - ✅ Excellent API documentation generation
  - ✅ Reduced runtime errors through compile-time checking
  - ✅ Consistent response formats across all endpoints
