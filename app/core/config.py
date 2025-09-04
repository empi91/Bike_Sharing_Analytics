"""
Application configuration management.

This module handles loading and validating configuration from environment variables
using Pydantic Settings. It provides type-safe configuration access throughout the application.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    This class uses Pydantic Settings to automatically load configuration
    from environment variables with type validation and default values.
    
    Attributes:
        supabase_url: Supabase project URL
        supabase_anon_key: Supabase anonymous (public) API key
        supabase_service_role_key: Supabase service role (private) API key
        environment: Application environment (development, production, test)
        api_key: Internal API key for protected endpoints
        log_level: Logging level
        city_bike_api_url: External city bike API URL
        api_request_timeout: Timeout for external API requests in seconds
        sync_interval_minutes: Background sync interval in minutes
        reliability_calculation_hour: Hour of day to calculate reliability scores
    """
    
    # Supabase Configuration
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anonymous API key")
    supabase_service_role_key: str = Field(..., description="Supabase service role API key")
    
    # Application Configuration
    environment: str = Field(default="development", description="Application environment")
    api_key: str = Field(..., description="Internal API key for protected endpoints")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # External API Configuration
    city_bike_api_url: str = Field(
        default="https://gbfs.citibikenyc.com/gbfs/gbfs.json",
        description="City bike API URL"
    )
    api_request_timeout: int = Field(default=30, description="API request timeout in seconds")
    
    # Background Task Configuration
    sync_interval_minutes: int = Field(default=5, description="Sync interval in minutes")
    reliability_calculation_hour: int = Field(
        default=2, 
        description="Hour of day to calculate reliability scores (0-23)"
    )
    
    class Config:
        """Pydantic configuration for Settings class."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """
    Get application settings instance.
    
    This function creates and returns a Settings instance with all
    configuration loaded from environment variables.
    
    Returns:
        Settings: Configured settings instance
        
    Raises:
        ValidationError: If required environment variables are missing or invalid
        
    Example:
        settings = get_settings()
        print(f"Environment: {settings.environment}")
    """
    return Settings()


# Global settings instance
settings = get_settings()
