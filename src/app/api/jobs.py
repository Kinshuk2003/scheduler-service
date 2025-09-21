"""
Job management API endpoints.

This module implements the REST API for job management following SOLID principles:
- Single Responsibility: Each endpoint has a single responsibility
- Open/Closed: Easy to extend with new job types
- Liskov Substitution: Consistent interface for all job operations
- Interface Segregation: Separate concerns for different operations
- Dependency Inversion: Depends on abstractions, not concretions
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import logging

from ..db import get_async_db
from ..models import Job, JobRun
from ..schemas import (
    JobCreate, JobUpdate, JobResponse, JobRunResponse,
    JobListResponse, JobRunListResponse
)
from ..settings import settings
from ..tasks import execute_job_task
from ..scheduler import calculate_next_run, is_cron_expression

logger = logging.getLogger(__name__)

router = APIRouter()


class JobService:
    """
    Service class for job operations following the Service Layer pattern.
    This encapsulates business logic and provides a clean interface for controllers.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_job(self, job_data: JobCreate) -> Job:
        """Create a new job with validation and next run calculation."""
        # Validate schedule expression
        if not is_cron_expression(job_data.schedule_expr):
            # Try to parse as datetime for one-time jobs
            try:
                datetime.fromisoformat(job_data.schedule_expr.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid schedule expression. Must be valid cron expression or ISO datetime."
                )
        
        # Calculate next run time
        next_run = calculate_next_run(job_data.schedule_expr, job_data.timezone)
        
        # Create job instance
        job = Job(
            name=job_data.name,
            schedule_expr=job_data.schedule_expr,
            timezone=job_data.timezone,
            payload=job_data.payload or {},
            retry_policy=job_data.retry_policy or {},
            owner_id=job_data.owner_id,
            status=job_data.status or "active",
            next_run=next_run
        )
        
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        
        logger.info(f"Created job {job.id}: {job.name}")
        return job
    
    async def get_job(self, job_id: int) -> Job:
        """Get a job by ID with runs."""
        result = await self.db.execute(
            select(Job)
            .options(selectinload(Job.runs))
            .where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job with id {job_id} not found"
            )
        
        return job
    
    async def list_jobs(
        self, 
        page: int = 1, 
        size: int = 10,
        status: Optional[str] = None,
        owner_id: Optional[str] = None
    ) -> tuple[List[Job], int]:
        """List jobs with pagination and filtering."""
        # Build query
        query = select(Job)
        count_query = select(func.count(Job.id))
        
        # Apply filters
        if status:
            query = query.where(Job.status == status)
            count_query = count_query.where(Job.status == status)
        
        if owner_id:
            query = query.where(Job.owner_id == owner_id)
            count_query = count_query.where(Job.owner_id == owner_id)
        
        # Apply pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        # Execute queries
        result = await self.db.execute(query)
        jobs = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        return jobs, total
    
    async def update_job(self, job_id: int, update_data: JobUpdate) -> Job:
        """Update a job."""
        job = await self.get_job(job_id)
        
        # Update fields
        if update_data.name is not None:
            job.name = update_data.name
        if update_data.schedule_expr is not None:
            job.schedule_expr = update_data.schedule_expr
            # Recalculate next run time
            job.next_run = calculate_next_run(update_data.schedule_expr, job.timezone)
        if update_data.timezone is not None:
            job.timezone = update_data.timezone
            # Recalculate next run time
            job.next_run = calculate_next_run(job.schedule_expr, update_data.timezone)
        if update_data.payload is not None:
            job.payload = update_data.payload
        if update_data.status is not None:
            job.status = update_data.status
        if update_data.retry_policy is not None:
            job.retry_policy = update_data.retry_policy
        if update_data.owner_id is not None:
            job.owner_id = update_data.owner_id
        
        job.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(job)
        
        logger.info(f"Updated job {job.id}: {job.name}")
        return job
    
    async def delete_job(self, job_id: int) -> bool:
        """Delete a job and all its runs."""
        job = await self.get_job(job_id)
        
        # Delete all job runs first (cascade should handle this, but being explicit)
        await self.db.execute(
            select(JobRun).where(JobRun.job_id == job_id)
        )
        
        await self.db.delete(job)
        await self.db.commit()
        
        logger.info(f"Deleted job {job.id}: {job.name}")
        return True
    
    async def get_job_runs(self, job_id: int, page: int = 1, size: int = 10) -> tuple[List[JobRun], int]:
        """Get job run history with pagination."""
        # Verify job exists
        await self.get_job(job_id)
        
        # Build queries
        query = select(JobRun).where(JobRun.job_id == job_id)
        count_query = select(func.count(JobRun.id)).where(JobRun.job_id == job_id)
        
        # Apply pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        # Execute queries
        result = await self.db.execute(query)
        runs = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        return runs, total
    
    async def run_job_immediately(self, job_id: int) -> JobRun:
        """Run a job immediately."""
        job = await self.get_job(job_id)
        
        if job.status != "active":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot run job with status '{job.status}'. Job must be active."
            )
        
        # Create a new job run
        job_run = JobRun(
            job_id=job.id,
            status="pending",
            created_at=datetime.utcnow(),
            retry_count=0
        )
        
        self.db.add(job_run)
        await self.db.flush()  # Get the ID
        
        # Enqueue the job for execution
        execute_job_task.delay(job.id, job_run.id, job.payload or {})
        
        await self.db.commit()
        await self.db.refresh(job_run)
        
        logger.info(f"Queued job {job.id} for immediate execution (run {job_run.id})")
        return job_run


