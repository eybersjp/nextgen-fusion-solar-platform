"""Test configuration and fixtures."""

import asyncio
import pytest
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_application
from app.core.database import get_db, Base
from app.core.config import get_settings
from app.models.user import User
from app.models.project import Project
from app.models.design import Design
from app.core.auth import AuthService
from app.schemas.user import UserCreate


# Test database URL
TEST_DATABASE_URL = "sqlite:///./test_nextgen_design.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session."""
    # Create test engine
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Drop tables
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app = create_application()
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
        "company": "Test Company",
        "role": "engineer"
    }


@pytest.fixture
def test_user(test_db, test_user_data):
    """Create a test user in the database."""
    auth_service = AuthService()
    
    # Create user
    user_create = UserCreate(**test_user_data)
    user = auth_service.create_user(test_db, user_create)
    
    # Verify email (for testing)
    user.is_verified = True
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers for test user."""
    auth_service = AuthService()
    access_token = auth_service.create_access_token(data={"sub": test_user.email})
    
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def test_project_data():
    """Test project data."""
    return {
        "name": "Test Solar Project",
        "description": "A test solar installation project",
        "location": {
            "address": "123 Test Street, Test City, TC 12345",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "timezone": "America/Los_Angeles"
        },
        "system_size_kw": 100.0,
        "project_type": "commercial",
        "status": "planning"
    }


@pytest.fixture
def test_project(test_db, test_user, test_project_data):
    """Create a test project in the database."""
    project = Project(
        **test_project_data,
        owner_id=test_user.id
    )
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)
    return project


@pytest.fixture
def test_design_data() -> dict:
    """Test solar design data."""
    return {
        "name": "Test Solar Design",
        "description": "A test solar design for unit testing",
        "system_capacity_kw": 100.0,
        "annual_energy_kwh": 150000.0,
        "system_type": "grid_tied",
        "design_stage": "concept"
    }


@pytest.fixture
def test_design(test_db, test_project, test_design_data, test_user):
    """Create a test solar design in the database."""
    design = Design(
        **test_design_data,
        project_id=test_project.id,
        organization_id=test_user.id,  # Using user ID as organization ID for testing
        created_by=test_user.id
    )
    test_db.add(design)
    test_db.commit()
    test_db.refresh(design)
    return design


@pytest.fixture
def admin_user(test_db):
    """Create an admin user for testing."""
    auth_service = AuthService()
    
    admin_data = {
        "email": "admin@example.com",
        "password": "adminpassword123",
        "full_name": "Admin User",
        "company": "NextGen Fusion",
        "role": "admin"
    }
    
    user_create = UserCreate(**admin_data)
    user = auth_service.create_user(test_db, user_create)
    
    # Set as admin and verify
    user.is_admin = True
    user.is_verified = True
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def admin_headers(admin_user):
    """Create authentication headers for admin user."""
    auth_service = AuthService()
    access_token = auth_service.create_access_token(data={"sub": admin_user.email})
    
    return {"Authorization": f"Bearer {access_token}"}