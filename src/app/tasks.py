"""
Celery tasks for job execution.

This module implements the background task processing following SOLID principles:
- Single Responsibility: Each task has a single responsibility
- Open/Closed: Easy to extend with new job types
- Liskov Substitution: Consistent task interface
- Interface Segregation: Separate concerns for different task types
- Dependency Inversion: Depends on abstractions, not concretions
"""

import asyncio
import json
import logging
import time
import subprocess
import tempfile
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from enum import Enum

from celery import Task
from sqlalchemy import select, update, create_engine
from sqlalchemy.orm import sessionmaker, selectinload

from .celery_app import celery_app
from .models import Job, JobRun
from .scheduler import calculate_next_run, is_cron_expression
from .settings import settings

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


class RetryPolicy:
    """
    Retry policy implementation following the Strategy pattern.
    This allows different retry strategies to be implemented.
    """
    
    def __init__(self, policy_config: Dict[str, Any]):
        self.max_retries = policy_config.get("max_retries", 3)
        self.retry_delay = policy_config.get("retry_delay", 60)  # seconds
        self.backoff_factor = policy_config.get("backoff_factor", 2)
    
    def should_retry(self, current_retry_count: int) -> bool:
        """Check if the task should be retried."""
        return current_retry_count < self.max_retries
    
    def get_retry_delay(self, current_retry_count: int) -> int:
        """Calculate the delay before retry."""
        return self.retry_delay * (self.backoff_factor ** current_retry_count)


# Create synchronous database engine for Celery tasks
sync_engine = create_engine(
    settings.database_url_sync,
    echo=settings.environment == "development",
    future=True
)

# Create synchronous session factory
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)


def get_sync_session():
    """Get synchronous database session for Celery tasks."""
    return SyncSessionLocal()


@celery_app.task(bind=True, max_retries=3)
def execute_job_task(self, job_id: int, job_run_id: int, payload: Dict[str, Any]):
    """
    Celery task to execute a scheduled job.
    This task supports different job types including real code execution.
    """
    session = get_sync_session()
    job_run = None
    job = None

    try:
        # Fetch job and job run
        job_run = session.query(JobRun).filter(JobRun.id == job_run_id).first()
        if not job_run:
            logger.error(f"JobRun with ID {job_run_id} not found.")
            return

        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job with ID {job_id} not found.")
            job_run.status = "failed"
            job_run.error = "Job not found."
            session.commit()
            return

        logger.info(f"Executing job_id={job_id}, job_run_id={job_run_id}, payload={payload}")

        job_run.status = "running"
        job_run.started_at = datetime.utcnow()
        session.commit()

        job_type = payload.get("type", "default")
        result_log = ""

        # --- Strategy Pattern for Job Execution ---
        if job_type == "python_code":
            result_log = _execute_python_code_job(payload)
        elif job_type == "shell_script":
            result_log = _execute_shell_script_job(payload)
        elif job_type == "data_processing":
            result_log = _execute_data_processing_job(payload)
        elif job_type == "email_notification":
            result_log = _execute_email_notification_job(payload)
        elif job_type == "ml_training":
            result_log = _execute_ml_training_job(payload)
        elif job_type == "number_crunching":
            result_log = _execute_number_crunching_job(payload)
        elif job_type == "dummy_sleep":
            sleep_duration = payload.get("duration", 5)
            time.sleep(sleep_duration)
            result_log = f"Dummy sleep job completed after {sleep_duration} seconds."
        else:
            result_log = _execute_default_job(payload)

        job_run.status = "success"
        job_run.logs = result_log
        job_run.finished_at = datetime.utcnow()
        job.last_run = job_run.started_at
        job.next_run = calculate_next_run(job.schedule_expr, job.timezone)
        session.commit()
        logger.info(f"Job {job_id} (run {job_run_id}) completed successfully.")

    except Exception as e:
        logger.error(f"Job {job_id} (run {job_run_id}) failed: {e}", exc_info=True)
        try:
            if job_run:
                job_run.status = "failed"
                job_run.error = str(e)
                job_run.finished_at = datetime.utcnow()
                job_run.retry_count = (job_run.retry_count or 0) + 1
                session.commit()

            # --- Retry Logic with Exponential Backoff ---
            if job and job.retry_policy and job_run.retry_count <= job.retry_policy.get("max_retries", 3):
                countdown = 2 ** job_run.retry_count * job.retry_policy.get("base_delay", 60) # Exponential backoff
                logger.warning(f"Retrying job {job_id} (run {job_run_id}) in {countdown} seconds. Retry count: {job_run.retry_count}")
                raise self.retry(exc=e, countdown=countdown)
            else:
                logger.error(f"Job {job_id} (run {job_run_id}) failed permanently after {job_run.retry_count} retries.")
        except Exception as commit_error:
            logger.error(f"Error committing failure status: {commit_error}")
            session.rollback()

    finally:
        try:
            session.close()
        except Exception as close_error:
            logger.error(f"Error closing session: {close_error}")


