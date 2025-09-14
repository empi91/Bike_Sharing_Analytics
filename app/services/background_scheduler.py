"""
Background Task Scheduler for MEVO Data Collection.

This module manages automated data collection and processing tasks using APScheduler.
It handles station status collection, reliability calculation, and data maintenance.
"""

import logging
import asyncio
from typing import Optional
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import db
from app.services.mevo_data_seeder import MevoDataSeeder

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """
    Background task scheduler for automated MEVO data operations.
    
    This class manages all background tasks including:
    - Station status collection every 5 minutes
    - Daily reliability score calculation
    - Data maintenance and cleanup
    """
    
    def __init__(self):
        """Initialize the background scheduler."""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.seeder = MevoDataSeeder(db)
        self.is_running = False
    
    async def start(self) -> None:
        """
        Start the background scheduler with all configured tasks.
        
        This method sets up and starts all background tasks according to
        the configuration in settings.
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("Starting background task scheduler")
        
        # Create scheduler
        self.scheduler = AsyncIOScheduler()
        
        # Add data collection task (every 5 minutes)
        self.scheduler.add_job(
            func=self._collect_station_status,
            trigger=IntervalTrigger(minutes=settings.sync_interval_minutes),
            id='station_status_collection',
            name='Collect Station Status Data',
            max_instances=1,  # Prevent overlapping executions
            replace_existing=True
        )
        
        # Note: Hourly averages are now calculated immediately after each data collection
        # No separate daily task needed - averages are updated every 5 minutes with new data
        
        # Add data maintenance task (weekly on Sunday at 3 AM)
        self.scheduler.add_job(
            func=self._perform_data_maintenance,
            trigger=CronTrigger(day_of_week='sun', hour=3, minute=0),
            id='data_maintenance',
            name='Weekly Data Maintenance',
            max_instances=1,
            replace_existing=True
        )
        
        # Start the scheduler
        self.scheduler.start()
        self.is_running = True
        
        logger.info("Background scheduler started successfully")
        logger.info(f"Data collection interval: {settings.sync_interval_minutes} minutes")
        logger.info("Hourly averages: Calculated immediately after each data collection")
        
        # Log next execution times
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time
            logger.info(f"Next '{job.name}' execution: {next_run}")
    
    async def stop(self) -> None:
        """
        Stop the background scheduler gracefully.
        
        This method stops all running tasks and shuts down the scheduler.
        """
        if not self.is_running or not self.scheduler:
            logger.warning("Scheduler is not running")
            return
        
        logger.info("Stopping background task scheduler")
        
        self.scheduler.shutdown(wait=True)
        self.scheduler = None
        self.is_running = False
        
        logger.info("Background scheduler stopped")
    
    async def get_status(self) -> dict:
        """
        Get current status of the background scheduler.
        
        Returns:
            dict: Scheduler status and job information
        """
        if not self.is_running or not self.scheduler:
            return {
                'running': False,
                'jobs': [],
                'next_executions': {}
            }
        
        jobs_info = []
        next_executions = {}
        
        for job in self.scheduler.get_jobs():
            job_info = {
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            }
            jobs_info.append(job_info)
            next_executions[job.id] = job.next_run_time.isoformat() if job.next_run_time else None
        
        return {
            'running': True,
            'jobs': jobs_info,
            'next_executions': next_executions,
            'scheduler_state': str(self.scheduler.state)
        }
    
    async def trigger_job(self, job_id: str) -> dict:
        """
        Manually trigger a specific job.
        
        Args:
            job_id: ID of the job to trigger
            
        Returns:
            dict: Execution result
        """
        if not self.is_running or not self.scheduler:
            raise Exception("Scheduler is not running")
        
        job = self.scheduler.get_job(job_id)
        if not job:
            raise Exception(f"Job with ID '{job_id}' not found")
        
        logger.info(f"Manually triggering job: {job.name}")
        
        try:
            # Execute the job function directly
            if job_id == 'station_status_collection':
                result = await self._collect_station_status()
            elif job_id == 'reliability_calculation':
                result = await self._calculate_reliability_scores()
            elif job_id == 'data_maintenance':
                result = await self._perform_data_maintenance()
            else:
                raise Exception(f"Unknown job ID: {job_id}")
            
            return {
                'success': True,
                'job_id': job_id,
                'job_name': job.name,
                'execution_time': datetime.utcnow().isoformat(),
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Manual job execution failed for {job_id}: {str(e)}")
            return {
                'success': False,
                'job_id': job_id,
                'job_name': job.name,
                'execution_time': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    # =====================================================
    # BACKGROUND TASK IMPLEMENTATIONS
    # =====================================================
    
    async def _collect_station_status(self) -> dict:
        """
        Collect current station status and create availability snapshots.
        
        This task runs every 5 minutes to collect real-time availability data
        from all MEVO stations.
        
        Returns:
            dict: Collection results
        """
        try:
            logger.info("Starting scheduled station status collection")
            
            result = await self.seeder.sync_station_status()
            
            if result['success']:
                logger.info(f"Status collection completed: {result['snapshots_created']} snapshots created")
                
                # Schedule hourly averages update in background (non-blocking)
                asyncio.create_task(self._update_hourly_averages_async())
            else:
                logger.error(f"Status collection had errors: {result['errors']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Station status collection failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'snapshots_created': 0
            }
    
    async def _update_hourly_averages_async(self) -> None:
        """
        Update hourly averages in background without blocking main operations.
        
        This runs as a separate asyncio task and doesn't block the main scheduler.
        """
        try:
            logger.info("Starting background hourly averages update")
            
            from app.repositories.station_repository import StationRepository
            repo = StationRepository(db)
            
            # Get all active stations
            stations = await repo.get_all_stations(active_only=True)
            
            # Process stations in smaller batches to avoid timeouts
            batch_size = 10  # Process 10 stations at a time
            total_batches = (len(stations) + batch_size - 1) // batch_size
            
            averages_updated = 0
            errors = []
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(stations))
                batch_stations = stations[start_idx:end_idx]
                
                logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch_stations)} stations)")
                
                # Process batch concurrently
                batch_tasks = []
                for station in batch_stations:
                    task = self._update_station_averages(repo, station)
                    batch_tasks.append(task)
                
                # Wait for batch to complete
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        error_msg = f"Error updating averages for station {batch_stations[i].id}: {str(result)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                    else:
                        averages_updated += result.get('averages_calculated', 0)
                
                # Small delay between batches to prevent overwhelming the database
                if batch_num < total_batches - 1:
                    await asyncio.sleep(1)
            
            logger.info(f"Background hourly averages update completed: {averages_updated} averages updated across {len(stations)} stations")
            
        except Exception as e:
            logger.error(f"Background hourly averages update failed: {str(e)}")
    
    async def _update_station_averages(self, repo, station) -> dict:
        """
        Update averages for a single station.
        
        Args:
            repo: Station repository instance
            station: Station to update
            
        Returns:
            dict: Update result
        """
        try:
            result = await repo.calculate_hourly_averages(station.id)
            return result
        except Exception as e:
            logger.error(f"Error updating averages for station {station.id}: {str(e)}")
            raise
    
    async def _update_hourly_averages(self) -> dict:
        """
        Update hourly availability averages for all stations.
        
        This task runs immediately after each availability data collection to keep
        the hourly averages up to date using ALL historical data.
        
        Returns:
            dict: Update results
        """
        try:
            logger.info("Starting hourly averages update (using ALL historical data)")
            
            from app.repositories.station_repository import StationRepository
            repo = StationRepository(db)
            
            # Get all active stations
            stations = await repo.get_all_stations(active_only=True)
            
            averages_updated = 0
            errors = []
            
            # Update averages for each station using ALL historical data
            for station in stations:
                try:
                    result = await repo.calculate_hourly_averages(station.id)
                    averages_updated += result.get('averages_calculated', 0)
                    logger.debug(f"Updated {result.get('averages_calculated', 0)} averages for station {station.name} using {result.get('total_snapshots', 0)} total snapshots")
                except Exception as e:
                    error_msg = f"Error updating averages for station {station.id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            result = {
                'success': len(errors) == 0,
                'averages_updated': averages_updated,
                'stations_processed': len(stations),
                'errors': errors
            }
            
            if result['success']:
                logger.info(f"Hourly averages update completed: {averages_updated} averages updated across {len(stations)} stations")
            else:
                logger.error(f"Hourly averages update had errors: {errors}")
            
            return result
            
        except Exception as e:
            logger.error(f"Hourly averages update failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'averages_updated': 0
            }
    
    async def _perform_data_maintenance(self) -> dict:
        """
        Perform weekly data maintenance tasks.
        
        This includes cleaning up old data, optimizing database performance,
        and other maintenance operations.
        
        Returns:
            dict: Maintenance results
        """
        try:
            logger.info("Starting scheduled data maintenance")
            
            # TODO: Implement data maintenance tasks
            # - Clean up old availability snapshots (keep last 90 days)
            # - Update station activity status
            # - Cleanup old sync logs
            # - Database optimization
            
            maintenance_tasks = []
            
            # For now, just log that maintenance would run
            logger.info("Data maintenance completed (placeholder)")
            
            return {
                'success': True,
                'tasks_completed': maintenance_tasks,
                'message': 'Data maintenance completed successfully'
            }
            
        except Exception as e:
            logger.error(f"Data maintenance failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'tasks_completed': []
            }


# Global scheduler instance
scheduler_instance = BackgroundScheduler()


async def start_background_tasks() -> None:
    """
    Start the global background task scheduler.
    
    This function should be called during application startup.
    """
    await scheduler_instance.start()


async def stop_background_tasks() -> None:
    """
    Stop the global background task scheduler.
    
    This function should be called during application shutdown.
    """
    await scheduler_instance.stop()


def get_scheduler() -> BackgroundScheduler:
    """
    Get the global scheduler instance.
    
    Returns:
        BackgroundScheduler: Global scheduler instance
    """
    return scheduler_instance

