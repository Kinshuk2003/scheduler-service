"""
Unit tests for the API endpoints.

This module tests the API functionality following SOLID principles:
- Single Responsibility: Each test has a single responsibility
- Open/Closed: Easy to extend with new test cases
- Liskov Substitution: Consistent test interface
- Interface Segregation: Separate test concerns
- Dependency Inversion: Depends on abstractions for testing
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from src.app.main import app
from src.app.db import get_async_db, Base
from src.app.models import Job, JobRun
from src.app.schemas import JobCreate, JobUpdate


# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True
)

# Create test session
TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_async_db():
    """Override database dependency for testing."""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Override the database dependency
app.dependency_overrides[get_async_db] = override_get_async_db


@pytest.fixture(scope="function")
async def setup_test_db():
    """Set up test database for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def test_client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_job_data():
    """Sample job data for testing."""
    return {
        "name": "Test Job",
        "schedule_expr": "*/5 * * * *",
        "timezone": "UTC",
        "payload": {
            "type": "test",
            "message": "Hello World"
        },
        "retry_policy": {
            "max_retries": 3,
            "retry_delay": 60
        },
        "owner_id": "test_user"
    }


@pytest.fixture
def sample_job_update_data():
    """Sample job update data for testing."""
    return {
        "name": "Updated Test Job",
        "status": "paused",
        "payload": {
            "type": "test",
            "message": "Updated Hello World"
        }
    }