def _execute_python_code_job(payload: Dict[str, Any]) -> str:
    """Execute Python code provided in the payload."""
    logger.info(f"Running Python code job with payload: {payload}")
    
    code = payload.get("code", "")
    if not code:
        raise ValueError("No Python code provided in payload")
    
    # Create a temporary file for the code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # Execute the Python code
        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=os.path.dirname(temp_file)
        )
        
        if result.returncode == 0:
            return f"Python code executed successfully.\nOutput: {result.stdout}"
        else:
            raise Exception(f"Python code execution failed with return code {result.returncode}.\nError: {result.stderr}")
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def _execute_shell_script_job(payload: Dict[str, Any]) -> str:
    """Execute shell script provided in the payload."""
    logger.info(f"Running shell script job with payload: {payload}")
    
    script = payload.get("script", "")
    if not script:
        raise ValueError("No shell script provided in payload")
    
    # Create a temporary file for the script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
        f.write(script)
        temp_file = f.name
    
    try:
        # Make the script executable
        os.chmod(temp_file, 0o755)
        
        # Execute the shell script
        result = subprocess.run(
            ['/bin/bash', temp_file],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=os.path.dirname(temp_file)
        )
        
        if result.returncode == 0:
            return f"Shell script executed successfully.\nOutput: {result.stdout}"
        else:
            raise Exception(f"Shell script execution failed with return code {result.returncode}.\nError: {result.stderr}")
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def _execute_number_crunching_job(payload: Dict[str, Any]) -> str:
    """Execute number crunching operations."""
    logger.info(f"Running number crunching job with payload: {payload}")
    
    operation = payload.get("operation", "default")
    data = payload.get("data", [])
    
    if operation == "fibonacci":
        n = payload.get("n", 10)
        result = _calculate_fibonacci(n)
        return f"Fibonacci sequence up to {n}: {result}"
    
    elif operation == "prime_numbers":
        limit = payload.get("limit", 100)
        result = _calculate_prime_numbers(limit)
        return f"Prime numbers up to {limit}: {result[:10]}... (total: {len(result)})"
    
    elif operation == "matrix_multiplication":
        size = payload.get("size", 100)
        result = _matrix_multiplication(size)
        return f"Matrix multiplication ({size}x{size}): {result}"
    
    elif operation == "statistical_analysis":
        result = _statistical_analysis(data)
        return f"Statistical analysis: {result}"
    
    elif operation == "custom_calculation":
        code = payload.get("code", "")
        if code:
            return _execute_python_code_job({"code": code})
        else:
            raise ValueError("No custom calculation code provided")
    
    else:
        # Default number crunching
        result = sum(i**2 for i in range(1000))
        return f"Default number crunching completed. Sum of squares 0-999: {result}"


def _calculate_fibonacci(n: int) -> list:
    """Calculate Fibonacci sequence up to n."""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    
    return fib


def _calculate_prime_numbers(limit: int) -> list:
    """Calculate prime numbers up to limit using Sieve of Eratosthenes."""
    if limit < 2:
        return []
    
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            for j in range(i*i, limit + 1, i):
                sieve[j] = False
    
    return [i for i in range(2, limit + 1) if sieve[i]]


