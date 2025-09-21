"""
Integration tests for the scheduler service.

This module tests the end-to-end functionality following SOLID principles:
- Single Responsibility: Each test has a single responsibility
- Open/Closed: Easy to extend with new integration test cases
- Liskov Substitution: Consistent test interface
- Interface Segregation: Separate test concerns
- Dependency Inversion: Depends on abstractions for testing
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from src.app.main import app
from src.app.db import get_async_db, Base
from src.app.models import Job, JobRun
from src.app.tasks import execute_job_task, poll_due_jobs


# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_integration.db"

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
async def test_client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestJobLifecycle:
    """Test class for complete job lifecycle."""
    
    @pytest.mark.asyncio
    async def test_create_and_execute_job(self, test_client, setup_test_db):
        """Test creating a job and executing it."""
        # Create a job
        job_data = {
            "name": "Integration Test Job",
            "schedule_expr": "*/1 * * * *",  # Every minute
            "timezone": "UTC",
            "payload": {
                "type": "sleep",
                "duration": 2
            },
            "retry_policy": {
                "max_retries": 2,
                "retry_delay": 10
            },
            "owner_id": "test_user"
        }
        
        response = await test_client.post(
            "/api/v1/jobs",
            json=job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 201
        job_response = response.json()
        job_id = job_response["id"]
        
        # Verify job was created
        assert job_response["name"] == job_data["name"]
        assert job_response["status"] == "active"
        assert job_response["schedule_expr"] == job_data["schedule_expr"]
        
        # Execute the job immediately
        execute_response = await test_client.post(
            f"/api/v1/jobs/{job_id}/execute",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert execute_response.status_code == 202
        execute_data = execute_response.json()
        assert "task_id" in execute_data
        assert execute_data["job_id"] == job_id
        
        # Wait for job execution to complete
        await asyncio.sleep(3)
        
        # Check job runs
        runs_response = await test_client.get(
            f"/api/v1/jobs/{job_id}/runs",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert runs_response.status_code == 200
        runs_data = runs_response.json()
        assert runs_data["total"] >= 1
        
        # Verify job run details
        job_run = runs_data["runs"][0]
        assert job_run["job_id"] == job_id
        assert job_run["status"] in ["success", "running", "pending"]
        assert job_run["started_at"] is not None
    
    @pytest.mark.asyncio
    async def test_job_scheduling_and_execution(self, test_client, setup_test_db):
        """Test job scheduling and automatic execution."""
        # Create a job with immediate execution
        future_time = datetime.utcnow() + timedelta(seconds=5)
        job_data = {
            "name": "Scheduled Test Job",
            "schedule_expr": future_time.strftime("%M %H %d %m *"),
            "timezone": "UTC",
            "payload": {
                "type": "compute",
                "iterations": 1000
            },
            "retry_policy": {
                "max_retries": 1,
                "retry_delay": 5
            }
        }
        
        response = await test_client.post(
            "/api/v1/jobs",
            json=job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 201
        job_response = response.json()
        job_id = job_response["id"]
        
        # Wait for scheduled execution
        await asyncio.sleep(10)
        
        # Check if job was executed
        runs_response = await test_client.get(
            f"/api/v1/jobs/{job_id}/runs",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert runs_response.status_code == 200
        runs_data = runs_response.json()
        
        # Job should have been executed
        assert runs_data["total"] >= 1
        
        # Verify job run
        job_run = runs_data["runs"][0]
        assert job_run["job_id"] == job_id
        assert job_run["status"] in ["success", "running", "pending"]
    
    @pytest.mark.asyncio
    async def test_job_retry_mechanism(self, test_client, setup_test_db):
        """Test job retry mechanism on failure."""
        # Create a job that will fail
        job_data = {
            "name": "Failing Test Job",
            "schedule_expr": "*/1 * * * *",
            "timezone": "UTC",
            "payload": {
                "type": "test_fail"  # This will cause a failure
            },
            "retry_policy": {
                "max_retries": 2,
                "retry_delay": 5
            }
        }
        
        response = await test_client.post(
            "/api/v1/jobs",
            json=job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 201
        job_response = response.json()
        job_id = job_response["id"]
        
        # Execute the job
        execute_response = await test_client.post(
            f"/api/v1/jobs/{job_id}/execute",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert execute_response.status_code == 202
        
        # Wait for retries
        await asyncio.sleep(15)
        
        # Check job runs
        runs_response = await test_client.get(
            f"/api/v1/jobs/{job_id}/runs",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert runs_response.status_code == 200
        runs_data = runs_response.json()
        
        # Should have multiple runs due to retries
        assert runs_data["total"] >= 1
        
        # Check retry count
        job_run = runs_data["runs"][0]
        assert job_run["retry_count"] >= 0


class TestJobManagement:
    """Test class for job management operations."""
    
    @pytest.mark.asyncio
    async def test_job_crud_operations(self, test_client, setup_test_db):
        """Test complete CRUD operations for jobs."""
        # Create a job
        job_data = {
            "name": "CRUD Test Job",
            "schedule_expr": "*/5 * * * *",
            "timezone": "UTC",
            "payload": {"type": "test"},
            "owner_id": "test_user"
        }
        
        create_response = await test_client.post(
            "/api/v1/jobs",
            json=job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert create_response.status_code == 201
        job_id = create_response.json()["id"]
        
        # Read the job
        get_response = await test_client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert get_response.status_code == 200
        job = get_response.json()
        assert job["name"] == job_data["name"]
        assert job["status"] == "active"
        
        # Update the job
        update_data = {
            "name": "Updated CRUD Test Job",
            "status": "paused"
        }
        
        update_response = await test_client.put(
            f"/api/v1/jobs/{job_id}",
            json=update_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert update_response.status_code == 200
        updated_job = update_response.json()
        assert updated_job["name"] == update_data["name"]
        assert updated_job["status"] == update_data["status"]
        
        # Delete the job
        delete_response = await test_client.delete(
            f"/api/v1/jobs/{job_id}",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert delete_response.status_code == 204
        
        # Verify job is deleted
        get_response = await test_client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_job_filtering_and_pagination(self, test_client, setup_test_db):
        """Test job filtering and pagination."""
        # Create multiple jobs with different attributes
        jobs_data = [
            {
                "name": "Active Job 1",
                "schedule_expr": "*/5 * * * *",
                "timezone": "UTC",
                "status": "active",
                "owner_id": "user1",
                "payload": {"type": "test"}
            },
            {
                "name": "Paused Job 1",
                "schedule_expr": "*/10 * * * *",
                "timezone": "UTC",
                "status": "paused",
                "owner_id": "user1",
                "payload": {"type": "test"}
            },
            {
                "name": "Active Job 2",
                "schedule_expr": "*/15 * * * *",
                "timezone": "UTC",
                "status": "active",
                "owner_id": "user2",
                "payload": {"type": "test"}
            }
        ]
        
        # Create jobs
        for job_data in jobs_data:
            response = await test_client.post(
                "/api/v1/jobs",
                json=job_data,
                headers={"X-API-Key": "your-secret-api-key-here"}
            )
            assert response.status_code == 201
        
        # Test filtering by status
        active_response = await test_client.get(
            "/api/v1/jobs?status=active",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert active_response.status_code == 200
        active_data = active_response.json()
        assert active_data["total"] == 2
        assert all(job["status"] == "active" for job in active_data["jobs"])
        
        # Test filtering by owner_id
        user1_response = await test_client.get(
            "/api/v1/jobs?owner_id=user1",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert user1_response.status_code == 200
        user1_data = user1_response.json()
        assert user1_data["total"] == 2
        assert all(job["owner_id"] == "user1" for job in user1_data["jobs"])
        
        # Test pagination
        paginated_response = await test_client.get(
            "/api/v1/jobs?page=1&size=2",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert paginated_response.status_code == 200
        paginated_data = paginated_response.json()
        assert paginated_data["total"] == 3
        assert len(paginated_data["jobs"]) == 2
        assert paginated_data["page"] == 1
        assert paginated_data["size"] == 2


class TestJobExecution:
    """Test class for job execution functionality."""
    
    @pytest.mark.asyncio
    async def test_different_job_types(self, test_client, setup_test_db):
        """Test execution of different job types."""
        job_types = [
            {
                "name": "Data Processing Job",
                "payload": {
                    "type": "data_processing",
                    "dataset": "test_data",
                    "batch_size": 100
                }
            },
            {
                "name": "Email Job",
                "payload": {
                    "type": "email",
                    "recipients": ["test@example.com"],
                    "subject": "Test Email",
                    "template": "test_template"
                }
            },
            {
                "name": "ML Training Job",
                "payload": {
                    "type": "ml_training",
                    "model": "test_model",
                    "epochs": 10,
                    "batch_size": 32
                }
            },
            {
                "name": "Sleep Job",
                "payload": {
                    "type": "sleep",
                    "duration": 1
                }
            },
            {
                "name": "Compute Job",
                "payload": {
                    "type": "compute",
                    "iterations": 1000
                }
            }
        ]
        
        for job_type in job_types:
            job_data = {
                "name": job_type["name"],
                "schedule_expr": "*/1 * * * *",
                "timezone": "UTC",
                "payload": job_type["payload"],
                "retry_policy": {
                    "max_retries": 1,
                    "retry_delay": 5
                }
            }
            
            # Create job
            create_response = await test_client.post(
                "/api/v1/jobs",
                json=job_data,
                headers={"X-API-Key": "your-secret-api-key-here"}
            )
            
            assert create_response.status_code == 201
            job_id = create_response.json()["id"]
            
            # Execute job
            execute_response = await test_client.post(
                f"/api/v1/jobs/{job_id}/execute",
                headers={"X-API-Key": "your-secret-api-key-here"}
            )
            
            assert execute_response.status_code == 202
            
            # Wait for execution
            await asyncio.sleep(2)
            
            # Check job runs
            runs_response = await test_client.get(
                f"/api/v1/jobs/{job_id}/runs",
                headers={"X-API-Key": "your-secret-api-key-here"}
            )
            
            assert runs_response.status_code == 200
            runs_data = runs_response.json()
            assert runs_data["total"] >= 1
            
            # Verify job run
            job_run = runs_data["runs"][0]
            assert job_run["job_id"] == job_id
            assert job_run["status"] in ["success", "running", "pending"]
    
    @pytest.mark.asyncio
    async def test_job_execution_with_logs(self, test_client, setup_test_db):
        """Test job execution with detailed logs."""
        job_data = {
            "name": "Logging Test Job",
            "schedule_expr": "*/1 * * * *",
            "timezone": "UTC",
            "payload": {
                "type": "sleep",
                "duration": 1
            },
            "retry_policy": {
                "max_retries": 1,
                "retry_delay": 5
            }
        }
        
        # Create job
        create_response = await test_client.post(
            "/api/v1/jobs",
            json=job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert create_response.status_code == 201
        job_id = create_response.json()["id"]
        
        # Execute job
        execute_response = await test_client.post(
            f"/api/v1/jobs/{job_id}/execute",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert execute_response.status_code == 202
        
        # Wait for execution
        await asyncio.sleep(3)
        
        # Check job runs with logs
        runs_response = await test_client.get(
            f"/api/v1/jobs/{job_id}/runs",
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert runs_response.status_code == 200
        runs_data = runs_response.json()
        assert runs_data["total"] >= 1
        
        # Verify job run details
        job_run = runs_data["runs"][0]
        assert job_run["job_id"] == job_id
        assert job_run["started_at"] is not None
        assert job_run["retry_count"] >= 0
        
        # If job completed successfully, check logs
        if job_run["status"] == "success":
            assert job_run["finished_at"] is not None
            assert job_run["logs"] is not None


class TestErrorHandling:
    """Test class for error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_invalid_schedule_expression(self, test_client, setup_test_db):
        """Test handling of invalid schedule expressions."""
        invalid_job_data = {
            "name": "Invalid Schedule Job",
            "schedule_expr": "invalid schedule expression",
            "timezone": "UTC",
            "payload": {"type": "test"}
        }
        
        response = await test_client.post(
            "/api/v1/jobs",
            json=invalid_job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, test_client, setup_test_db):
        """Test handling of missing required fields."""
        incomplete_job_data = {
            "name": "Incomplete Job"
            # Missing required fields
        }
        
        response = await test_client.post(
            "/api/v1/jobs",
            json=incomplete_job_data,
            headers={"X-API-Key": "your-secret-api-key-here"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, test_client, setup_test_db):
        """Test handling of unauthorized access."""
        job_data = {
            "name": "Unauthorized Job",
            "schedule_expr": "*/5 * * * *",
            "timezone": "UTC",
            "payload": {"type": "test"}
        }
        
        # Try to create job without API key
        response = await test_client.post(
            "/api/v1/jobs",
            json=job_data
        )
        
        assert response.status_code == 401
        
        # Try to create job with wrong API key
        response = await test_client.post(
            "/api/v1/jobs",
            json=job_data,
            headers={"X-API-Key": "wrong-api-key"}
        )
        
        assert response.status_code == 401
