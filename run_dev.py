#!/usr/bin/env python3
"""
Development server runner for the Bike Station Reliability API.

This script runs the FastAPI application using uvicorn with development settings.
Use this during development for automatic reloading and debug features.

Usage:
    python run_dev.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
