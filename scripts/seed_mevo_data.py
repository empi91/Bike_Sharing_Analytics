#!/usr/bin/env python3
"""
MEVO Data Seeding Script.

This script fetches station data from the MEVO GBFS API and seeds the database.
Run this script to initialize your database with real MEVO station data.

Usage:
    python scripts/seed_mevo_data.py
    
Environment Variables:
    All Supabase and API configuration should be set via .env file
"""

import asyncio
import sys
import os
from pathlib import Path
import logging
from datetime import datetime
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import db
from app.services.mevo_data_seeder import MevoDataSeeder
from app.services.mevo_api_client import MevoApiClient


def setup_logging():
    """Configure logging for the seeding script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"mevo_seed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        ]
    )


async def test_mevo_connection():
    """Test connection to MEVO API and display system information."""
    print("🔗 Testing MEVO API connection...")
    
    try:
        async with MevoApiClient() as client:
            # Get system information
            system_info = await client.get_system_information()
            
            print(f"✅ Connected to {system_info.name}")
            print(f"   System ID: {system_info.system_id}")
            print(f"   Operator: {system_info.operator}")
            print(f"   Timezone: {system_info.timezone}")
            print(f"   Language: {system_info.language}")
            print(f"   Contact: {system_info.email}")
            print()
            
            return True
            
    except Exception as e:
        print(f"❌ Failed to connect to MEVO API: {str(e)}")
        return False


async def fetch_and_display_station_sample():
    """Fetch and display a sample of MEVO stations."""
    print("📍 Fetching MEVO station data...")
    
    try:
        async with MevoApiClient() as client:
            # Get station information
            stations = await client.get_station_information()
            
            print(f"✅ Found {len(stations)} MEVO stations")
            print()
            
            # Display sample stations
            print("📋 Sample stations:")
            print("-" * 80)
            
            sample_stations = stations[:5]  # Show first 5 stations
            for i, station in enumerate(sample_stations, 1):
                print(f"{i}. {station.name} (ID: {station.station_id})")
                print(f"   📍 Location: {station.lat:.6f}, {station.lon:.6f}")
                print(f"   🏢 Address: {station.address}")
                print(f"   🚲 Capacity: {station.capacity} bikes")
                print(f"   📱 Virtual Station: {station.is_virtual_station}")
                print()
            
            if len(stations) > 5:
                print(f"... and {len(stations) - 5} more stations")
                print()
            
            # Group stations by area
            areas = {}
            for station in stations:
                if station.name.startswith('GDA'):
                    area = 'Gdańsk'
                elif station.name.startswith('GPG'):
                    area = 'Gdynia'
                elif station.name.startswith('SOP'):
                    area = 'Sopot'
                else:
                    area = 'Other'
                areas[area] = areas.get(area, 0) + 1
            
            print("🗺️ Stations by area:")
            for area, count in areas.items():
                print(f"   {area}: {count} stations")
            print()
            
            return stations
            
    except Exception as e:
        print(f"❌ Failed to fetch station data: {str(e)}")
        return []


async def fetch_and_display_status_sample():
    """Fetch and display current station status."""
    print("📊 Fetching current station status...")
    
    try:
        async with MevoApiClient() as client:
            # Get station status
            statuses = await client.get_station_status()
            
            print(f"✅ Retrieved status for {len(statuses)} stations")
            print()
            
            # Calculate statistics
            total_bikes = sum(status.num_bikes_available for status in statuses)
            total_docks = sum(status.num_docks_available for status in statuses)
            renting_stations = sum(1 for status in statuses if status.is_renting)
            returning_stations = sum(1 for status in statuses if status.is_returning)
            
            print("📈 System-wide statistics:")
            print(f"   🚲 Total available bikes: {total_bikes}")
            print(f"   🅿️ Total available docks: {total_docks}")
            print(f"   ✅ Stations accepting rentals: {renting_stations}/{len(statuses)}")
            print(f"   🔄 Stations accepting returns: {returning_stations}/{len(statuses)}")
            print()
            
            # Show sample station statuses
            print("📋 Sample station status:")
            print("-" * 60)
            
            sample_statuses = statuses[:5]
            for status in sample_statuses:
                last_reported = datetime.fromtimestamp(status.last_reported)
                print(f"Station {status.station_id}:")
                print(f"   🚲 Bikes: {status.num_bikes_available}")
                print(f"   🅿️ Docks: {status.num_docks_available}")
                print(f"   📅 Last updated: {last_reported.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   🔄 Renting: {'✅' if status.is_renting else '❌'} | Returning: {'✅' if status.is_returning else '❌'}")
                print()
            
            return statuses
            
    except Exception as e:
        print(f"❌ Failed to fetch station status: {str(e)}")
        return []


async def test_database_connection():
    """Test database connection."""
    print("🗄️ Testing database connection...")
    
    try:
        # Test basic connection
        result = await db.test_connection()
        
        if result:
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Database connection error: {str(e)}")
        return False


async def seed_database():
    """Seed the database with MEVO station data."""
    print("🌱 Starting database seeding...")
    
    try:
        seeder = MevoDataSeeder(db)
        
        # Perform initial seeding
        result = await seeder.seed_initial_stations()
        
        print("📊 Seeding Results:")
        print("-" * 50)
        print(f"🔍 Stations fetched: {result['stations_fetched']}")
        print(f"✅ Stations created: {result['stations_created']}")
        print(f"🔄 Stations updated: {result['stations_updated']}")
        print(f"⏭️ Stations skipped: {result['stations_skipped']}")
        print(f"⏱️ Duration: {result.get('duration_ms', 0)} ms")
        print(f"🎯 Success: {'✅' if result['success'] else '❌'}")
        
        if result['errors']:
            print(f"\n⚠️ Errors encountered:")
            for error in result['errors']:
                print(f"   • {error}")
        
        print()
        
        # Get and display summary
        summary = await seeder.get_seeding_summary()
        
        print("📈 Database Summary:")
        print("-" * 50)
        print(f"🏢 Total stations: {summary['total_stations']}")
        print(f"✅ Active stations: {summary['active_stations']}")
        print(f"❌ Inactive stations: {summary['inactive_stations']}")
        
        if summary['stations_by_area']:
            print("\n🗺️ Stations by area:")
            for area, count in summary['stations_by_area'].items():
                print(f"   {area}: {count} stations")
        
        if summary['recent_syncs']:
            print(f"\n🔄 Recent sync logs:")
            for sync in summary['recent_syncs'][:3]:  # Show last 3 syncs
                print(f"   {sync['timestamp']}: {sync['status']} ({sync['stations_updated']} stations)")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ Seeding failed: {str(e)}")
        return False


async def main():
    """Main script execution."""
    print("🚲 MEVO Data Seeding Script")
    print("=" * 50)
    print()
    
    # Test API connection
    api_ok = await test_mevo_connection()
    if not api_ok:
        print("❌ Cannot proceed without API connection")
        return 1
    
    # Test database connection
    db_ok = await test_database_connection()
    if not db_ok:
        print("❌ Cannot proceed without database connection")
        return 1
    
    print()
    
    # Fetch and display sample data
    stations = await fetch_and_display_station_sample()
    if not stations:
        print("❌ Cannot proceed without station data")
        return 1
    
    await fetch_and_display_status_sample()
    
    # Ask user if they want to proceed with seeding
    print("🤔 Do you want to proceed with database seeding? (y/N): ", end="")
    
    # For automated testing, we'll proceed automatically
    # In interactive mode, uncomment the next line:
    # response = input().strip().lower()
    response = "y"  # Auto-proceed for script testing
    
    if response not in ['y', 'yes']:
        print("⏹️ Seeding cancelled by user")
        return 0
    
    print()
    
    # Perform database seeding
    success = await seed_database()
    
    if success:
        print("\n🎉 MEVO data seeding completed successfully!")
        print("💡 You can now use the API endpoints to access station data")
        print("📚 Check /docs for API documentation")
        return 0
    else:
        print("\n❌ MEVO data seeding failed")
        print("🔍 Check the logs for detailed error information")
        return 1


if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    # Run the main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
