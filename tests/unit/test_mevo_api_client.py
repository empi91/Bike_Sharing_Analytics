"""
Unit tests for MEVO API client.

Tests the MevoApiClient functionality including successful requests,
error handling, and data parsing for the Gdańsk MEVO bike sharing system.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
import httpx
from datetime import datetime, timezone

from app.services.mevo_api_client import (
    MevoApiClient,
    MevoApiError,
    MevoSystemInfo,
    MevoStation,
    MevoStationStatus,
    create_mevo_client
)


class TestMevoApiClient:
    """Test cases for MevoApiClient."""
    
    @pytest_asyncio.async_test
    async def test_create_mevo_client(self):
        """Test client creation."""
        client = await create_mevo_client()
        assert isinstance(client, MevoApiClient)
    
    @pytest_asyncio.async_test
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with MevoApiClient() as client:
            assert client._session is not None
        # Session should be closed after exiting context
    
    @pytest_asyncio.async_test
    async def test_get_system_information_success(self):
        """Test successful system information retrieval."""
        mock_response = {
            "last_updated": 1757445615,
            "ttl": 15,
            "version": "2.3",
            "data": {
                "system_id": "inurba-gdansk",
                "language": "pl",
                "name": "MEVO",
                "operator": "Inurba",
                "timezone": "Europe/Warsaw",
                "phone_number": "+48587391123",
                "email": "kontakt@rowermevo.pl",
                "rental_apps": {
                    "android": {
                        "discovery_uri": "rowermevo://",
                        "store_uri": "https://play.google.com/store/apps/details?id=com.urbansharing.citybike.gdansk"
                    },
                    "ios": {
                        "discovery_uri": "rowermevo://",
                        "store_uri": "https://apps.apple.com/pl/app/rowermevo/id6452801246"
                    }
                }
            }
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_get.return_value = mock_response_obj
            
            async with MevoApiClient() as client:
                system_info = await client.get_system_information()
                
                assert isinstance(system_info, MevoSystemInfo)
                assert system_info.system_id == "inurba-gdansk"
                assert system_info.name == "MEVO"
                assert system_info.operator == "Inurba"
                assert system_info.timezone == "Europe/Warsaw"
                assert system_info.email == "kontakt@rowermevo.pl"
    
    @pytest_asyncio.async_test
    async def test_get_station_information_success(self):
        """Test successful station information retrieval."""
        mock_response = {
            "last_updated": 1757445615,
            "ttl": 15,
            "version": "2.3",
            "data": {
                "stations": [
                    {
                        "station_id": "5811",
                        "name": "GDA398",
                        "address": "Aleja Generała Józefa Hallera 201",
                        "cross_street": "Aleja Generała Józefa Hallera 201",
                        "lat": 54.39641221825073,
                        "lon": 18.62255276998812,
                        "is_virtual_station": True,
                        "capacity": 10,
                        "station_area": {
                            "type": "MultiPolygon",
                            "coordinates": [[[[18.62258501367978, 54.39645628596841]]]]
                        },
                        "rental_uris": {
                            "android": "rowermevo://stations/5811",
                            "ios": "rowermevo://stations/5811"
                        }
                    }
                ]
            }
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_get.return_value = mock_response_obj
            
            async with MevoApiClient() as client:
                stations = await client.get_station_information()
                
                assert len(stations) == 1
                station = stations[0]
                assert isinstance(station, MevoStation)
                assert station.station_id == "5811"
                assert station.name == "GDA398"
                assert station.is_virtual_station is True
                assert station.capacity == 10
                assert station.lat == 54.39641221825073
                assert station.lon == 18.62255276998812
    
    @pytest_asyncio.async_test
    async def test_get_station_status_success(self):
        """Test successful station status retrieval."""
        mock_response = {
            "last_updated": 1757445615,
            "ttl": 15,
            "version": "2.3",
            "data": {
                "stations": [
                    {
                        "station_id": "5811",
                        "num_bikes_available": 3,
                        "num_docks_available": 7,
                        "is_installed": True,
                        "is_renting": True,
                        "is_returning": True,
                        "last_reported": 1757445600
                    }
                ]
            }
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_get.return_value = mock_response_obj
            
            async with MevoApiClient() as client:
                statuses = await client.get_station_status()
                
                assert len(statuses) == 1
                status = statuses[0]
                assert isinstance(status, MevoStationStatus)
                assert status.station_id == "5811"
                assert status.num_bikes_available == 3
                assert status.num_docks_available == 7
                assert status.is_installed is True
                assert status.is_renting is True
                assert status.is_returning is True
                assert status.last_reported == 1757445600
    
    @pytest_asyncio.async_test
    async def test_get_station_by_id_found(self):
        """Test finding a station by ID."""
        mock_response = {
            "data": {
                "stations": [
                    {
                        "station_id": "5811",
                        "name": "GDA398",
                        "address": "Test Address",
                        "cross_street": "Test Street",
                        "lat": 54.39641221825073,
                        "lon": 18.62255276998812,
                        "is_virtual_station": True,
                        "capacity": 10,
                        "rental_uris": {"android": "test://", "ios": "test://"}
                    }
                ]
            }
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_get.return_value = mock_response_obj
            
            async with MevoApiClient() as client:
                station = await client.get_station_by_id("5811")
                
                assert station is not None
                assert station.station_id == "5811"
                assert station.name == "GDA398"
    
    @pytest_asyncio.async_test
    async def test_get_station_by_id_not_found(self):
        """Test station not found by ID."""
        mock_response = {
            "data": {
                "stations": [
                    {
                        "station_id": "5811",
                        "name": "GDA398",
                        "address": "Test Address",
                        "cross_street": "Test Street",
                        "lat": 54.39641221825073,
                        "lon": 18.62255276998812,
                        "is_virtual_station": True,
                        "capacity": 10,
                        "rental_uris": {"android": "test://", "ios": "test://"}
                    }
                ]
            }
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_get.return_value = mock_response_obj
            
            async with MevoApiClient() as client:
                station = await client.get_station_by_id("nonexistent")
                
                assert station is None
    
    @pytest_asyncio.async_test
    async def test_http_error_handling(self):
        """Test HTTP error handling."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = AsyncMock()
            mock_response_obj.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=AsyncMock(), response=AsyncMock(status_code=404)
            )
            mock_get.return_value = mock_response_obj
            
            async with MevoApiClient() as client:
                with pytest.raises(MevoApiError, match="HTTP 404 error from MEVO API"):
                    await client.get_system_information()
    
    @pytest_asyncio.async_test
    async def test_request_error_handling(self):
        """Test network request error handling."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection failed")
            
            async with MevoApiClient() as client:
                with pytest.raises(MevoApiError, match="Network error connecting to MEVO API"):
                    await client.get_system_information()
    
    @pytest_asyncio.async_test
    async def test_invalid_gbfs_response(self):
        """Test handling of invalid GBFS response structure."""
        mock_response = {"invalid": "structure"}  # Missing 'data' key
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_get.return_value = mock_response_obj
            
            async with MevoApiClient() as client:
                with pytest.raises(MevoApiError, match="Invalid GBFS response structure"):
                    await client.get_system_information()
    
    @pytest_asyncio.async_test
    async def test_session_not_initialized(self):
        """Test error when session is not initialized."""
        client = MevoApiClient()
        
        with pytest.raises(MevoApiError, match="Client session not initialized"):
            await client.get_system_information()
    
    @pytest_asyncio.async_test
    async def test_get_combined_station_data(self):
        """Test combined station data retrieval."""
        station_mock_response = {
            "data": {
                "stations": [
                    {
                        "station_id": "5811",
                        "name": "GDA398",
                        "address": "Test Address",
                        "cross_street": "Test Street",
                        "lat": 54.39641221825073,
                        "lon": 18.62255276998812,
                        "is_virtual_station": True,
                        "capacity": 10,
                        "rental_uris": {"android": "test://", "ios": "test://"}
                    }
                ]
            }
        }
        
        status_mock_response = {
            "data": {
                "stations": [
                    {
                        "station_id": "5811",
                        "num_bikes_available": 3,
                        "num_docks_available": 7,
                        "is_installed": True,
                        "is_renting": True,
                        "is_returning": True,
                        "last_reported": 1757445600
                    }
                ]
            }
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            def side_effect(url):
                mock_response_obj = AsyncMock()
                mock_response_obj.raise_for_status.return_value = None
                
                if 'station_information' in url:
                    mock_response_obj.json.return_value = station_mock_response
                elif 'station_status' in url:
                    mock_response_obj.json.return_value = status_mock_response
                    
                return mock_response_obj
            
            mock_get.side_effect = side_effect
            
            async with MevoApiClient() as client:
                combined_data = await client.get_combined_station_data()
                
                assert len(combined_data) == 1
                station_data = combined_data[0]
                
                # Check station info fields
                assert station_data['station_id'] == "5811"
                assert station_data['name'] == "GDA398"
                assert station_data['lat'] == 54.39641221825073
                
                # Check status fields
                assert station_data['num_bikes_available'] == 3
                assert station_data['num_docks_available'] == 7
                assert station_data['is_installed'] is True
                assert station_data['last_reported'] == 1757445600
                assert 'last_reported_datetime' in station_data
