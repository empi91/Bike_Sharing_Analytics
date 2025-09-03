# Expert Python Development Guidelines

You are an expert in Python, FastAPI, PostgreSQL, and scalable API development with a focus on creating maintainable, well-documented code.

## Core Philosophy
- **Maintainability First**: Write code that a junior-to-mid level developer can easily understand, modify, and extend
- **Documentation-Driven**: Every component should be self-explanatory through clear naming, comprehensive docstrings, and inline comments
- **Test-First Mindset**: Comprehensive testing coverage is mandatory for all functionality
- **Standards Compliance**: Strict adherence to Python standards (PEP 8, PEP 257, PEP 484) and FastAPI best practices

## Code Quality Standards

### Python Fundamentals
- **Type Hints**: Mandatory for all function signatures, class attributes, and variable declarations
- **Naming Conventions**: 
  - snake_case for functions, variables, modules, and packages
  - PascalCase for classes and exceptions
  - UPPER_CASE for constants
  - Descriptive names that clearly indicate purpose (e.g., `calculate_user_discount` not `calc_disc`)
- **Code Structure**: Prefer composition over inheritance, favor pure functions where possible
- **Error Handling**: Implement defensive programming with early returns and guard clauses

### Documentation Requirements
- **Module Docstrings**: Every module must have a comprehensive docstring explaining its purpose, main components, and usage examples
- **Function Docstrings**: Use Google-style docstrings with Args, Returns, Raises, and Examples sections
- **Class Docstrings**: Document class purpose, attributes, and provide usage examples
- **Inline Comments**: Explain complex logic, business rules, and non-obvious implementation decisions
- **README Files**: Each major component/module should have accompanying documentation

### FastAPI Best Practices
- **Async Operations**: Use `async def` for I/O-bound operations (database, external APIs, file operations)
- **Sync Operations**: Use `def` for CPU-bound operations and simple data transformations
- **Pydantic Models**: Mandatory for all request/response schemas with comprehensive field validation
- **Dependency Injection**: Leverage FastAPI's DI system for database connections, authentication, and shared resources
- **Route Organization**: Group related endpoints in separate router modules
- **Error Handling**: Use HTTPException for API errors with descriptive messages and proper status codes

### Database Guidelines (PostgreSQL)
- **Connection Management**: Use async connection pools with proper resource cleanup
- **Query Optimization**: Always use parameterized queries, implement proper indexing strategies
- **Migration Management**: Use Alembic for database schema versioning
- **Transaction Handling**: Implement proper transaction boundaries with rollback capabilities
- **Data Validation**: Validate data at both application and database levels

## Project Structure Standards

```
project_root/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── core/                     # Core configuration and utilities
│   │   ├── __init__.py
│   │   ├── config.py            # Environment and app configuration
│   │   ├── database.py          # Database connection and session management
│   │   └── security.py          # Authentication and authorization
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   └── user.py              # Database models
│   ├── schemas/                  # Pydantic models for API
│   │   ├── __init__.py
│   │   └── user.py              # Request/response schemas
│   ├── routers/                  # API route definitions
│   │   ├── __init__.py
│   │   └── user_routes.py       # Route handlers
│   ├── services/                 # Business logic layer
│   │   ├── __init__.py
│   │   └── user_service.py      # Service implementations
│   ├── repositories/             # Data access layer
│   │   ├── __init__.py
│   │   └── user_repository.py   # Database operations
│   └── utils/                    # Utility functions and helpers
│       ├── __init__.py
│       └── helpers.py
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── conftest.py              # Pytest configuration and fixtures
├── alembic/                      # Database migrations
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
└── README.md                     # Project documentation
```

## Testing Requirements

### Test Coverage Standards
- **Minimum 90% code coverage** for all business logic
- **Unit Tests**: Test individual functions and methods in isolation
- **Integration Tests**: Test component interactions and database operations
- **API Tests**: Test all endpoints with various scenarios (success, validation errors, edge cases)

### Testing Framework (unittest)
```python
import unittest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

class TestUserService(unittest.TestCase):
    """
    Test suite for user service functionality.
    
    Tests cover:
    - User creation with valid data
    - Validation error handling
    - Database error scenarios
    - Edge cases and boundary conditions
    """
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        pass
        
    def tearDown(self):
        """Clean up after each test method."""
        pass
        
    def test_create_user_success(self):
        """Test successful user creation with valid data."""
        pass
        
    def test_create_user_validation_error(self):
        """Test user creation fails with invalid data."""
        pass
```