def _matrix_multiplication(size: int) -> dict:
    """Perform matrix multiplication of two random matrices."""
    import random
    
    # Generate random matrices
    matrix_a = [[random.randint(1, 10) for _ in range(size)] for _ in range(size)]
    matrix_b = [[random.randint(1, 10) for _ in range(size)] for _ in range(size)]
    
    # Perform multiplication
    result = [[0 for _ in range(size)] for _ in range(size)]
    
    for i in range(size):
        for j in range(size):
            for k in range(size):
                result[i][j] += matrix_a[i][k] * matrix_b[k][j]
    
    return {
        "size": size,
        "sum_of_elements": sum(sum(row) for row in result),
        "max_element": max(max(row) for row in result),
        "min_element": min(min(row) for row in result)
    }


def _statistical_analysis(data: list) -> dict:
    """Perform statistical analysis on provided data."""
    if not data:
        data = [i for i in range(100)]  # Default data
    
    n = len(data)
    mean = sum(data) / n
    variance = sum((x - mean) ** 2 for x in data) / n
    std_dev = variance ** 0.5
    
    return {
        "count": n,
        "mean": round(mean, 4),
        "variance": round(variance, 4),
        "std_deviation": round(std_dev, 4),
        "min": min(data),
        "max": max(data),
        "sum": sum(data)
    }


def _execute_data_processing_job(payload: Dict[str, Any]) -> str:
    """Simulates a data processing job."""
    logger.info(f"Running data processing job with payload: {payload}")
    time.sleep(5)  # Simulate work
    return f"Data processing for {payload.get('dataset_id')} completed."


def _execute_email_notification_job(payload: Dict[str, Any]) -> str:
    """Simulates an email notification job."""
    logger.info(f"Sending email notification to {payload.get('recipient')} with subject: {payload.get('subject')}")
    time.sleep(2)  # Simulate work
    return f"Email sent to {payload.get('recipient')}."


def _execute_ml_training_job(payload: Dict[str, Any]) -> str:
    """Simulates an ML model training job."""
    logger.info(f"Starting ML training for model: {payload.get('model_name')}")
    time.sleep(10)  # Simulate longer work
    return f"ML model {payload.get('model_name')} trained successfully."


def _execute_default_job(payload: Dict[str, Any]) -> str:
    """Default job execution if no specific type is matched."""
    logger.info(f"Running default job with payload: {payload}")
    time.sleep(1)  # Simulate work
    return f"Default job executed with data: {payload}."


@celery_app.task(bind=True)
def poll_due_jobs(self):
    """
    Celery Beat task to poll for jobs whose next_run is due.
    Enqueues them to the Celery worker.
    """
    session = get_sync_session()
    logger.info("Polling for due jobs...")
    now_utc = datetime.utcnow()

    try:
        # Select jobs that are active and due
        due_jobs = session.query(Job).filter(
            Job.status == "active",
            Job.next_run <= now_utc
        ).with_for_update(skip_locked=True).all()  # Prevents multiple beat instances from picking same job

        if not due_jobs:
            logger.info("No jobs due at this time.")
            return

        logger.info(f"Found {len(due_jobs)} jobs due.")

        for job in due_jobs:
            try:
                # Create a new JobRun entry
                new_run = JobRun(
                    job_id=job.id,
                    status="pending",
                    created_at=now_utc,
                    retry_count=0  # Initialize retry count
                )
                session.add(new_run)
                session.flush()  # To get the new_run.id

                # Enqueue the job for execution
                execute_job_task.delay(job.id, new_run.id, job.payload or {})
                logger.info(f"Enqueued job_id={job.id} (run_id={new_run.id}) for execution.")

                # Update job's next_run immediately to prevent re-scheduling by other beat instances
                # and calculate the next scheduled run
                job.last_run = now_utc
                job.next_run = calculate_next_run(job.schedule_expr, job.timezone)
                if not job.next_run:
                    job.status = "completed"  # Mark as completed if no future runs
                    logger.warning(f"Job {job.id} has no future runs, marking as 'completed'.")
                session.commit()  # Commit changes for each job to release lock faster
                
            except Exception as job_error:
                logger.error(f"Error processing job {job.id}: {job_error}")
                session.rollback()
                continue

    except Exception as e:
        logger.error(f"Error in poll_due_jobs: {e}", exc_info=True)
        session.rollback()
    finally:
        try:
            session.close()
        except Exception as close_error:
            logger.error(f"Error closing session: {close_error}")
