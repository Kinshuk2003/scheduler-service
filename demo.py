"""
Demo script for the Scheduler Service.

This script demonstrates the complete functionality of the scheduler service
including job creation, scheduling, execution, and monitoring with real code execution.
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List


class SchedulerDemo:
    """Demo client for the Scheduler Service."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = "your-secret-api-key-here"):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    async def health_check(self) -> bool:
        """Check if the API is healthy."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()["status"] == "healthy"
        except Exception:
            return False
    
    async def create_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new job."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/jobs",
                headers=self.headers,
                json=job_data
            )
            response.raise_for_status()
            return response.json()
    
    async def list_jobs(self, page: int = 1, size: int = 10, status: str = None) -> Dict[str, Any]:
        """List all jobs."""
        params = {"page": page, "size": size}
        if status:
            params["status"] = status
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/jobs",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get job details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/jobs/{job_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def update_job(self, job_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a job."""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/api/v1/jobs/{job_id}",
                headers=self.headers,
                json=update_data
            )
            response.raise_for_status()
            return response.json()
    
    async def delete_job(self, job_id: int) -> bool:
        """Delete a job."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/api/v1/jobs/{job_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"Error deleting job {job_id}: {e}")
            return False
    
    async def get_job_runs(self, job_id: int, page: int = 1, size: int = 10) -> Dict[str, Any]:
        """Get job run history."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/jobs/{job_id}/runs",
                headers=self.headers,
                params={"page": page, "size": size}
            )
            response.raise_for_status()
            return response.json()
    
    async def run_job(self, job_id: int) -> Dict[str, Any]:
        """Run a job immediately."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/jobs/{job_id}/run",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()


async def main():
    """Main demo function."""
    print(" Scheduler Service Demo - Real Code Execution")
    print("=" * 60)
    
    demo = SchedulerDemo()
    
    # Health check
    print("1. Testing API health...")
    if not await demo.health_check():
        print(" Cannot connect to API: All connection attempts failed")
        print("Make sure the API is running on http://localhost:8000")
        return
    print(" API is healthy")
    
    # Create sample jobs with real code execution
    print("\n2. Creating sample jobs with real code execution...")
    
    # Job 1: Python code execution
    python_code = '''
import math
import random

# Calculate the sum of squares of first 1000 numbers
result = sum(i**2 for i in range(1000))
print(f"Sum of squares 0-999: {result}")

# Calculate some mathematical constants
pi_approximation = 4 * sum((-1)**i / (2*i + 1) for i in range(10000))
print(f"Pi approximation: {pi_approximation}")

# Generate and analyze random data
data = [random.randint(1, 100) for _ in range(1000)]
mean = sum(data) / len(data)
variance = sum((x - mean)**2 for x in data) / len(data)
print(f"Random data analysis - Mean: {mean:.2f}, Variance: {variance:.2f}")
'''
    
    job1_data = {
        "name": "Python Code Execution Job",
        "schedule_expr": "*/2 * * * *",  # Every 2 minutes
        "timezone": "UTC",
        "payload": {
            "type": "python_code",
            "code": python_code,
            "description": "Mathematical calculations and data analysis"
        },
        "retry_policy": {
            "max_retries": 2,
            "retry_delay": 30
        },
        "owner_id": "math_team"
    }
    
    try:
        job1 = await demo.create_job(job1_data)
        print(f" Created job: {job1['name']} (ID: {job1['id']})")
    except Exception as e:
        print(f" Failed to create job 1: {e}")
        return
    
    # Job 2: Number crunching job
    job2_data = {
        "name": "Number Crunching Job",
        "schedule_expr": "*/3 * * * *",  # Every 3 minutes
        "timezone": "UTC",
        "payload": {
            "type": "number_crunching",
            "operation": "fibonacci",
            "n": 20,
            "description": "Calculate Fibonacci sequence"
        },
        "retry_policy": {
            "max_retries": 2,
            "retry_delay": 30
        },
        "owner_id": "math_team"
    }
    
    try:
        job2 = await demo.create_job(job2_data)
        print(f" Created job: {job2['name']} (ID: {job2['id']})")
    except Exception as e:
        print(f" Failed to create job 2: {e}")
        return
    
    # Job 3: Custom calculation with Python code
    custom_calculation_code = '''
import numpy as np

# Create matrices and perform operations
matrix_a = np.random.randint(1, 10, (50, 50))
matrix_b = np.random.randint(1, 10, (50, 50))

# Matrix multiplication
result = np.dot(matrix_a, matrix_b)

# Calculate statistics
print(f"Matrix multiplication result shape: {result.shape}")
print(f"Sum of all elements: {np.sum(result)}")
print(f"Mean: {np.mean(result):.2f}")
print(f"Standard deviation: {np.std(result):.2f}")

# Eigenvalue calculation
eigenvalues = np.linalg.eigvals(result)
print(f"Largest eigenvalue: {np.max(eigenvalues):.2f}")
'''
    
    job3_data = {
        "name": "Matrix Operations Job",
        "schedule_expr": "*/5 * * * *",  # Every 5 minutes
        "timezone": "UTC",
        "payload": {
            "type": "python_code",
            "code": custom_calculation_code,
            "description": "Matrix operations and linear algebra"
        },
        "retry_policy": {
            "max_retries": 1,
            "retry_delay": 60
        },
        "owner_id": "math_team"
    }
    
    try:
        job3 = await demo.create_job(job3_data)
        print(f" Created job: {job3['name']} (ID: {job3['id']})")
    except Exception as e:
        print(f" Failed to create job 3: {e}")
        return
    
    # Job 4: Statistical analysis
    job4_data = {
        "name": "Statistical Analysis Job",
        "schedule_expr": "*/4 * * * *",  # Every 4 minutes
        "timezone": "UTC",
        "payload": {
            "type": "number_crunching",
            "operation": "statistical_analysis",
            "data": [i for i in range(1, 1001)],  # Numbers 1-1000
            "description": "Statistical analysis of numerical data"
        },
        "retry_policy": {
            "max_retries": 2,
            "retry_delay": 30
        },
        "owner_id": "stats_team"
    }
    
    try:
        job4 = await demo.create_job(job4_data)
        print(f" Created job: {job4['name']} (ID: {job4['id']})")
    except Exception as e:
        print(f" Failed to create job 4: {e}")
        return
    
    # List all jobs
    print("\n3. Listing all jobs...")
    try:
        jobs = await demo.list_jobs()
        print(f" Found {jobs['total']} jobs:")
        for job in jobs['jobs']:
            print(f"   - {job['name']} (ID: {job['id']}, Status: {job['status']})")
    except Exception as e:
        print(f" Failed to list jobs: {e}")
    
    # Get job details
    print(f"\n4. Getting details for job {job1['id']}...")
    try:
        job_details = await demo.get_job(job1['id'])
        print(f" Job details:")
        print(f"   - Name: {job_details['name']}")
        print(f"   - Schedule: {job_details['schedule_expr']}")
        print(f"   - Next Run: {job_details['next_run']}")
        print(f"   - Status: {job_details['status']}")
    except Exception as e:
        print(f" Failed to get job details: {e}")
    
    # Run a job immediately
    print(f"\n5. Running job {job2['id']} immediately...")
    try:
        run_result = await demo.run_job(job2['id'])
        print(f" Job queued for immediate execution (Run ID: {run_result['run_id']})")
    except Exception as e:
        print(f" Failed to run job: {e}")
    
    # Wait for job executions
    print("\n6. Waiting for job executions...")
    print("   (This will take about 5 minutes to see multiple job runs)")
    await asyncio.sleep(300)  # Wait for 5 minutes
    
    # Check job runs for all jobs
    print(f"\n7. Checking job runs...")
    for job in [job1, job2, job3, job4]:
        try:
            runs = await demo.get_job_runs(job['id'])
            print(f" Job {job['id']} ({job['name']}): {runs['total']} runs")
            for run in runs['runs'][:2]:  # Show first 2 runs
                print(f"   - Run ID: {run['id']}, Status: {run['status']}, Started: {run['started_at']}")
                if run['logs']:
                    # Show first 100 characters of logs
                    log_preview = run['logs'][:100] + "..." if len(run['logs']) > 100 else run['logs']
                    print(f"     Logs: {log_preview}")
        except Exception as e:
            print(f" Failed to get job runs for job {job['id']}: {e}")
    
    # Clean up - delete jobs
    print(f"\n8. Cleaning up...")
    for job in [job1, job2, job3, job4]:
        try:
            if await demo.delete_job(job['id']):
                print(f" Deleted job {job['id']}")
            else:
                print(f" Failed to delete job {job['id']}")
        except Exception as e:
            print(f" Failed to delete job {job['id']}: {e}")
    
    print("\n Demo completed successfully!")
    print("\nTo run this demo:")
    print("1. Start the services: docker-compose up -d")
    print("2. Wait for services to be ready (about 30 seconds)")
    print("3. Run: python demo.py")
    print("\nNote: This demo shows real code execution including:")
    print("- Python code execution with mathematical calculations")
    print("- Number crunching operations (Fibonacci, prime numbers)")
    print("- Matrix operations and linear algebra")
    print("- Statistical analysis of data")


if __name__ == "__main__":
    asyncio.run(main())
