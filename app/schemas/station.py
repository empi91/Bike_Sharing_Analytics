"""
Pydantic schemas for bike station related data.

This module contains all data models for bike stations, including
request/response schemas and internal data transfer objects.
"""

from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class DayType(str, Enum):
    """Enumeration for day types used in reliability calculations."""
    WEEKDAY = "weekday"
    WEEKEND = "weekend"


class SyncStatus(str, Enum):
    """Enumeration for API sync status values."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


# =====================================================
# BIKE STATION SCHEMAS
# =====================================================

class BikeStationBase(BaseModel):
    """Base schema for bike station data."""
    external_station_id: str = Field(..., max_length=100, description="Station ID from external API")
    name: str = Field(..., max_length=255, description="Human-readable station name")
    latitude: Decimal = Field(..., ge=-90, le=90, description="Station latitude coordinate")
    longitude: Decimal = Field(..., ge=-180, le=180, description="Station longitude coordinate")
    total_docks: int = Field(..., gt=0, description="Total number of bike docks at station")
    is_active: bool = Field(default=True, description="Whether station is currently operational")


class BikeStationCreate(BikeStationBase):
    """Schema for creating a new bike station."""
    pass


class BikeStationUpdate(BaseModel):
    """Schema for updating bike station data."""
    name: Optional[str] = Field(None, max_length=255)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    total_docks: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None


class BikeStation(BikeStationBase):
    """Complete bike station schema for responses."""
    id: int = Field(..., description="Unique station identifier")
    created_at: datetime = Field(..., description="Station creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class BikeStationWithDistance(BikeStation):
    """Bike station schema with distance calculation for nearby queries."""
    distance_km: float = Field(..., description="Distance from search point in kilometers")
    estimated_walk_time_minutes: int = Field(..., description="Estimated walking time in minutes")


# =====================================================
# AVAILABILITY SNAPSHOT SCHEMAS
# =====================================================

class AvailabilitySnapshotBase(BaseModel):
    """Base schema for availability snapshot data."""
    station_id: int = Field(..., description="Reference to bike station")
    available_bikes: int = Field(..., ge=0, description="Number of available bikes")
    available_docks: int = Field(..., ge=0, description="Number of available docks")
    is_renting: bool = Field(default=True, description="Station accepting bike rentals")
    is_returning: bool = Field(default=True, description="Station accepting bike returns")
    timestamp: datetime = Field(..., description="When snapshot was taken")
    day_of_week: int = Field(..., ge=1, le=7, description="Day of week (1=Monday, 7=Sunday)")
    hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    minute_slot: int = Field(..., description="15-minute slot (0, 15, 30, 45)")


class AvailabilitySnapshotCreate(AvailabilitySnapshotBase):
    """Schema for creating availability snapshots."""
    pass


class AvailabilitySnapshot(AvailabilitySnapshotBase):
    """Complete availability snapshot schema for responses."""
    id: int = Field(..., description="Unique snapshot identifier")
    created_at: datetime = Field(..., description="Record creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# =====================================================
# RELIABILITY SCORE SCHEMAS
# =====================================================

class ReliabilityScoreBase(BaseModel):
    """Base schema for reliability score data."""
    station_id: int = Field(..., description="Reference to bike station")
    hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    day_type: DayType = Field(..., description="Type of day (weekday/weekend)")
    reliability_percentage: Decimal = Field(..., ge=0, le=100, description="Percentage of time bikes available")
    avg_available_bikes: Decimal = Field(..., ge=0, description="Average bikes available during this hour")
    sample_size: int = Field(..., gt=0, description="Number of data points used for calculation")
    data_period_start: date = Field(..., description="Start of data period used")
    data_period_end: date = Field(..., description="End of data period used")


class ReliabilityScoreCreate(ReliabilityScoreBase):
    """Schema for creating reliability scores."""
    pass


class ReliabilityScore(ReliabilityScoreBase):
    """Complete reliability score schema for responses."""
    id: int = Field(..., description="Unique score identifier")
    calculated_at: datetime = Field(..., description="When scores were calculated")
    created_at: datetime = Field(..., description="Record creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# =====================================================
# API SYNC LOG SCHEMAS
# =====================================================

class ApiSyncLogBase(BaseModel):
    """Base schema for API sync log data."""
    sync_timestamp: datetime = Field(..., description="When sync was attempted")
    sync_status: SyncStatus = Field(..., description="Result of sync operation")
    stations_updated: int = Field(default=0, ge=0, description="Number of stations processed")
    snapshots_created: int = Field(default=0, ge=0, description="Number of new snapshots")
    error_message: Optional[str] = Field(None, description="Error details if sync failed")
    response_time_ms: Optional[int] = Field(None, ge=0, description="API response time in milliseconds")


class ApiSyncLogCreate(ApiSyncLogBase):
    """Schema for creating API sync logs."""
    pass


class ApiSyncLog(ApiSyncLogBase):
    """Complete API sync log schema for responses."""
    id: int = Field(..., description="Unique log identifier")
    created_at: datetime = Field(..., description="Record creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# =====================================================
# COMBINED/RESPONSE SCHEMAS
# =====================================================

class StationReliabilityTimeline(BaseModel):
    """Schema for station reliability timeline data."""
    station: BikeStation = Field(..., description="Station information")
    hourly_reliability: List[ReliabilityScore] = Field(..., description="Hourly reliability scores")
    overall_reliability: float = Field(..., description="Overall reliability percentage")
    best_hours: List[int] = Field(..., description="Hours with highest reliability")
    worst_hours: List[int] = Field(..., description="Hours with lowest reliability")


class NearbyStationsResponse(BaseModel):
    """Schema for nearby stations API response."""
    search_location: dict = Field(..., description="Searched location coordinates")
    stations: List[BikeStationWithDistance] = Field(..., description="Nearby stations with distances")
    total_found: int = Field(..., description="Total number of stations found")
    search_radius_km: float = Field(..., description="Search radius used")


class StationCurrentStatus(BaseModel):
    """Schema for current station status."""
    station: BikeStation = Field(..., description="Station information")
    current_availability: Optional[AvailabilitySnapshot] = Field(None, description="Most recent availability data")
    reliability_summary: dict = Field(..., description="Summary of reliability metrics")
    last_updated: datetime = Field(..., description="When data was last updated")


# =====================================================
# ERROR RESPONSE SCHEMAS
# =====================================================

class ErrorResponse(BaseModel):
    """Standard error response schema."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class ValidationErrorResponse(ErrorResponse):
    """Validation error response schema."""
    validation_errors: List[dict] = Field(..., description="Detailed validation errors")
