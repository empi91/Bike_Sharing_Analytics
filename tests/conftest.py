"""
Test configuration and fixtures for unittest-based test suite.

This module provides shared test utilities, fixtures, and configuration
for the unittest test framework used throughout the project.
"""

import unittest
import os
import sys
from unittest.mock import AsyncMock, Mock
from typing import Any, Dict

# Add the app directory to the Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    """
    Base test case class for async test methods.
    
    Extends unittest.IsolatedAsyncioTestCase to provide async test support
    with proper setup and teardown for database connections and mocks.
    """
    
    async def asyncSetUp(self):
        """Set up async test fixtures before each test method."""
        pass
        
    async def asyncTearDown(self):
        """Clean up async test fixtures after each test method."""
        pass


class BaseTestCase(unittest.TestCase):
    """
    Base test case class for synchronous test methods.
    
    Provides common setup, teardown, and utility methods for all test cases.
    """
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        pass
        
    def tearDown(self):
        """Clean up test fixtures after each test method."""
        pass


def create_mock_supabase_client() -> Mock:
    """
    Create a mock Supabase client for testing.
    
    Returns:
        Mock: Configured mock Supabase client with common methods
    """
    mock_client = Mock()
    mock_client.table.return_value = Mock()
    mock_client.auth = Mock()
    return mock_client


def create_test_config() -> Dict[str, Any]:
    """
    Create test configuration settings.
    
    Returns:
        Dict[str, Any]: Test configuration dictionary
    """
    return {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test_key",
        "API_KEY": "test_api_key",
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "ENVIRONMENT": "test"
    }
