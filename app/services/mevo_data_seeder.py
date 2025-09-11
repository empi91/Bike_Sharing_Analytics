"""
MEVO Data Seeding Service.

This service handles fetching data from MEVO GBFS API and storing it in
the Supabase database. It manages both initial seeding and incremental updates.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from decimal import Decimal

from app.services.mevo_api_client import MevoApiClient, MevoApiError
from app.repositories.station_repository import StationRepository
from app.schemas.station import (
    BikeStationCreate,
    AvailabilitySnapshotCreate,
    ApiSyncLogCreate,
    SyncStatus
)
from app.core.database import SupabaseClient

logger = logging.getLogger(__name__)


class MevoDataSeeder:
    """
    Service for seeding and updating database with MEVO data.
    
    This service coordinates between the MEVO API client and the database
    repository to ensure data consistency and proper error handling.
    """
    
    def __init__(self, db: SupabaseClient):
        """
        Initialize the data seeder.
        
        Args:
            db: Supabase database client
        """
        self.db = db
        self.repository = StationRepository(db)
    
    async def seed_initial_stations(self) -> Dict[str, Any]:
        """
        Perform initial seeding of MEVO stations.
        
        Fetches all stations from MEVO API and stores them in the database.
        This should be run once during initial setup.
        
        Returns:
            Dict containing seeding statistics and results
        """
        start_time = datetime.now(timezone.utc)
        stats = {
            'start_time': start_time.isoformat(),
            'stations_fetched': 0,
            'stations_created': 0,
            'stations_updated': 0,
            'stations_skipped': 0,
            'errors': [],
            'success': False
        }
        
        try:
            logger.info("Starting MEVO initial station seeding")
            
            async with MevoApiClient() as mevo_client:
                # Fetch system information first
                try:
                    system_info = await mevo_client.get_system_information()
                    logger.info(f"Connected to {system_info.name} system (ID: {system_info.system_id})")
                except Exception as e:
                    logger.error(f"Failed to fetch system info: {str(e)}")
                    stats['errors'].append(f"System info error: {str(e)}")
                
                # Fetch all stations
                stations = await mevo_client.get_station_information()
                stats['stations_fetched'] = len(stations)
                
                logger.info(f"Fetched {len(stations)} stations from MEVO API")
                
                # Process stations in batches for better performance
                await self._process_stations_batch(stations, stats)
                
                # Create sync log entry
                end_time = datetime.now(timezone.utc)
                response_time_ms = int((end_time - start_time).total_seconds() * 1000)
                
                sync_status = SyncStatus.SUCCESS if not stats['errors'] else (
                    SyncStatus.PARTIAL if stats['stations_created'] > 0 else SyncStatus.FAILED
                )
                
                sync_log = ApiSyncLogCreate(
                    sync_timestamp=start_time,
                    sync_status=sync_status,
                    stations_updated=stats['stations_created'] + stats['stations_updated'],
                    snapshots_created=0,  # No snapshots in initial seeding
                    error_message='; '.join(stats['errors']) if stats['errors'] else None,
                    response_time_ms=response_time_ms
                )
                
                try:
                    await self.repository.create_sync_log(sync_log)
                except Exception as e:
                    logger.error(f"Failed to create sync log: {str(e)}")
                
                stats['success'] = sync_status in [SyncStatus.SUCCESS, SyncStatus.PARTIAL]
                stats['end_time'] = end_time.isoformat()
                stats['duration_ms'] = response_time_ms
                
                logger.info(f"Initial seeding completed: {stats}")
                return stats
                
        except MevoApiError as e:
            error_msg = f"MEVO API error during seeding: {str(e)}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            return stats
            
        except Exception as e:
            error_msg = f"Unexpected error during seeding: {str(e)}"
            logger.error(error_msg, exc_info=True)
            stats['errors'].append(error_msg)
            return stats
    
    async def sync_station_status(self) -> Dict[str, Any]:
        """
        Sync current station status and create availability snapshots.
        
        This method should be called periodically (every 5 minutes) to
        collect real-time availability data.
        
        Returns:
            Dict containing sync statistics and results
        """
        start_time = datetime.now(timezone.utc)
        stats = {
            'start_time': start_time.isoformat(),
            'stations_processed': 0,
            'snapshots_created': 0,
            'errors': [],
            'success': False
        }
        
        try:
            logger.info("Starting MEVO station status sync")
            
            async with MevoApiClient() as mevo_client:
                # Get current status for all stations
                station_statuses = await mevo_client.get_station_status()
                
                logger.info(f"Fetched status for {len(station_statuses)} stations")
                
                # Process station statuses in batch for better performance
                await self._process_station_statuses_batch(station_statuses, start_time, stats)
                
                # Create sync log entry
                end_time = datetime.now(timezone.utc)
                response_time_ms = int((end_time - start_time).total_seconds() * 1000)
                
                sync_status = SyncStatus.SUCCESS if not stats['errors'] else (
                    SyncStatus.PARTIAL if stats['snapshots_created'] > 0 else SyncStatus.FAILED
                )
                
                sync_log = ApiSyncLogCreate(
                    sync_timestamp=start_time,
                    sync_status=sync_status,
                    stations_updated=stats['stations_processed'],
                    snapshots_created=stats['snapshots_created'],
                    error_message='; '.join(stats['errors']) if stats['errors'] else None,
                    response_time_ms=response_time_ms
                )
                
                try:
                    await self.repository.create_sync_log(sync_log)
                except Exception as e:
                    logger.error(f"Failed to create sync log: {str(e)}")
                
                stats['success'] = sync_status in [SyncStatus.SUCCESS, SyncStatus.PARTIAL]
                stats['end_time'] = end_time.isoformat()
                stats['duration_ms'] = response_time_ms
                
                logger.info(f"Status sync completed: {stats}")
                return stats
                
        except MevoApiError as e:
            error_msg = f"MEVO API error during status sync: {str(e)}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            return stats
            
        except Exception as e:
            error_msg = f"Unexpected error during status sync: {str(e)}"
            logger.error(error_msg, exc_info=True)
            stats['errors'].append(error_msg)
            return stats
    
    async def _process_stations_batch(self, mevo_stations, stats: Dict[str, Any]) -> None:
        """
        Process MEVO stations in efficient batches.
        
        Args:
            mevo_stations: List of station data from MEVO API
            stats: Statistics dictionary to update
        """
        try:
            # Separate new stations from existing ones
            new_stations = []
            stations_to_update = []
            
            # Check which stations already exist
            for mevo_station in mevo_stations:
                try:
                    existing_station = await self.repository.get_station_by_external_id(
                        mevo_station.station_id
                    )
                    
                    station_data = BikeStationCreate(
                        external_station_id=mevo_station.station_id,
                        name=mevo_station.name,
                        address=mevo_station.address,  # Include address from MEVO API
                        latitude=Decimal(str(mevo_station.lat)),
                        longitude=Decimal(str(mevo_station.lon)),
                        total_docks=mevo_station.capacity,  # Virtual station capacity
                        is_active=True
                    )
                    
                    if existing_station:
                        stations_to_update.append((existing_station, station_data))
                    else:
                        new_stations.append(station_data)
                        
                except Exception as e:
                    error_msg = f"Error processing station {mevo_station.station_id}: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
                    stats['stations_skipped'] += 1
            
            # Batch create new stations
            if new_stations:
                try:
                    created_stations = await self.repository.create_stations_batch(new_stations)
                    stats['stations_created'] += len(created_stations)
                    logger.info(f"Created {len(created_stations)} new stations in batch")
                except Exception as e:
                    error_msg = f"Error creating stations batch: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
                    stats['stations_skipped'] += len(new_stations)
            
            # Update existing stations (done individually for now)
            for existing_station, station_data in stations_to_update:
                try:
                    from app.schemas.station import BikeStationUpdate
                    update_data = BikeStationUpdate(
                        name=station_data.name,
                        address=station_data.address,  # Include address in updates
                        latitude=station_data.latitude,
                        longitude=station_data.longitude,
                        total_docks=station_data.total_docks,
                        is_active=station_data.is_active
                    )
                    
                    updated_station = await self.repository.update_station(
                        existing_station.id, update_data
                    )
                    
                    if updated_station:
                        stats['stations_updated'] += 1
                    else:
                        stats['stations_skipped'] += 1
                        
                except Exception as e:
                    error_msg = f"Error updating station {existing_station.external_station_id}: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
                    stats['stations_skipped'] += 1
                    
        except Exception as e:
            logger.error(f"Error in batch station processing: {str(e)}")
            raise

    async def _process_station(self, mevo_station, stats: Dict[str, Any]) -> None:
        """
        Process a single MEVO station for database storage.
        
        Args:
            mevo_station: Station data from MEVO API
            stats: Statistics dictionary to update
        """
        try:
            # Check if station already exists
            existing_station = await self.repository.get_station_by_external_id(
                mevo_station.station_id
            )
            
            # For MEVO virtual stations, use capacity as total_docks
            # This maps the virtual station concept to our physical dock model
            station_data = BikeStationCreate(
                external_station_id=mevo_station.station_id,
                name=mevo_station.name,
                address=mevo_station.address,  # Include address from MEVO API
                latitude=Decimal(str(mevo_station.lat)),
                longitude=Decimal(str(mevo_station.lon)),
                total_docks=mevo_station.capacity,  # Virtual station capacity
                is_active=True
            )
            
            if existing_station:
                # Update existing station
                from app.schemas.station import BikeStationUpdate
                update_data = BikeStationUpdate(
                    name=station_data.name,
                    address=station_data.address,  # Include address in updates
                    latitude=station_data.latitude,
                    longitude=station_data.longitude,
                    total_docks=station_data.total_docks,
                    is_active=station_data.is_active
                )
                
                updated_station = await self.repository.update_station(
                    existing_station.id, update_data
                )
                
                if updated_station:
                    logger.info(f"Updated station: {updated_station.name} (ID: {updated_station.external_station_id})")
                    stats['stations_updated'] += 1
                else:
                    logger.warning(f"Failed to update station {mevo_station.station_id}")
                    stats['stations_skipped'] += 1
            else:
                # Create new station
                new_station = await self.repository.create_station(station_data)
                logger.info(f"Created station: {new_station.name} (ID: {new_station.external_station_id})")
                stats['stations_created'] += 1
                
        except Exception as e:
            logger.error(f"Error processing station {mevo_station.station_id}: {str(e)}")
            raise
    
    async def _process_station_statuses_batch(
        self, 
        station_statuses, 
        timestamp: datetime, 
        stats: Dict[str, Any]
    ) -> None:
        """
        Process station statuses in efficient batches.
        
        Args:
            station_statuses: List of station status data from MEVO API
            timestamp: Timestamp for the snapshots
            stats: Statistics dictionary to update
        """
        try:
            # Get all stations from database for lookup
            all_stations = await self.repository.get_all_stations(active_only=False)
            station_lookup = {station.external_station_id: station for station in all_stations}
            
            # Build batch of snapshots
            snapshots_to_create = []
            
            for status in station_statuses:
                try:
                    station = station_lookup.get(status.station_id)
                    
                    if not station:
                        logger.warning(f"Station {status.station_id} not found in database, skipping status")
                        continue
                    
                    # Calculate time-based fields
                    day_of_week = timestamp.isoweekday()  # 1=Monday, 7=Sunday
                    hour = timestamp.hour
                    minute_slot = (timestamp.minute // 15) * 15  # Round to 15-minute intervals
                    
                    # Create availability snapshot data
                    snapshot_data = AvailabilitySnapshotCreate(
                        station_id=station.id,
                        available_bikes=status.num_bikes_available,
                        available_docks=status.num_docks_available,
                        is_renting=status.is_renting,
                        is_returning=status.is_returning,
                        timestamp=timestamp,
                        day_of_week=day_of_week,
                        hour=hour,
                        minute_slot=minute_slot
                    )
                    
                    snapshots_to_create.append(snapshot_data)
                    stats['stations_processed'] += 1
                    
                except Exception as e:
                    error_msg = f"Error preparing snapshot for station {status.station_id}: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            # Batch create all snapshots
            if snapshots_to_create:
                try:
                    created_snapshots = await self.repository.create_availability_snapshots_batch(snapshots_to_create)
                    stats['snapshots_created'] += len(created_snapshots)
                    logger.info(f"Created {len(created_snapshots)} availability snapshots in batch")
                except Exception as e:
                    error_msg = f"Error creating snapshots batch: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
                    
        except Exception as e:
            logger.error(f"Error in batch status processing: {str(e)}")
            raise

    async def _process_station_status(
        self, 
        status, 
        timestamp: datetime, 
        stats: Dict[str, Any]
    ) -> None:
        """
        Process station status and create availability snapshot.
        
        Args:
            status: Station status from MEVO API
            timestamp: Timestamp for the snapshot
            stats: Statistics dictionary to update
        """
        try:
            # Find the corresponding station in our database
            station = await self.repository.get_station_by_external_id(status.station_id)
            
            if not station:
                logger.warning(f"Station {status.station_id} not found in database, skipping status")
                return
            
            # Calculate time-based fields
            day_of_week = timestamp.isoweekday()  # 1=Monday, 7=Sunday
            hour = timestamp.hour
            minute_slot = (timestamp.minute // 15) * 15  # Round to 15-minute intervals
            
            # Create availability snapshot
            snapshot_data = AvailabilitySnapshotCreate(
                station_id=station.id,
                available_bikes=status.num_bikes_available,
                available_docks=status.num_docks_available,
                is_renting=status.is_renting,
                is_returning=status.is_returning,
                timestamp=timestamp,
                day_of_week=day_of_week,
                hour=hour,
                minute_slot=minute_slot
            )
            
            snapshot = await self.repository.create_availability_snapshot(snapshot_data)
            logger.debug(f"Created availability snapshot for station {station.name}")
            
            stats['stations_processed'] += 1
            stats['snapshots_created'] += 1
            
        except Exception as e:
            logger.error(f"Error processing status for station {status.station_id}: {str(e)}")
            raise
    
    async def get_seeding_summary(self) -> Dict[str, Any]:
        """
        Get summary of current database state.
        
        Returns:
            Dict containing database statistics
        """
        try:
            # Get all stations
            stations = await self.repository.get_all_stations(active_only=False)
            
            # Get recent sync logs
            recent_logs = await self.repository.get_recent_sync_logs(limit=5)
            
            # Get total snapshots count (approximate)
            # Note: This might need a custom query for better performance
            
            summary = {
                'total_stations': len(stations),
                'active_stations': len([s for s in stations if s.is_active]),
                'inactive_stations': len([s for s in stations if not s.is_active]),
                'recent_syncs': [
                    {
                        'timestamp': log.sync_timestamp.isoformat(),
                        'status': log.sync_status,
                        'stations_updated': log.stations_updated,
                        'snapshots_created': log.snapshots_created,
                        'response_time_ms': log.response_time_ms
                    }
                    for log in recent_logs
                ],
                'stations_by_area': self._group_stations_by_area(stations)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating seeding summary: {str(e)}")
            raise
    
    def _group_stations_by_area(self, stations) -> Dict[str, int]:
        """
        Group stations by area based on name prefix.
        
        Args:
            stations: List of station objects
            
        Returns:
            Dict with area counts
        """
        areas = {}
        
        for station in stations:
            # Extract area from station name prefix
            if station.name.startswith('GDA'):
                area = 'Gdańsk'
            elif station.name.startswith('GPG'):
                area = 'Gdynia'
            elif station.name.startswith('SOP'):
                area = 'Sopot'
            else:
                area = 'Other'
            
            areas[area] = areas.get(area, 0) + 1
        
        return areas
