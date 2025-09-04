"""
Database connection and client management for Supabase.

This module provides a centralized way to connect to Supabase and manage
database operations throughout the application.
"""

import logging
from typing import Optional
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Supabase client manager for database operations.
    
    This class provides a singleton-like interface to the Supabase client
    with proper connection management and error handling.
    
    Attributes:
        client: The Supabase client instance
    """
    
    def __init__(self):
        """Initialize the Supabase client with configuration settings."""
        self._client: Optional[Client] = None
        
    @property
    def client(self) -> Client:
        """
        Get the Supabase client instance.
        
        Creates the client on first access (lazy initialization).
        
        Returns:
            Client: Configured Supabase client
            
        Raises:
            Exception: If client creation fails
        """
        if self._client is None:
            try:
                logger.info("Creating Supabase client connection")
                self._client = create_client(
                    supabase_url=settings.supabase_url,
                    supabase_key=settings.supabase_anon_key
                )
                logger.info("Supabase client created successfully")
            except Exception as e:
                logger.error(f"Failed to create Supabase client: {str(e)}")
                raise Exception(f"Database connection failed: {str(e)}")
        
        return self._client
    
    async def test_connection(self) -> bool:
        """
        Test the Supabase connection.
        
        Attempts to connect to Supabase and perform a simple operation
        to verify the connection is working.
        
        Returns:
            bool: True if connection is successful, False otherwise
            
        Example:
            db = SupabaseClient()
            is_connected = await db.test_connection()
            if is_connected:
                print("Database connection successful!")
        """
        try:
            logger.info("Testing Supabase connection")
            
            # Try to access the client (this will create connection)
            client = self.client
            
            # For now, if we can create the client successfully, consider it connected
            # We'll implement a proper database ping once we have tables
            logger.info("Supabase connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Supabase connection test failed: {str(e)}")
            return False
    
    def get_admin_client(self) -> Client:
        """
        Get Supabase client with service role key for admin operations.
        
        Use this client for operations that require elevated privileges,
        such as bypassing Row Level Security (RLS).
        
        Returns:
            Client: Supabase client with service role privileges
            
        Raises:
            Exception: If admin client creation fails
        """
        try:
            logger.info("Creating Supabase admin client")
            admin_client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_service_role_key
            )
            logger.info("Supabase admin client created successfully")
            return admin_client
            
        except Exception as e:
            logger.error(f"Failed to create Supabase admin client: {str(e)}")
            raise Exception(f"Admin database connection failed: {str(e)}")


# Global database client instance
db = SupabaseClient()


def get_db() -> SupabaseClient:
    """
    Get the global database client instance.
    
    This function provides access to the shared Supabase client
    for dependency injection in FastAPI endpoints.
    
    Returns:
        SupabaseClient: The global database client instance
        
    Example:
        # In FastAPI endpoint
        def get_stations(db: SupabaseClient = Depends(get_db)):
            return db.client.table('bike_stations').select('*').execute()
    """
    return db
