from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class JobCreate(BaseModel):
    """Schema for creating a new job."""
    name: str = Field(..., min_length=1, max_length=255, description="Job name")
    schedule_expr: str = Field(..., description="Cron expression or interval (e.g., '*/10 * * * *' or '10s')")
    timezone: str = Field(default="UTC", description="Timezone for the schedule")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Job payload data")
    retry_policy: Optional[Dict[str, Any]] = Field(None, description="Retry policy configuration")
    owner_id: Optional[str] = Field(None, max_length=100, description="Owner identifier")
    status: Optional[str] = Field("active", pattern="^(active|paused|completed)$", description="Job status")


class JobUpdate(BaseModel):
    """Schema for updating a job."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    schedule_expr: Optional[str] = None
    timezone: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(active|paused|completed)$")
    retry_policy: Optional[Dict[str, Any]] = None
    owner_id: Optional[str] = Field(None, max_length=100)


class JobResponse(BaseModel):
    """Schema for job response."""
    id: int
    name: str
    schedule_expr: str
    timezone: str
    payload: Dict[str, Any]
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: str
    retry_policy: Optional[Dict[str, Any]] = None
    owner_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobRunResponse(BaseModel):
    """Schema for job run response."""
    id: int
    job_id: int
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    logs: Optional[str]
    error: Optional[str]
    retry_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Schema for job list response."""
    jobs: list[JobResponse]
    total: int
    page: int
    size: int


class JobRunListResponse(BaseModel):
    """Schema for job run list response."""
    runs: list[JobRunResponse]
    total: int
    page: int
    size: int
