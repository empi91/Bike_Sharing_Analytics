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
    
    async def get_stations_without_address(self) -> List[BikeStation]:
        """
        Get stations that don't have address information.
        
        Returns:
            List[BikeStation]: Stations without addresses
        """
        try:
            result = (
                self.db.client.table('bike_stations')
                .select('*')
                .or_('address.is.null,address.eq.')
                .execute()
            )
            
            stations = [BikeStation(**station) for station in result.data]
            logger.info(f"Found {len(stations)} stations without addresses")
            return stations
            
        except Exception as e:
            logger.error(f"Failed to fetch stations without addresses: {str(e)}")
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
            
            # Convert to dict with proper JSON serialization
            station_dict = station_data.model_dump()
            # Convert Decimal to float for JSON serialization
            station_dict['latitude'] = float(station_dict['latitude'])
            station_dict['longitude'] = float(station_dict['longitude'])
            
            result = self.db.client.table('bike_stations').insert(station_dict).execute()
            
            if result.data:
                created_station = BikeStation(**result.data[0])
                logger.info(f"Created station with ID: {created_station.id}")
                return created_station
            
            raise Exception("Failed to create station - no data returned")
            
        except Exception as e:
            logger.error(f"Failed to create station: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
    
    async def create_stations_batch(self, stations_data: List[BikeStationCreate]) -> List[BikeStation]:
        """
        Create multiple bike stations in a batch operation.
        
        Args:
            stations_data: List of station data to create
            
        Returns:
            List[BikeStation]: List of created stations with generated IDs
        """
        try:
            logger.info(f"Creating {len(stations_data)} stations in batch")
            
            # Convert to dicts for Supabase with proper JSON serialization
            insert_data = []
            for station in stations_data:
                station_dict = station.model_dump()
                # Convert Decimal to float for JSON serialization
                station_dict['latitude'] = float(station_dict['latitude'])
                station_dict['longitude'] = float(station_dict['longitude'])
                insert_data.append(station_dict)
            
            result = self.db.client.table('bike_stations').insert(insert_data).execute()
            
            if result.data:
                created_stations = [BikeStation(**station) for station in result.data]
                logger.info(f"Created {len(created_stations)} stations in batch")
                return created_stations
            
            raise Exception("Failed to create stations - no data returned")
            
        except Exception as e:
            logger.error(f"Failed to create stations batch: {str(e)}")
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
            
            # Convert Decimal to float for JSON serialization
            if 'latitude' in update_data and isinstance(update_data['latitude'], Decimal):
                update_data['latitude'] = float(update_data['latitude'])
            if 'longitude' in update_data and isinstance(update_data['longitude'], Decimal):
                update_data['longitude'] = float(update_data['longitude'])
            
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
    
    async def create_availability_snapshots_batch(self, snapshots_data: List[AvailabilitySnapshotCreate]) -> List[AvailabilitySnapshot]:
        """
        Create multiple availability snapshots in a batch operation.
        
        Args:
            snapshots_data: List of snapshot data to create
            
        Returns:
            List[AvailabilitySnapshot]: List of created snapshots
        """
        try:
            logger.info(f"Creating {len(snapshots_data)} availability snapshots in batch")
            
            # Convert to dicts for Supabase with proper JSON serialization
            insert_data = []
            for snapshot in snapshots_data:
                snapshot_dict = snapshot.model_dump()
                # Convert datetime to ISO string for JSON serialization
                if 'timestamp' in snapshot_dict and snapshot_dict['timestamp']:
                    snapshot_dict['timestamp'] = snapshot_dict['timestamp'].isoformat()
                insert_data.append(snapshot_dict)
            
            result = self.db.client.table('availability_snapshots').insert(insert_data).execute()
            
            if result.data:
                created_snapshots = [AvailabilitySnapshot(**snapshot) for snapshot in result.data]
                logger.info(f"Created {len(created_snapshots)} snapshots in batch")
                return created_snapshots
            
            raise Exception("Failed to create snapshots - no data returned")
            
        except Exception as e:
            logger.error(f"Failed to create snapshots batch: {str(e)}")
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
    
    async def calculate_reliability_scores(
        self, 
        station_id: Optional[int] = None, 
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate reliability scores for stations based on historical data.
        
        Args:
            station_id: Calculate for specific station (None = all stations)
            days_back: Number of days of historical data to analyze
            
        Returns:
            Dict with calculation results and statistics
        """
        try:
            from datetime import date, timedelta
            
            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=days_back)
            
            logger.info(f"Calculating reliability scores for {days_back} days ({start_date} to {end_date})")
            
            # Get stations to process
            if station_id:
                stations = [await self.get_station_by_id(station_id)]
                stations = [s for s in stations if s is not None]
            else:
                stations = await self.get_all_stations(active_only=True)
            
            scores_calculated = 0
            errors = []
            
            for station in stations:
                try:
                    # Calculate scores for this station
                    station_scores = await self._calculate_station_reliability(
                        station.id, start_date, end_date
                    )
                    scores_calculated += len(station_scores)
                    
                except Exception as e:
                    error_msg = f"Error calculating reliability for station {station.id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            result = {
                'stations_processed': len(stations),
                'scores_calculated': scores_calculated,
                'data_period_start': start_date.isoformat(),
                'data_period_end': end_date.isoformat(),
                'errors': errors,
                'success': len(errors) == 0
            }
            
            logger.info(f"Reliability calculation completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to calculate reliability scores: {str(e)}")
            raise Exception(f"Reliability calculation error: {str(e)}")
    
    async def _calculate_station_reliability(
        self, 
        station_id: int, 
        start_date: date, 
        end_date: date
    ) -> List[ReliabilityScore]:
        """
        Calculate reliability scores for a specific station.
        
        Args:
            station_id: Station to calculate for
            start_date: Start of data period
            end_date: End of data period
            
        Returns:
            List of calculated reliability scores
        """
        try:
            from app.schemas.station import ReliabilityScoreCreate
            from datetime import datetime
            
            # Get availability snapshots for the period using Supabase client
            result = (
                self.db.client.table('availability_snapshots')
                .select('hour, day_of_week, available_bikes, timestamp')
                .eq('station_id', station_id)
                .gte('timestamp', f"{start_date}T00:00:00")
                .lte('timestamp', f"{end_date}T23:59:59")
                .execute()
            )
            
            if not result.data:
                logger.info(f"No availability data found for station {station_id} in period {start_date} to {end_date}")
                return []
            
            # Group data by hour and day_type in Python
            grouped_data = {}
            for row in result.data:
                hour = row['hour']
                day_type = 'weekday' if row['day_of_week'] in [1, 2, 3, 4, 5] else 'weekend'
                key = (hour, day_type)
                
                if key not in grouped_data:
                    grouped_data[key] = {
                        'total_snapshots': 0,
                        'bikes_available_count': 0,
                        'total_bikes': 0
                    }
                
                grouped_data[key]['total_snapshots'] += 1
                grouped_data[key]['total_bikes'] += row['available_bikes']
                if row['available_bikes'] > 0:
                    grouped_data[key]['bikes_available_count'] += 1
            
            calculated_scores = []
            
            # Calculate reliability scores for each hour/day_type combination
            for (hour, day_type), data in grouped_data.items():
                # Skip if sample size is too small
                if data['total_snapshots'] < 5:
                    continue
                
                # Calculate reliability percentage
                reliability_percentage = (data['bikes_available_count'] / data['total_snapshots']) * 100
                avg_bikes = data['total_bikes'] / data['total_snapshots']
                
                # Create reliability score
                score_data = ReliabilityScoreCreate(
                    station_id=station_id,
                    hour=hour,
                    day_type=DayType(day_type),
                    reliability_percentage=Decimal(f"{reliability_percentage:.2f}"),
                    avg_available_bikes=Decimal(f"{avg_bikes:.2f}"),
                    sample_size=data['total_snapshots'],
                    data_period_start=start_date,
                    data_period_end=end_date
                )
                
                # Insert or update the score
                await self._upsert_reliability_score(score_data)
                calculated_scores.append(score_data)
            
            logger.info(f"Calculated {len(calculated_scores)} reliability scores for station {station_id}")
            return calculated_scores
            
        except Exception as e:
            logger.error(f"Failed to calculate station reliability for {station_id}: {str(e)}")
            raise
    
    async def _upsert_reliability_score(self, score_data: 'ReliabilityScoreCreate') -> None:
        """
        Insert or update a reliability score (upsert operation).
        
        Args:
            score_data: Reliability score data to upsert
        """
        try:
            # Check if score already exists
            existing = (
                self.db.client.table('reliability_scores')
                .select('id')
                .eq('station_id', score_data.station_id)
                .eq('hour', score_data.hour)
                .eq('day_type', score_data.day_type.value)
                .execute()
            )
            
            score_dict = score_data.model_dump()
            score_dict['day_type'] = score_data.day_type.value  # Convert enum to string
            
            # Convert Decimal to float for JSON serialization
            if 'reliability_percentage' in score_dict:
                score_dict['reliability_percentage'] = float(score_dict['reliability_percentage'])
            if 'avg_available_bikes' in score_dict:
                score_dict['avg_available_bikes'] = float(score_dict['avg_available_bikes'])
            
            if existing.data:
                # Update existing score
                result = (
                    self.db.client.table('reliability_scores')
                    .update(score_dict)
                    .eq('id', existing.data[0]['id'])
                    .execute()
                )
            else:
                # Insert new score
                result = (
                    self.db.client.table('reliability_scores')
                    .insert(score_dict)
                    .execute()
                )
            
            if not result.data:
                raise Exception("Upsert operation returned no data")
                
        except Exception as e:
            logger.error(f"Failed to upsert reliability score: {str(e)}")
            raise

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
            # Convert to dict with proper JSON serialization
            log_dict = log_data.model_dump()
            # Convert datetime to ISO string for JSON serialization
            if 'sync_timestamp' in log_dict and log_dict['sync_timestamp']:
                log_dict['sync_timestamp'] = log_dict['sync_timestamp'].isoformat()
            if 'start_time' in log_dict and log_dict['start_time']:
                log_dict['start_time'] = log_dict['start_time'].isoformat()
            if 'end_time' in log_dict and log_dict['end_time']:
                log_dict['end_time'] = log_dict['end_time'].isoformat()
            
            result = self.db.client.table('api_sync_logs').insert(log_dict).execute()
            
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
    
    # =====================================================
    # HOURLY AVAILABILITY AVERAGES OPERATIONS
    # =====================================================
    
    async def get_hourly_averages(
        self, 
        station_id: int, 
        day_type: Optional[DayType] = None
    ) -> List['HourlyAvailabilityAverage']:
        """
        Get hourly availability averages for a station.
        
        Args:
            station_id: Station identifier
            day_type: Optional filter by day type
            
        Returns:
            List of hourly availability averages
        """
        try:
            from app.schemas.station import HourlyAvailabilityAverage
            
            query = (
                self.db.client.table('hourly_availability_averages')
                .select('*')
                .eq('station_id', station_id)
                .order('hour')
            )
            
            if day_type:
                query = query.eq('day_type', day_type.value)
            
            result = query.execute()
            
            return [HourlyAvailabilityAverage(**avg) for avg in result.data]
            
        except Exception as e:
            logger.error(f"Failed to fetch hourly averages for station {station_id}: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
    
    async def calculate_hourly_averages(self, station_id: int) -> Dict[str, Any]:
        """
        Calculate and store hourly availability averages for a station using database aggregation.
        
        This method uses SQL aggregation for better performance instead of processing in Python.
        
        Args:
            station_id: Station identifier
            
        Returns:
            Dict with calculation results
        """
        try:
            from app.schemas.station import HourlyAvailabilityAverageCreate
            
            logger.debug(f"Calculating hourly averages for station {station_id}")
            
            # Use database aggregation for better performance
            # This query groups by hour and day_type and calculates averages directly in the database
            result = self.db.client.rpc(
                'calculate_hourly_averages',
                {
                    'station_id_param': station_id
                }
            ).execute()
            
            if not result.data:
                logger.info(f"No availability data found for station {station_id}")
                return {'averages_calculated': 0, 'message': 'No data available'}
            
            # Process aggregated results
            averages_calculated = 0
            for row in result.data:
                if row['total_snapshots'] < 5:  # Skip if too few samples
                    continue
                
                # Create average data
                avg_data = HourlyAvailabilityAverageCreate(
                    station_id=station_id,
                    hour=row['hour'],
                    day_type=DayType(row['day_type']),
                    avg_bikes_available=Decimal(f"{row['avg_bikes']:.2f}"),
                    total_snapshots=row['total_snapshots']
                )
                
                # Upsert the average
                await self._upsert_hourly_average(avg_data)
                averages_calculated += 1
            
            logger.debug(f"Calculated {averages_calculated} hourly averages for station {station_id}")
            return {
                'averages_calculated': averages_calculated,
                'data_period': 'All historical data',
                'total_snapshots': sum(row['total_snapshots'] for row in result.data)
            }
            
        except Exception as e:
            # Fallback to Python-based calculation if database function doesn't exist
            logger.warning(f"Database function failed, falling back to Python calculation: {str(e)}")
            return await self._calculate_hourly_averages_fallback(station_id)
    
    async def _calculate_hourly_averages_fallback(self, station_id: int) -> Dict[str, Any]:
        """
        Fallback method using Python-based calculation.
        
        This is used if the database function is not available.
        """
        try:
            from app.schemas.station import HourlyAvailabilityAverageCreate
            
            logger.info(f"Using fallback calculation for station {station_id}")
            
            # Get ALL availability snapshots for this station
            result = (
                self.db.client.table('availability_snapshots')
                .select('hour, day_of_week, available_bikes')
                .eq('station_id', station_id)
                .execute()
            )
            
            if not result.data:
                return {'averages_calculated': 0, 'message': 'No data available'}
            
            # Group data by hour and day_type
            grouped_data = {}
            for row in result.data:
                hour = row['hour']
                day_type = 'weekday' if row['day_of_week'] in [1, 2, 3, 4, 5] else 'weekend'
                key = (hour, day_type)
                
                if key not in grouped_data:
                    grouped_data[key] = {
                        'total_snapshots': 0,
                        'total_bikes': 0
                    }
                
                grouped_data[key]['total_snapshots'] += 1
                grouped_data[key]['total_bikes'] += row['available_bikes']
            
            # Calculate averages and upsert
            averages_calculated = 0
            for (hour, day_type), data in grouped_data.items():
                if data['total_snapshots'] < 5:  # Skip if too few samples
                    continue
                
                avg_bikes = data['total_bikes'] / data['total_snapshots']
                
                # Create average data
                avg_data = HourlyAvailabilityAverageCreate(
                    station_id=station_id,
                    hour=hour,
                    day_type=DayType(day_type),
                    avg_bikes_available=Decimal(f"{avg_bikes:.2f}"),
                    total_snapshots=data['total_snapshots']
                )
                
                # Upsert the average
                await self._upsert_hourly_average(avg_data)
                averages_calculated += 1
            
            return {
                'averages_calculated': averages_calculated,
                'data_period': 'All historical data',
                'total_snapshots': len(result.data)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate hourly averages for station {station_id}: {str(e)}")
            raise Exception(f"Hourly averages calculation error: {str(e)}")
    
    async def _upsert_hourly_average(self, avg_data: 'HourlyAvailabilityAverageCreate') -> None:
        """
        Insert or update a hourly availability average (upsert operation).
        
        Args:
            avg_data: Hourly average data to upsert
        """
        try:
            # Check if average already exists
            existing = (
                self.db.client.table('hourly_availability_averages')
                .select('id')
                .eq('station_id', avg_data.station_id)
                .eq('hour', avg_data.hour)
                .eq('day_type', avg_data.day_type.value)
                .execute()
            )
            
            avg_dict = avg_data.model_dump()
            avg_dict['day_type'] = avg_data.day_type.value
            
            # Convert Decimal to float for JSON serialization
            if 'avg_bikes_available' in avg_dict:
                avg_dict['avg_bikes_available'] = float(avg_dict['avg_bikes_available'])
            
            if existing.data:
                # Update existing
                self.db.client.table('hourly_availability_averages').update(avg_dict).eq('id', existing.data[0]['id']).execute()
            else:
                # Insert new
                self.db.client.table('hourly_availability_averages').insert(avg_dict).execute()
                
        except Exception as e:
            logger.error(f"Failed to upsert hourly average: {str(e)}")
            raise