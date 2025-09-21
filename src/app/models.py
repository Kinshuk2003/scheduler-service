from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()


class Job(Base):
    """Job model for storing scheduled jobs."""
    
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    schedule_expr = Column(String(255), nullable=False)  # cron expression or interval
    timezone = Column(String(50), default="UTC")
    payload = Column(JSON, nullable=False)  # job data
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True, index=True)
    status = Column(String(20), default="active", index=True)  # active, paused, completed
    retry_policy = Column(JSON, nullable=True)  # retry configuration
    owner_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to job runs
    runs = relationship("JobRun", back_populates="job", cascade="all, delete-orphan")


class JobRun(Base):
    """Job run history model for tracking job executions."""
    
    __tablename__ = "job_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)  # pending, running, success, failed
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    logs = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to job
    job = relationship("Job", back_populates="runs")
