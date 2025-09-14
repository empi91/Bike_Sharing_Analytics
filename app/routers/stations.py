"""
API routes for bike station operations.

This module contains all user-facing API endpoints related to bike stations,
including station lookup, nearby search, and reliability data retrieval.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app.core.database import get_db, SupabaseClient
from app.repositories.station_repository import StationRepository
from app.schemas.station import (
    BikeStation,
    BikeStationWithDistance,
    NearbyStationsResponse,
    StationCurrentStatus,
    StationReliabilityTimeline,
    ReliabilityScore,
    AvailabilitySnapshot,
    HourlyAvailabilityAverage,
    DayType,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

# Create router for station-related endpoints
router = APIRouter(prefix="/api/stations", tags=["Stations"])


def get_station_repository(db: SupabaseClient = Depends(get_db)) -> StationRepository:
    """
    Dependency to get station repository instance.
    
    Args:
        db: Supabase client instance
        
    Returns:
        StationRepository: Repository instance for station operations
    """
    return StationRepository(db)


@router.get("/", response_model=List[BikeStation])
async def get_all_stations(
    active_only: bool = Query(True, description="Return only active stations"),
    repo: StationRepository = Depends(get_station_repository)
):
    """
    Get all bike stations.
    
    This endpoint returns a list of all bike stations in the system.
    By default, only active stations are returned.
    
    Args:
        active_only: If True, only return active stations
        repo: Station repository dependency
        
    Returns:
        List[BikeStation]: List of bike stations
        
    Raises:
        HTTPException: If database operation fails
        
    Example:
        GET /api/stations/?active_only=true
    """
    try:
        logger.info(f"Fetching all stations (active_only={active_only})")
        stations = await repo.get_all_stations(active_only=active_only)
        logger.info(f"Retrieved {len(stations)} stations")
        return stations
        
    except Exception as e:
        logger.error(f"Failed to fetch stations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve stations"
        )


@router.get("/nearby", response_model=NearbyStationsResponse)
async def get_nearby_stations(
    address: Optional[str] = Query(None, description="Address to search from"),
    latitude: Optional[float] = Query(None, description="Latitude coordinate"),
    longitude: Optional[float] = Query(None, description="Longitude coordinate"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of stations to return"),
    max_distance_km: float = Query(5.0, ge=0.1, le=50.0, description="Maximum search radius in kilometers"),
    repo: StationRepository = Depends(get_station_repository)
):
    """
    Find nearby bike stations.
    
    This endpoint finds bike stations near a given location. You can specify
    the location either by address (which will be geocoded) or by providing
    latitude/longitude coordinates directly.
    
    Args:
        address: Address to search from (will be geocoded)
        latitude: Latitude coordinate (alternative to address)
        longitude: Longitude coordinate (alternative to address)
        limit: Maximum number of stations to return (1-20)
        max_distance_km: Maximum search radius in kilometers (0.1-50.0)
        repo: Station repository dependency
        
    Returns:
        NearbyStationsResponse: Nearby stations with distances
        
    Raises:
        HTTPException: If invalid parameters or database operation fails
        
    Example:
        GET /api/stations/nearby?latitude=40.7589&longitude=-73.9851&limit=5
    """
    try:
        # Validate input parameters
        if address and (latitude is not None or longitude is not None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either 'address' or 'latitude/longitude', not both"
            )
        
        if not address and (latitude is None or longitude is None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide either 'address' or both 'latitude' and 'longitude'"
            )
        
        # If address is provided, we would geocode it here
        # For now, we'll just handle lat/lng coordinates
        if address:
            # TODO: Implement address geocoding using Nominatim
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Address geocoding not yet implemented. Please use latitude/longitude."
            )
        
        # Validate coordinate ranges
        if not (-90 <= latitude <= 90):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Latitude must be between -90 and 90"
            )
        
        if not (-180 <= longitude <= 180):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Longitude must be between -180 and 180"
            )
        
        logger.info(f"Searching for stations near ({latitude}, {longitude})")
        
        # Find nearby stations
        nearby_stations_data = await repo.get_nearby_stations(
            latitude=latitude,
            longitude=longitude,
            limit=limit,
            max_distance_km=max_distance_km
        )
        
        # Convert to response format
        stations_with_distance = []
        for station_data in nearby_stations_data:
            distance_km = station_data.pop('distance_km', 0)
            
            # Calculate estimated walking time (assuming 5 km/h walking speed)
            walking_time_minutes = int((distance_km / 5.0) * 60)
            
            station = BikeStation(**station_data)
            station_with_distance = BikeStationWithDistance(
                **station.model_dump(),
                distance_km=distance_km,
                estimated_walk_time_minutes=walking_time_minutes
            )
            stations_with_distance.append(station_with_distance)
        
        response = NearbyStationsResponse(
            search_location={"latitude": latitude, "longitude": longitude},
            stations=stations_with_distance,
            total_found=len(stations_with_distance),
            search_radius_km=max_distance_km
        )
        
        logger.info(f"Found {len(stations_with_distance)} nearby stations")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to find nearby stations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search for nearby stations"
        )


@router.get("/{station_id}", response_model=StationCurrentStatus)
async def get_station_by_id(
    station_id: int,
    repo: StationRepository = Depends(get_station_repository)
):
    """
    Get detailed information about a specific station.
    
    This endpoint returns comprehensive information about a bike station,
    including current availability and reliability summary.
    
    Args:
        station_id: Unique station identifier
        repo: Station repository dependency
        
    Returns:
        StationCurrentStatus: Detailed station information
        
    Raises:
        HTTPException: If station not found or database operation fails
        
    Example:
        GET /api/stations/1
    """
    try:
        logger.info(f"Fetching station details for ID: {station_id}")
        
        # Get station information
        station = await repo.get_station_by_id(station_id)
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Station with ID {station_id} not found"
            )
        
        # Get recent availability data
        recent_snapshots = await repo.get_recent_snapshots(station_id, limit=1)
        current_availability = recent_snapshots[0] if recent_snapshots else None
        
        # Get reliability scores for summary
        reliability_scores = await repo.get_reliability_scores(station_id)
        
        # Calculate reliability summary
        reliability_summary = {
            "overall_reliability": 0.0,
            "best_hour": None,
            "worst_hour": None,
            "total_scores": len(reliability_scores)
        }
        
        if reliability_scores:
            # Calculate overall average reliability
            avg_reliability = sum(float(score.reliability_percentage) for score in reliability_scores) / len(reliability_scores)
            reliability_summary["overall_reliability"] = round(avg_reliability, 2)
            
            # Find best and worst hours
            best_score = max(reliability_scores, key=lambda x: x.reliability_percentage)
            worst_score = min(reliability_scores, key=lambda x: x.reliability_percentage)
            
            reliability_summary["best_hour"] = {
                "hour": best_score.hour,
                "reliability": float(best_score.reliability_percentage),
                "day_type": best_score.day_type
            }
            reliability_summary["worst_hour"] = {
                "hour": worst_score.hour,
                "reliability": float(worst_score.reliability_percentage),
                "day_type": worst_score.day_type
            }
        
        response = StationCurrentStatus(
            station=station,
            current_availability=current_availability,
            reliability_summary=reliability_summary,
            last_updated=current_availability.timestamp if current_availability else station.updated_at
        )
        
        logger.info(f"Retrieved details for station: {station.name}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch station {station_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve station information"
        )


@router.get("/{station_id}/reliability", response_model=StationReliabilityTimeline)
async def get_station_reliability(
    station_id: int,
    day_type: Optional[DayType] = Query(None, description="Filter by day type (weekday/weekend)"),
    hours: Optional[str] = Query(None, description="Comma-separated hours to filter (e.g., '7,8,9')"),
    repo: StationRepository = Depends(get_station_repository)
):
    """
    Get detailed reliability timeline for a specific station.
    
    This endpoint provides hourly reliability data for a station,
    with optional filtering by day type and specific hours.
    
    Args:
        station_id: Unique station identifier
        day_type: Filter by day type (weekday/weekend)
        hours: Comma-separated hours to filter (0-23)
        repo: Station repository dependency
        
    Returns:
        StationReliabilityTimeline: Detailed reliability timeline
        
    Raises:
        HTTPException: If station not found or invalid parameters
        
    Example:
        GET /api/stations/1/reliability?day_type=weekday&hours=7,8,9
    """
    try:
        logger.info(f"Fetching reliability data for station {station_id}")
        
        # Verify station exists
        station = await repo.get_station_by_id(station_id)
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Station with ID {station_id} not found"
            )
        
        # Get reliability scores
        reliability_scores = await repo.get_reliability_scores(station_id, day_type)
        
        # Filter by hours if specified
        if hours:
            try:
                hour_list = [int(h.strip()) for h in hours.split(',')]
                if not all(0 <= h <= 23 for h in hour_list):
                    raise ValueError("Hours must be between 0 and 23")
                reliability_scores = [score for score in reliability_scores if score.hour in hour_list]
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid hours parameter: {str(e)}"
                )
        
        if not reliability_scores:
            logger.warning(f"No reliability data found for station {station_id}")
        
        # Calculate overall metrics
        overall_reliability = 0.0
        best_hours = []
        worst_hours = []
        
        if reliability_scores:
            overall_reliability = sum(float(score.reliability_percentage) for score in reliability_scores) / len(reliability_scores)
            
            # Find best and worst performing hours
            max_reliability = max(float(score.reliability_percentage) for score in reliability_scores)
            min_reliability = min(float(score.reliability_percentage) for score in reliability_scores)
            
            best_hours = [score.hour for score in reliability_scores if float(score.reliability_percentage) == max_reliability]
            worst_hours = [score.hour for score in reliability_scores if float(score.reliability_percentage) == min_reliability]
        
        response = StationReliabilityTimeline(
            station=station,
            hourly_reliability=reliability_scores,
            overall_reliability=round(overall_reliability, 2),
            best_hours=best_hours,
            worst_hours=worst_hours
        )
        
        logger.info(f"Retrieved reliability data: {len(reliability_scores)} hourly scores")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch reliability for station {station_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reliability data"
        )


@router.get("/{station_id}/availability", response_model=List[AvailabilitySnapshot])
async def get_station_availability_history(
    station_id: int,
    limit: int = Query(10, ge=1, le=50, description="Maximum number of snapshots to return"),
    repo: StationRepository = Depends(get_station_repository)
):
    """
    Get recent availability history for a specific station.
    
    This endpoint returns the most recent availability snapshots
    for a station, showing historical bike availability data.
    
    Args:
        station_id: Unique station identifier
        limit: Maximum number of snapshots to return (1-50)
        repo: Station repository dependency
        
    Returns:
        List[AvailabilitySnapshot]: Recent availability snapshots
        
    Raises:
        HTTPException: If station not found or database operation fails
        
    Example:
        GET /api/stations/1/availability?limit=10
    """
    try:
        logger.info(f"Fetching availability history for station {station_id} (limit={limit})")
        
        # Verify station exists
        station = await repo.get_station_by_id(station_id)
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Station with ID {station_id} not found"
            )
        
        # Get recent snapshots
        snapshots = await repo.get_recent_snapshots(station_id, limit=limit)
        
        logger.info(f"Retrieved {len(snapshots)} availability snapshots for station {station_id}")
        return snapshots
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch availability history for station {station_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve availability history"
        )


@router.get("/{station_id}/hourly-averages", response_model=List[HourlyAvailabilityAverage])
async def get_station_hourly_averages(
    station_id: int,
    day_type: Optional[DayType] = Query(None, description="Filter by day type (weekday/weekend)"),
    repo: StationRepository = Depends(get_station_repository)
):
    """
    Get hourly availability averages for a specific station.
    
    This endpoint returns pre-calculated hourly averages showing the average
    number of bikes available during each hour of the day, based on historical data.
    
    Args:
        station_id: Unique station identifier
        day_type: Optional filter by day type (weekday/weekend)
        repo: Station repository dependency
        
    Returns:
        List[HourlyAvailabilityAverage]: Hourly availability averages
        
    Raises:
        HTTPException: If station not found or database operation fails
        
    Example:
        GET /api/stations/1/hourly-averages?day_type=weekday
    """
    try:
        logger.info(f"Fetching hourly averages for station {station_id} (day_type={day_type})")
        
        # Verify station exists
        station = await repo.get_station_by_id(station_id)
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Station with ID {station_id} not found"
            )
        
        # Get hourly averages
        averages = await repo.get_hourly_averages(station_id, day_type)
        
        logger.info(f"Retrieved {len(averages)} hourly averages for station {station_id}")
        return averages
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch hourly averages for station {station_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve hourly averages"
        )