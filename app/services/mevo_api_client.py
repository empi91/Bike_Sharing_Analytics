"""
MEVO Gdańsk Bike Sharing API Client.

This module provides an asynchronous client for interacting with the MEVO 
bike sharing system GBFS API. MEVO operates in Gdańsk, Poland and provides
real-time information about bike stations and availability.

GBFS Endpoints:
- Discovery: https://gbfs.urbansharing.com/rowermevo.pl/gbfs.json
- System Info: https://gbfs.urbansharing.com/rowermevo.pl/system_information.json
- Station Info: https://gbfs.urbansharing.com/rowermevo.pl/station_information.json
- Station Status: https://gbfs.urbansharing.com/rowermevo.pl/station_status.json

System Details:
- System ID: inurba-gdansk
- Operator: Inurba
- Timezone: Europe/Warsaw
- Language: Polish (pl)
- Uses virtual stations with polygonal areas
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import httpx
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class MevoSystemInfo(BaseModel):
    """MEVO system information model."""
    system_id: str
    language: str
    name: str
    operator: str
    timezone: str
    phone_number: str
    email: str
    rental_apps: Dict[str, Dict[str, str]]


class MevoStation(BaseModel):
    """MEVO station information model."""
    station_id: str
    name: str
    address: str
    cross_street: str
    lat: float
    lon: float
    is_virtual_station: bool
    capacity: int
    station_area: Optional[Dict[str, Any]] = None  # GeoJSON MultiPolygon
    rental_uris: Dict[str, str]


class MevoStationStatus(BaseModel):
    """MEVO station status model."""
    station_id: str
    num_bikes_available: int
    num_docks_available: int
    is_installed: bool
    is_renting: bool
    is_returning: bool
    last_reported: int  # Unix timestamp


class MevoApiError(Exception):
    """Custom exception for MEVO API errors."""
    pass


class MevoApiClient:
    """
    Asynchronous client for MEVO Gdańsk bike sharing GBFS API.
    
    This client handles all interactions with the MEVO GBFS feeds,
    including system information, station data, and real-time status.
    """
    
    def __init__(self):
        """Initialize the MEVO API client."""
        self.timeout = httpx.Timeout(settings.api_request_timeout)
        self.base_urls = {
            'discovery': settings.mevo_gbfs_discovery_url,
            'system_info': settings.mevo_system_info_url,
            'station_info': settings.mevo_station_info_url,
            'station_status': settings.mevo_station_status_url,
        }
        self._session: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._session = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.aclose()
    
    async def _make_request(self, url: str) -> Dict[str, Any]:
        """
        Make an HTTP request to the MEVO API.
        
        Args:
            url: The URL to request
            
        Returns:
            Dict containing the JSON response
            
        Raises:
            MevoApiError: If the request fails or returns invalid data
        """
        if not self._session:
            raise MevoApiError("Client session not initialized. Use async context manager.")
        
        try:
            logger.info(f"Making request to MEVO API: {url}")
            response = await self._session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            # Validate GBFS response structure
            if 'data' not in data:
                raise MevoApiError(f"Invalid GBFS response structure from {url}")
            
            logger.info(f"Successfully fetched data from {url}")
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from MEVO API {url}: {e.response.status_code}")
            raise MevoApiError(f"HTTP {e.response.status_code} error from MEVO API")
        
        except httpx.RequestError as e:
            logger.error(f"Request error to MEVO API {url}: {str(e)}")
            raise MevoApiError(f"Network error connecting to MEVO API: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error fetching from {url}: {str(e)}")
            raise MevoApiError(f"Unexpected error: {str(e)}")
    
    async def get_system_information(self) -> MevoSystemInfo:
        """
        Get MEVO system information.
        
        Returns:
            MevoSystemInfo: System details including operator, timezone, etc.
        """
        try:
            response = await self._make_request(self.base_urls['system_info'])
            system_data = response['data']
            
            return MevoSystemInfo(**system_data)
            
        except Exception as e:
            logger.error(f"Failed to fetch MEVO system information: {str(e)}")
            raise MevoApiError(f"Failed to get system information: {str(e)}")
    
    async def get_station_information(self) -> List[MevoStation]:
        """
        Get all MEVO station information.
        
        Returns:
            List[MevoStation]: List of all stations with locations and details
        """
        try:
            response = await self._make_request(self.base_urls['station_info'])
            stations_data = response['data']['stations']
            
            stations = []
            for station_data in stations_data:
                try:
                    station = MevoStation(**station_data)
                    stations.append(station)
                except Exception as e:
                    logger.warning(f"Failed to parse station {station_data.get('station_id', 'unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Retrieved {len(stations)} MEVO stations")
            return stations
            
        except Exception as e:
            logger.error(f"Failed to fetch MEVO station information: {str(e)}")
            raise MevoApiError(f"Failed to get station information: {str(e)}")
    
    async def get_station_status(self) -> List[MevoStationStatus]:
        """
        Get real-time status for all MEVO stations.
        
        Returns:
            List[MevoStationStatus]: Current availability and status for all stations
        """
        try:
            response = await self._make_request(self.base_urls['station_status'])
            statuses_data = response['data']['stations']
            
            statuses = []
            for status_data in statuses_data:
                try:
                    status = MevoStationStatus(**status_data)
                    statuses.append(status)
                except Exception as e:
                    logger.warning(f"Failed to parse station status {status_data.get('station_id', 'unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Retrieved status for {len(statuses)} MEVO stations")
            return statuses
            
        except Exception as e:
            logger.error(f"Failed to fetch MEVO station status: {str(e)}")
            raise MevoApiError(f"Failed to get station status: {str(e)}")
    
    async def get_station_by_id(self, station_id: str) -> Optional[MevoStation]:
        """
        Get information for a specific station.
        
        Args:
            station_id: The MEVO station ID to look up
            
        Returns:
            Optional[MevoStation]: Station information if found, None otherwise
        """
        try:
            stations = await self.get_station_information()
            
            for station in stations:
                if station.station_id == station_id:
                    return station
            
            logger.info(f"Station {station_id} not found in MEVO system")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get station {station_id}: {str(e)}")
            raise MevoApiError(f"Failed to get station {station_id}: {str(e)}")
    
    async def get_combined_station_data(self) -> List[Dict[str, Any]]:
        """
        Get combined station information and status.
        
        Returns:
            List[Dict]: Stations with both static info and current status
        """
        try:
            # Fetch both station info and status concurrently
            stations_task = asyncio.create_task(self.get_station_information())
            statuses_task = asyncio.create_task(self.get_station_status())
            
            stations, statuses = await asyncio.gather(stations_task, statuses_task)
            
            # Create lookup map for statuses
            status_map = {status.station_id: status for status in statuses}
            
            # Combine data
            combined_data = []
            for station in stations:
                station_dict = station.model_dump()
                
                # Add status if available
                if station.station_id in status_map:
                    status = status_map[station.station_id]
                    station_dict.update({
                        'num_bikes_available': status.num_bikes_available,
                        'num_docks_available': status.num_docks_available,
                        'is_installed': status.is_installed,
                        'is_renting': status.is_renting,
                        'is_returning': status.is_returning,
                        'last_reported': status.last_reported,
                        'last_reported_datetime': datetime.fromtimestamp(
                            status.last_reported, tz=timezone.utc
                        ).isoformat()
                    })
                else:
                    logger.warning(f"No status data for station {station.station_id}")
                    # Add default values
                    station_dict.update({
                        'num_bikes_available': 0,
                        'num_docks_available': 0,
                        'is_installed': False,
                        'is_renting': False,
                        'is_returning': False,
                        'last_reported': 0,
                        'last_reported_datetime': None
                    })
                
                combined_data.append(station_dict)
            
            logger.info(f"Combined data for {len(combined_data)} MEVO stations")
            return combined_data
            
        except Exception as e:
            logger.error(f"Failed to get combined station data: {str(e)}")
            raise MevoApiError(f"Failed to get combined station data: {str(e)}")


# Convenience function for creating client instances
async def create_mevo_client() -> MevoApiClient:
    """
    Create and return a MEVO API client.
    
    Returns:
        MevoApiClient: Configured client instance
        
    Example:
        async with create_mevo_client() as client:
            stations = await client.get_station_information()
    """
    return MevoApiClient()