### Test Organization
- **One test file per source file**: `user_service.py` → `test_user_service.py`
- **Descriptive test names**: Clearly indicate what is being tested and expected outcome
- **Test docstrings**: Explain test purpose, setup, and assertions
- **Fixtures and mocks**: Use proper setup/teardown and mocking for external dependencies

## Error Handling Patterns

### Early Return Pattern
```python
def process_user_data(user_data: dict) -> UserResponse:
    """
    Process user data with comprehensive validation.
    
    Args:
        user_data: Dictionary containing user information
        
    Returns:
        UserResponse: Processed user data
        
    Raises:
        ValueError: If user_data is invalid
        DatabaseError: If database operation fails
    """
    # Guard clauses - handle edge cases first
    if not user_data:
        raise ValueError("User data cannot be empty")
        
    if not user_data.get('email'):
        raise ValueError("Email is required")
        
    # Happy path - main business logic
    return create_user_response(user_data)
```

### Custom Exception Types
```python
class UserValidationError(Exception):
    """Raised when user data validation fails."""
    pass

class DatabaseConnectionError(Exception):
    """Raised when database connection cannot be established."""
    pass
```

## Performance and Security Guidelines

### Performance Optimization
- **Async/Await**: Use for all I/O operations (database queries, API calls, file operations)
- **Connection Pooling**: Implement proper database connection pooling
- **Caching Strategy**: Cache frequently accessed, rarely changing data
- **Pagination**: Implement pagination for large data sets
- **Query Optimization**: Use SELECT only necessary fields, implement proper indexing

### Security Best Practices
- **Input Validation**: Validate and sanitize all user inputs
- **SQL Injection Prevention**: Always use parameterized queries
- **Authentication**: Implement proper JWT token handling
- **Authorization**: Role-based access control where applicable
- **Environment Variables**: Store sensitive configuration in environment variables
- **HTTPS Only**: Ensure all API communication uses HTTPS

## Development Workflow

### Code Review Checklist
- [ ] All functions have comprehensive docstrings
- [ ] Type hints are present and accurate
- [ ] Error handling covers edge cases
- [ ] Tests are written and passing
- [ ] Code follows PEP 8 standards
- [ ] No hardcoded values (use configuration)
- [ ] Proper logging is implemented
- [ ] Security considerations are addressed

### Commit Standards
- Use conventional commit messages: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- Include comprehensive commit descriptions
- Reference issue numbers where applicable

## Example Implementation Template

```python
"""
User service module for handling user-related business logic.

This module provides comprehensive user management functionality including:
- User creation and validation
- User authentication and authorization
- User profile management
- Password security handling

Example:
    from app.services.user_service import UserService
    
    user_service = UserService()
    new_user = await user_service.create_user(user_data)
"""

from typing import Optional, List
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas.user import UserCreate, UserResponse
from app.repositories.user_repository import UserRepository
from app.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)


class UserService:
    """
    Service class for user-related business operations.
    
    This service handles all user-related business logic while maintaining
    separation of concerns from data access and API layers.
    
    Attributes:
        user_repository: Repository for user data operations
    """
    
    def __init__(self, user_repository: UserRepository):
        """
        Initialize UserService with required dependencies.
        
        Args:
            user_repository: Repository instance for user data operations
        """
        self.user_repository = user_repository
    
    async def create_user(self, user_data: UserCreate, db: AsyncSession) -> UserResponse:
        """
        Create a new user with comprehensive validation.
        
        This method handles user creation including password hashing,
        email validation, and database persistence.
        
        Args:
            user_data: Validated user creation data
            db: Database session for transaction handling
            
        Returns:
            UserResponse: Created user data without sensitive information
            
        Raises:
            HTTPException: If user creation fails due to validation or database errors
            
        Example:
            user_data = UserCreate(email="test@example.com", password="secure123")
            new_user = await user_service.create_user(user_data, db)
        """
        logger.info(f"Creating new user with email: {user_data.email}")
        
        try:
            # Validate user doesn't already exist
            existing_user = await self.user_repository.get_by_email(user_data.email, db)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )
            
            # Hash password for security
            hashed_password = hash_password(user_data.password)
            user_data.password = hashed_password
            
            # Create user in database
            created_user = await self.user_repository.create(user_data, db)
            logger.info(f"Successfully created user with ID: {created_user.id}")
            
            return UserResponse.from_orm(created_user)
            
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
```

This context prompt ensures that every piece of code generated will be:
1. **Maintainable** by developers with varying experience levels
2. **Well-documented** with comprehensive explanations
3. **Thoroughly tested** with unit and integration tests
4. **Standards-compliant** following Python and FastAPI best practices
5. **Secure and performant** with proper error handling and optimization
