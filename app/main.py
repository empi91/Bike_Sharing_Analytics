"""
Main FastAPI application for Bike Station Reliability Lookup.

This module creates and configures the FastAPI application instance,
sets up middleware, includes routers, and defines the application lifecycle.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import db


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the FastAPI application.
    This is where we can initialize connections, start background tasks, etc.
    
    Args:
        app: FastAPI application instance
        
    Yields:
        None: Control back to FastAPI during application runtime
    """
    # Startup
    logger.info("Starting Bike Station Reliability API")
    logger.info(f"Environment: {settings.environment}")
    
    # Test database connection on startup
    try:
        connection_test = await db.test_connection()
        if connection_test:
            logger.info("Database connection verified successfully")
        else:
            logger.warning("Database connection test failed")
    except Exception as e:
        logger.error(f"Database connection error during startup: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Bike Station Reliability API")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    This function creates the FastAPI app instance with all necessary
    configuration including middleware, exception handlers, and metadata.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Bike Station Reliability API",
        description="API for tracking and analyzing bike sharing station reliability based on historical availability data",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add exception handler for better error responses
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Handle unexpected exceptions with proper logging."""
        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )
    
    return app


# Create the FastAPI application instance
app = create_application()


@app.get("/api/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the current status of the API and its dependencies.
    This endpoint is used for monitoring and ensuring the service is running properly.
    
    Returns:
        dict: Health status information including API status and database connectivity
        
    Example:
        GET /api/health
        {
            "status": "healthy",
            "message": "Bike Station Reliability API is running",
            "version": "1.0.0",
            "environment": "development",
            "database": "connected",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    """
    from datetime import datetime
    
    # Test database connection
    database_status = "connected"
    try:
        connection_test = await db.test_connection()
        if not connection_test:
            database_status = "disconnected"
    except Exception as e:
        logger.error(f"Health check database test failed: {str(e)}")
        database_status = "error"
    
    # If database is not connected, return 503 Service Unavailable
    if database_status != "connected":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "message": "Database connection failed",
                "database": database_status,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )
    
    return {
        "status": "healthy",
        "message": "Bike Station Reliability API is running",
        "version": "1.0.0",
        "environment": settings.environment,
        "database": database_status,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint with basic API information.
    
    Returns:
        dict: Basic API information and links to documentation
    """
    return {
        "message": "Bike Station Reliability API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }
