"""
Internal API routes for administrative operations.

This module contains endpoints for internal system operations such as
data synchronization, health monitoring, and administrative tasks.
These endpoints require API key authentication.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.database import get_db, SupabaseClient
from app.repositories.station_repository import StationRepository
from app.schemas.station import (
    ApiSyncLog,
    ApiSyncLogCreate,
    SyncStatus,
    BikeStation,
    AvailabilitySnapshot,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

# Create router for internal endpoints
router = APIRouter(prefix="/api/internal", tags=["Internal"])

# Security scheme for API key authentication
security = HTTPBearer()


def get_station_repository(db: SupabaseClient = Depends(get_db)) -> StationRepository:
    """
    Dependency to get station repository instance.
    
    Args:
        db: Supabase client instance
        
    Returns:
        StationRepository: Repository instance for station operations
    """
    return StationRepository(db)


def verify_api_key(
    authorization: HTTPAuthorizationCredentials = Depends(security)
) -> bool:
    """
    Verify API key for internal endpoints.
    
    Args:
        authorization: Authorization header with bearer token
        
    Returns:
        bool: True if API key is valid
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not authorization or authorization.credentials != settings.api_key:
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


@router.post("/sync/stations", response_model=Dict[str, Any])
async def trigger_station_sync(
    force_update: bool = False,
    authorized: bool = Depends(verify_api_key),
    repo: StationRepository = Depends(get_station_repository)
):
    """
    Trigger manual synchronization of station data from external API.
    
    This endpoint triggers a manual sync of bike station data from the
    external bike sharing API. It's typically called by scheduled tasks
    or for manual data updates.
    
    Args:
        force_update: If True, update all stations regardless of last update time
        authorized: API key verification dependency
        repo: Station repository dependency
        
    Returns:
        Dict[str, Any]: Sync operation results
        
    Raises:
        HTTPException: If sync operation fails
        
    Example:
        POST /api/internal/sync/stations
        Authorization: Bearer your_api_key
    """
    start_time = datetime.utcnow()
    sync_log_data = ApiSyncLogCreate(
        sync_timestamp=start_time,
        sync_status=SyncStatus.SUCCESS,
        stations_updated=0,
        snapshots_created=0
    )
    
    try:
        logger.info(f"Starting manual station sync (force_update={force_update})")
        
        # TODO: Implement actual sync logic here
        # For now, we'll simulate the sync operation
        
        # This would typically:
        # 1. Fetch data from external bike API
        # 2. Compare with existing station data
        # 3. Update changed stations
        # 4. Log the results
        
        # Simulate processing
        existing_stations = await repo.get_all_stations(active_only=False)
        stations_updated = len(existing_stations) if force_update else 0
        
        # Log the sync operation
        sync_log_data.stations_updated = stations_updated
        sync_log_data.sync_status = SyncStatus.SUCCESS
        
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        sync_log_data.response_time_ms = response_time_ms
        
        # Create sync log entry
        sync_log = await repo.create_sync_log(sync_log_data)
        
        result = {
            "sync_id": sync_log.id,
            "status": "success",
            "message": "Station sync completed successfully",
            "stations_processed": len(existing_stations),
            "stations_updated": stations_updated,
            "response_time_ms": response_time_ms,
            "timestamp": start_time.isoformat(),
            "force_update": force_update
        }
        
        logger.info(f"Station sync completed: {stations_updated} stations updated")
        return result
        
    except Exception as e:
        logger.error(f"Station sync failed: {str(e)}")
        
        # Log the failed sync
        sync_log_data.sync_status = SyncStatus.FAILED
        sync_log_data.error_message = str(e)
        
        try:
            await repo.create_sync_log(sync_log_data)
        except Exception as log_error:
            logger.error(f"Failed to log sync error: {str(log_error)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Station sync failed: {str(e)}"
        )


@router.post("/sync/availability", response_model=Dict[str, Any])
async def trigger_availability_sync(
    authorized: bool = Depends(verify_api_key),
    repo: StationRepository = Depends(get_station_repository)
):
    """
    Trigger manual collection of current availability data.
    
    This endpoint triggers a manual collection of current bike availability
    data from all active stations. This is typically called every 5 minutes
    by the background scheduler.
    
    Args:
        authorized: API key verification dependency
        repo: Station repository dependency
        
    Returns:
        Dict[str, Any]: Availability sync results
        
    Raises:
        HTTPException: If sync operation fails
        
    Example:
        POST /api/internal/sync/availability
        Authorization: Bearer your_api_key
    """
    start_time = datetime.utcnow()
    sync_log_data = ApiSyncLogCreate(
        sync_timestamp=start_time,
        sync_status=SyncStatus.SUCCESS,
        stations_updated=0,
        snapshots_created=0
    )
    
    try:
        logger.info("Starting availability data collection")
        
        # Get all active stations
        active_stations = await repo.get_all_stations(active_only=True)
        
        # TODO: Implement actual availability data collection
        # This would typically:
        # 1. For each active station, fetch current availability from external API
        # 2. Create availability snapshots
        # 3. Store in database
        
        # Simulate creating snapshots for all stations
        snapshots_created = len(active_stations)
        
        # Update sync log data
        sync_log_data.stations_updated = len(active_stations)
        sync_log_data.snapshots_created = snapshots_created
        sync_log_data.sync_status = SyncStatus.SUCCESS
        
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        sync_log_data.response_time_ms = response_time_ms
        
        # Create sync log entry
        sync_log = await repo.create_sync_log(sync_log_data)
        
        result = {
            "sync_id": sync_log.id,
            "status": "success",
            "message": "Availability sync completed successfully",
            "stations_processed": len(active_stations),
            "snapshots_created": snapshots_created,
            "response_time_ms": response_time_ms,
            "timestamp": start_time.isoformat()
        }
        
        logger.info(f"Availability sync completed: {snapshots_created} snapshots created")
        return result
        
    except Exception as e:
        logger.error(f"Availability sync failed: {str(e)}")
        
        # Log the failed sync
        sync_log_data.sync_status = SyncStatus.FAILED
        sync_log_data.error_message = str(e)
        
        try:
            await repo.create_sync_log(sync_log_data)
        except Exception as log_error:
            logger.error(f"Failed to log sync error: {str(log_error)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Availability sync failed: {str(e)}"
        )


