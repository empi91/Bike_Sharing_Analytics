"""
Repository for bike station data access operations.

This module handles all database operations related to bike stations,
providing a clean interface between the business logic and Supabase.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal

from app.core.database import SupabaseClient
from app.schemas.station import (
    BikeStation,
    BikeStationCreate,
    BikeStationUpdate,
    AvailabilitySnapshot,
    AvailabilitySnapshotCreate,
    ReliabilityScore,
    ApiSyncLog,
    ApiSyncLogCreate,
    DayType,
)

logger = logging.getLogger(__name__)


class StationRepository:
    """
    Repository class for bike station data operations.
    
    This class handles all database interactions for bike stations,
    availability snapshots, reliability scores, and sync logs.
    """
    
    def __init__(self, db: SupabaseClient):
        """
        Initialize the repository with a database client.
        
        Args:
            db: Supabase client instance for database operations
        """
        self.db = db
    
    # =====================================================
    # BIKE STATION OPERATIONS
    # =====================================================
    
    async def get_all_stations(self, active_only: bool = True) -> List[BikeStation]:
        """
        Get all bike stations.
        
        Args:
            active_only: If True, only return active stations
            
        Returns:
            List[BikeStation]: List of bike stations
            
        Raises:
            Exception: If database query fails
        """
        try:
            logger.info(f"Fetching all stations (active_only={active_only})")
            
            query = self.db.client.table('bike_stations').select('*')
            
            if active_only:
                query = query.eq('is_active', True)
            
            result = query.execute()
            
            stations = [BikeStation(**station) for station in result.data]
            logger.info(f"Retrieved {len(stations)} stations")
            
            return stations
            
        except Exception as e:
            logger.error(f"Failed to fetch stations: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
    
    async def get_station_by_id(self, station_id: int) -> Optional[BikeStation]:
        """
        Get a bike station by its ID.
        
        Args:
            station_id: Station ID to search for
            
        Returns:
            Optional[BikeStation]: Station if found, None otherwise
        """
        try:
            logger.info(f"Fetching station with ID: {station_id}")
            
            result = self.db.client.table('bike_stations').select('*').eq('id', station_id).execute()
            
            if result.data:
                station = BikeStation(**result.data[0])
                logger.info(f"Found station: {station.name}")
                return station
            
            logger.info(f"Station with ID {station_id} not found")
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch station {station_id}: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
    
    async def get_station_by_external_id(self, external_id: str) -> Optional[BikeStation]:
        """
        Get a bike station by its external API ID.
        
        Args:
            external_id: External station ID from bike sharing API
            
        Returns:
            Optional[BikeStation]: Station if found, None otherwise
        """
        try:
            result = self.db.client.table('bike_stations').select('*').eq('external_station_id', external_id).execute()
            
            if result.data:
                return BikeStation(**result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch station by external ID {external_id}: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
    
    async def create_station(self, station_data: BikeStationCreate) -> BikeStation:
        """
        Create a new bike station.
        
        Args:
            station_data: Station data to create
            
        Returns:
            BikeStation: Created station with generated ID
        """
        try:
            logger.info(f"Creating new station: {station_data.name}")
            
            result = self.db.client.table('bike_stations').insert(station_data.model_dump()).execute()
            
            if result.data:
                created_station = BikeStation(**result.data[0])
                logger.info(f"Created station with ID: {created_station.id}")
                return created_station
            
            raise Exception("Failed to create station - no data returned")
            
        except Exception as e:
            logger.error(f"Failed to create station: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
    
    async def update_station(self, station_id: int, station_data: BikeStationUpdate) -> Optional[BikeStation]:
        """
        Update an existing bike station.
        
        Args:
            station_id: ID of station to update
            station_data: Updated station data
            
        Returns:
            Optional[BikeStation]: Updated station if successful, None if not found
        """
        try:
            logger.info(f"Updating station {station_id}")
            
            # Only include non-None fields in update
            update_data = {k: v for k, v in station_data.model_dump().items() if v is not None}
            
            if not update_data:
                logger.warning("No fields to update")
                return await self.get_station_by_id(station_id)
            
            result = self.db.client.table('bike_stations').update(update_data).eq('id', station_id).execute()
            
            if result.data:
                updated_station = BikeStation(**result.data[0])
                logger.info(f"Updated station: {updated_station.name}")
                return updated_station
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to update station {station_id}: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
    
    # =====================================================
    # NEARBY STATIONS (SPATIAL QUERIES)
    # =====================================================
    
    async def get_nearby_stations(
        self, 
        latitude: float, 
        longitude: float, 
        limit: int = 5, 
        max_distance_km: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Get nearby stations using simple distance calculation.
        
        Args:
            latitude: Search center latitude
            longitude: Search center longitude
            limit: Maximum number of stations to return
            max_distance_km: Maximum search radius in kilometers
            
        Returns:
            List[Dict]: Stations with distance calculations
        """
        try:
            logger.info(f"Searching for stations near ({latitude}, {longitude})")
            
            # For now, use simple approach - get all stations and calculate distance in Python
            # TODO: Implement PostGIS spatial queries later
            all_stations = await self.get_all_stations()
            
            stations_with_distance = []
            for station in all_stations:
                # Simple distance calculation (approximate)
                lat_diff = float(station.latitude) - latitude
                lng_diff = float(station.longitude) - longitude
                distance_km = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111  # Rough km conversion
                
                if distance_km <= max_distance_km:
                    station_dict = station.model_dump()
                    station_dict['distance_km'] = distance_km
                    stations_with_distance.append(station_dict)
            
            # Sort by distance and limit results
            stations_with_distance.sort(key=lambda x: x['distance_km'])
            result = stations_with_distance[:limit]
            
            logger.info(f"Found {len(result)} nearby stations")
            return result
            
        except Exception as e:
            logger.error(f"Failed to find nearby stations: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
    
    # =====================================================
    # AVAILABILITY SNAPSHOT OPERATIONS
    # =====================================================
    
    async def create_availability_snapshot(self, snapshot_data: AvailabilitySnapshotCreate) -> AvailabilitySnapshot:
        """
        Create a new availability snapshot.
        
        Args:
            snapshot_data: Availability snapshot data
            
        Returns:
            AvailabilitySnapshot: Created snapshot
        """
        try:
            result = self.db.client.table('availability_snapshots').insert(snapshot_data.model_dump()).execute()
            
            if result.data:
                return AvailabilitySnapshot(**result.data[0])
            
            raise Exception("Failed to create snapshot - no data returned")
            
        except Exception as e:
            logger.error(f"Failed to create availability snapshot: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
    
    async def get_recent_snapshots(self, station_id: int, limit: int = 10) -> List[AvailabilitySnapshot]:
        """
        Get recent availability snapshots for a station.
        
        Args:
            station_id: Station ID to get snapshots for
            limit: Maximum number of snapshots to return
            
        Returns:
            List[AvailabilitySnapshot]: Recent snapshots
        """
        try:
            result = (
                self.db.client.table('availability_snapshots')
                .select('*')
                .eq('station_id', station_id)
                .order('timestamp', desc=True)
                .limit(limit)
                .execute()
            )
            
            return [AvailabilitySnapshot(**snapshot) for snapshot in result.data]
            
        except Exception as e:
            logger.error(f"Failed to fetch recent snapshots for station {station_id}: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
    
    # =====================================================
    # RELIABILITY SCORE OPERATIONS
    # =====================================================
    
    async def get_reliability_scores(
        self, 
        station_id: int, 
        day_type: Optional[DayType] = None
    ) -> List[ReliabilityScore]:
        """
        Get reliability scores for a station.
        
        Args:
            station_id: Station ID to get scores for
            day_type: Filter by day type (weekday/weekend)
            
        Returns:
            List[ReliabilityScore]: Reliability scores
        """
        try:
            query = self.db.client.table('reliability_scores').select('*').eq('station_id', station_id)
            
            if day_type:
                query = query.eq('day_type', day_type.value)
            
            result = query.order('hour').execute()
            
            return [ReliabilityScore(**score) for score in result.data]
            
        except Exception as e:
            logger.error(f"Failed to fetch reliability scores for station {station_id}: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
    
    # =====================================================
    # API SYNC LOG OPERATIONS
    # =====================================================
    
    async def create_sync_log(self, log_data: ApiSyncLogCreate) -> ApiSyncLog:
        """
        Create a new API sync log entry.
        
        Args:
            log_data: Sync log data
            
        Returns:
            ApiSyncLog: Created log entry
        """
        try:
            result = self.db.client.table('api_sync_logs').insert(log_data.model_dump()).execute()
            
            if result.data:
                return ApiSyncLog(**result.data[0])
            
            raise Exception("Failed to create sync log - no data returned")
            
        except Exception as e:
            logger.error(f"Failed to create sync log: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
    
    async def get_recent_sync_logs(self, limit: int = 10) -> List[ApiSyncLog]:
        """
        Get recent API sync logs.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List[ApiSyncLog]: Recent sync logs
        """
        try:
            result = (
                self.db.client.table('api_sync_logs')
                .select('*')
                .order('sync_timestamp', desc=True)
                .limit(limit)
                .execute()
            )
            
            return [ApiSyncLog(**log) for log in result.data]
            
        except Exception as e:
            logger.error(f"Failed to fetch recent sync logs: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