def get_job_service(db: AsyncSession = Depends(get_async_db)) -> JobService:
    """Dependency to get job service."""
    return JobService(db)


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    service: JobService = Depends(get_job_service)
) -> JobResponse:
    """
    Create a new job.
    
    Creates a new scheduled job with the specified configuration.
    """
    try:
        job = await service.create_job(job_data)
        return JobResponse.from_orm(job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while creating job"
        )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    owner_id: Optional[str] = Query(None, description="Filter by owner ID"),
    service: JobService = Depends(get_job_service)
) -> JobListResponse:
    """
    List all jobs.
    
    Returns a paginated list of jobs with optional filtering.
    """
    try:
        jobs, total = await service.list_jobs(page, size, status, owner_id)
        return JobListResponse(
            jobs=[JobResponse.from_orm(job) for job in jobs],
            total=total,
            page=page,
            size=size
        )
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while listing jobs"
        )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    service: JobService = Depends(get_job_service)
) -> JobResponse:
    """
    Get job details.
    
    Returns detailed information about a specific job.
    """
    try:
        job = await service.get_job(job_id)
        return JobResponse.from_orm(job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while getting job"
        )


@router.put("/jobs/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    update_data: JobUpdate,
    service: JobService = Depends(get_job_service)
) -> JobResponse:
    """
    Update a job.
    
    Updates an existing job with the provided data.
    """
    try:
        job = await service.update_job(job_id, update_data)
        return JobResponse.from_orm(job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while updating job"
        )


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    service: JobService = Depends(get_job_service)
) -> None:
    """
    Delete a job.
    
    Permanently removes the job and all its run history.
    """
    try:
        await service.delete_job(job_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while deleting job"
        )


@router.get("/jobs/{job_id}/runs", response_model=JobRunListResponse)
async def get_job_runs(
    job_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    service: JobService = Depends(get_job_service)
) -> JobRunListResponse:
    """
    Get job run history.
    
    Returns the execution history for a specific job.
    """
    try:
        runs, total = await service.get_job_runs(job_id, page, size)
        return JobRunListResponse(
            runs=[JobRunResponse.from_orm(run) for run in runs],
            total=total,
            page=page,
            size=size
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job runs for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while getting job runs"
        )


@router.post("/jobs/{job_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_job(
    job_id: int,
    service: JobService = Depends(get_job_service)
) -> dict:
    """
    Run a job immediately.
    
    Queues a job for immediate execution, bypassing its schedule.
    """
    try:
        job_run = await service.run_job_immediately(job_id)
        return {
            "message": "Job queued for immediate execution",
            "job_id": job_id,
            "run_id": job_run.id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while executing job"
        )