class TestJobAPI:
    """Test class for job API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_job_success(self, test_client, setup_test_db, sample_job_data):
        """Test successful job creation."""
        response = test_client.post(
            "/api/v1/jobs",
            json=sample_job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_job_data["name"]
        assert data["schedule_expr"] == sample_job_data["schedule_expr"]
        assert data["status"] == "active"
        assert "id" in data
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_create_job_invalid_schedule(self, test_client, setup_test_db):
        """Test job creation with invalid schedule."""
        invalid_job_data = {
            "name": "Invalid Job",
            "schedule_expr": "invalid schedule",
            "timezone": "UTC",
            "payload": {"type": "test"}
        }
        
        response = test_client.post(
            "/api/v1/jobs",
            json=invalid_job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_create_job_missing_api_key(self, test_client, setup_test_db, sample_job_data):
        """Test job creation without API key."""
        response = test_client.post(
            "/api/v1/jobs",
            json=sample_job_data
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_list_jobs_empty(self, test_client, setup_test_db):
        """Test listing jobs when none exist."""
        response = test_client.get(
            "/api/v1/jobs",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["jobs"] == []
        assert data["page"] == 1
        assert data["size"] == 10
    
    @pytest.mark.asyncio
    async def test_list_jobs_with_data(self, test_client, setup_test_db, sample_job_data):
        """Test listing jobs with existing data."""
        # Create a job first
        create_response = test_client.post(
            "/api/v1/jobs",
            json=sample_job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        assert create_response.status_code == 201
        
        # List jobs
        response = test_client.get(
            "/api/v1/jobs",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["name"] == sample_job_data["name"]
    
    @pytest.mark.asyncio
    async def test_get_job_success(self, test_client, setup_test_db, sample_job_data):
        """Test getting a specific job."""
        # Create a job first
        create_response = test_client.post(
            "/api/v1/jobs",
            json=sample_job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        job_id = create_response.json()["id"]
        
        # Get the job
        response = test_client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["name"] == sample_job_data["name"]
    
    @pytest.mark.asyncio
    async def test_get_job_not_found(self, test_client, setup_test_db):
        """Test getting a non-existent job."""
        response = test_client.get(
            "/api/v1/jobs/999",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_job_success(self, test_client, setup_test_db, sample_job_data, sample_job_update_data):
        """Test updating a job."""
        # Create a job first
        create_response = test_client.post(
            "/api/v1/jobs",
            json=sample_job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        job_id = create_response.json()["id"]
        
        # Update the job
        response = test_client.put(
            f"/api/v1/jobs/{job_id}",
            json=sample_job_update_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_job_update_data["name"]
        assert data["status"] == sample_job_update_data["status"]
    
    @pytest.mark.asyncio
    async def test_update_job_not_found(self, test_client, setup_test_db, sample_job_update_data):
        """Test updating a non-existent job."""
        response = test_client.put(
            "/api/v1/jobs/999",
            json=sample_job_update_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_job_success(self, test_client, setup_test_db, sample_job_data):
        """Test deleting a job."""
        # Create a job first
        create_response = test_client.post(
            "/api/v1/jobs",
            json=sample_job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        job_id = create_response.json()["id"]
        
        # Delete the job
        response = test_client.delete(
            f"/api/v1/jobs/{job_id}",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 204
        
        # Verify job is deleted
        get_response = test_client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_job_not_found(self, test_client, setup_test_db):
        """Test deleting a non-existent job."""
        response = test_client.delete(
            "/api/v1/jobs/999",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_job_runs_empty(self, test_client, setup_test_db, sample_job_data):
        """Test getting job runs when none exist."""
        # Create a job first
        create_response = test_client.post(
            "/api/v1/jobs",
            json=sample_job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        job_id = create_response.json()["id"]
        
        # Get job runs
        response = test_client.get(
            f"/api/v1/jobs/{job_id}/runs",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["runs"] == []
    
    @pytest.mark.asyncio
    async def test_execute_job_now_success(self, test_client, setup_test_db, sample_job_data):
        """Test executing a job immediately."""
        # Create a job first
        create_response = test_client.post(
            "/api/v1/jobs",
            json=sample_job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        job_id = create_response.json()["id"]
        
        # Execute the job
        response = test_client.post(
            f"/api/v1/jobs/{job_id}/execute",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["job_id"] == job_id
    
    @pytest.mark.asyncio
    async def test_execute_job_not_found(self, test_client, setup_test_db):
        """Test executing a non-existent job."""
        response = test_client.post(
            "/api/v1/jobs/999/execute",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 404


class TestHealthEndpoints:
    """Test class for health check endpoints."""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
    
    def test_health_check(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "scheduler"


class TestPagination:
    """Test class for pagination functionality."""
    
    @pytest.mark.asyncio
    async def test_pagination(self, test_client, setup_test_db):
        """Test pagination functionality."""
        # Create multiple jobs
        for i in range(15):
            job_data = {
                "name": f"Test Job {i}",
                "schedule_expr": "*/5 * * * *",
                "timezone": "UTC",
                "payload": {"type": "test", "index": i}
            }
            response = test_client.post(
                "/api/v1/jobs",
                json=job_data,
                headers={"X-API-Key": "your-secret-api-key-here"}
            )
            assert response.status_code == 201
        
        # Test first page
        response = test_client.get(
            "/api/v1/jobs?page=1&size=10",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 15
        assert len(data["jobs"]) == 10
        assert data["page"] == 1
        assert data["size"] == 10
        
        # Test second page
        response = test_client.get(
            "/api/v1/jobs?page=2&size=10",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 15
        assert len(data["jobs"]) == 5
        assert data["page"] == 2
        assert data["size"] == 10


class TestFiltering:
    """Test class for filtering functionality."""
    
    @pytest.mark.asyncio
    async def test_filter_by_status(self, test_client, setup_test_db):
        """Test filtering jobs by status."""
        # Create jobs with different statuses
        active_job = {
            "name": "Active Job",
            "schedule_expr": "*/5 * * * *",
            "timezone": "UTC",
            "status": "active",
            "payload": {"type": "test"}
        }
        
        paused_job = {
            "name": "Paused Job",
            "schedule_expr": "*/5 * * * *",
            "timezone": "UTC",
            "status": "paused",
            "payload": {"type": "test"}
        }
        
        # Create jobs
        test_client.post(
            "/api/v1/jobs",
            json=active_job,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        test_client.post(
            "/api/v1/jobs",
            json=paused_job,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        # Filter by active status
        response = test_client.get(
            "/api/v1/jobs?status=active",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["status"] == "active"
        
        # Filter by paused status
        response = test_client.get(
            "/api/v1/jobs?status=paused",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["status"] == "paused"
    
    @pytest.mark.asyncio
    async def test_filter_by_owner_id(self, test_client, setup_test_db):
        """Test filtering jobs by owner ID."""
        # Create jobs with different owner IDs
        user1_job = {
            "name": "User 1 Job",
            "schedule_expr": "*/5 * * * *",
            "timezone": "UTC",
            "owner_id": "user1",
            "payload": {"type": "test"}
        }
        
        user2_job = {
            "name": "User 2 Job",
            "schedule_expr": "*/5 * * * *",
            "timezone": "UTC",
            "owner_id": "user2",
            "payload": {"type": "test"}
        }
        
        # Create jobs
        test_client.post(
            "/api/v1/jobs",
            json=user1_job,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        test_client.post(
            "/api/v1/jobs",
            json=user2_job,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        # Filter by user1
        response = test_client.get(
            "/api/v1/jobs?owner_id=user1",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["owner_id"] == "user1"