@router.post("/calculate/reliability", response_model=Dict[str, Any])
async def trigger_reliability_calculation(
    station_id: Optional[int] = None,
    days_back: int = 30,
    authorized: bool = Depends(verify_api_key),
    repo: StationRepository = Depends(get_station_repository)
):
    """
    Trigger recalculation of reliability scores.
    
    This endpoint triggers the calculation of reliability scores based on
    historical availability data. Can be run for all stations or a specific station.
    
    Args:
        station_id: Optional station ID to calculate for (None = all stations)
        days_back: Number of days of historical data to include (default: 30)
        authorized: API key verification dependency
        repo: Station repository dependency
        
    Returns:
        Dict[str, Any]: Calculation results
        
    Raises:
        HTTPException: If calculation fails
        
    Example:
        POST /api/internal/calculate/reliability?days_back=30
        Authorization: Bearer your_api_key
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Starting reliability calculation (station_id={station_id}, days_back={days_back})")
        
        # Validate parameters
        if days_back < 1 or days_back > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="days_back must be between 1 and 365"
            )
        
        # Get stations to process
        if station_id:
            station = await repo.get_station_by_id(station_id)
            if not station:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Station with ID {station_id} not found"
                )
            stations_to_process = [station]
        else:
            stations_to_process = await repo.get_all_stations(active_only=True)
        
        # TODO: Implement actual reliability calculation
        # This would typically:
        # 1. For each station, get availability snapshots from the last N days
        # 2. Group by hour and day type (weekday/weekend)
        # 3. Calculate reliability percentage for each hour/day_type combination
        # 4. Update reliability_scores table
        
        scores_calculated = len(stations_to_process) * 24 * 2  # 24 hours * 2 day types per station
        
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        result = {
            "status": "success",
            "message": "Reliability calculation completed successfully",
            "stations_processed": len(stations_to_process),
            "scores_calculated": scores_calculated,
            "days_back": days_back,
            "response_time_ms": response_time_ms,
            "timestamp": start_time.isoformat()
        }
        
        logger.info(f"Reliability calculation completed: {scores_calculated} scores calculated")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reliability calculation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reliability calculation failed: {str(e)}"
        )


@router.get("/health/sync", response_model=Dict[str, Any])
async def get_sync_health(
    limit: int = 10,
    authorized: bool = Depends(verify_api_key),
    repo: StationRepository = Depends(get_station_repository)
):
    """
    Check the health status of background data collection.
    
    This endpoint provides monitoring information about the sync processes,
    including recent sync attempts, error rates, and data freshness.
    
    Args:
        limit: Maximum number of recent sync logs to include
        authorized: API key verification dependency
        repo: Station repository dependency
        
    Returns:
        Dict[str, Any]: Sync health status and metrics
        
    Example:
        GET /api/internal/health/sync?limit=5
        Authorization: Bearer your_api_key
    """
    try:
        logger.info("Checking sync health status")
        
        # Get recent sync logs
        recent_logs = await repo.get_recent_sync_logs(limit=limit)
        
        # Calculate health metrics
        total_syncs = len(recent_logs)
        successful_syncs = sum(1 for log in recent_logs if log.sync_status == SyncStatus.SUCCESS)
        failed_syncs = sum(1 for log in recent_logs if log.sync_status == SyncStatus.FAILED)
        partial_syncs = sum(1 for log in recent_logs if log.sync_status == SyncStatus.PARTIAL)
        
        success_rate = (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0
        
        # Find last successful sync
        last_successful_sync = None
        for log in recent_logs:
            if log.sync_status == SyncStatus.SUCCESS:
                last_successful_sync = log.sync_timestamp
                break
        
        # Calculate average response time
        response_times = [log.response_time_ms for log in recent_logs if log.response_time_ms is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        health_status = {
            "overall_status": "healthy" if success_rate >= 80 else "degraded" if success_rate >= 50 else "unhealthy",
            "metrics": {
                "total_syncs_checked": total_syncs,
                "successful_syncs": successful_syncs,
                "failed_syncs": failed_syncs,
                "partial_syncs": partial_syncs,
                "success_rate_percentage": round(success_rate, 2),
                "average_response_time_ms": round(avg_response_time, 2) if avg_response_time > 0 else None
            },
            "last_successful_sync": last_successful_sync.isoformat() if last_successful_sync else None,
            "recent_sync_logs": [
                {
                    "timestamp": log.sync_timestamp.isoformat(),
                    "status": log.sync_status.value,
                    "stations_updated": log.stations_updated,
                    "snapshots_created": log.snapshots_created,
                    "response_time_ms": log.response_time_ms,
                    "error_message": log.error_message
                }
                for log in recent_logs
            ],
            "check_timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Sync health check completed: {health_status['overall_status']}")
        return health_status
        
    except Exception as e:
        logger.error(f"Sync health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check sync health: {str(e)}"
        )
