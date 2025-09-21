# Scheduler Service

A production-ready microservice for scheduling and executing background jobs with support for **real code execution**, cron expressions, datetime scheduling, and interval-based execution. Built with FastAPI, Celery, PostgreSQL, and Redis following SOLID principles and design patterns.

##  What This Service Does

The Scheduler Service provides a comprehensive solution for managing background job execution with the following capabilities:

- **Real Code Execution**: Execute actual Python code, shell scripts, and custom programs
- **Job Management**: Create, read, update, and delete scheduled jobs
- **Multiple Schedule Types**: Support for cron expressions, specific datetime, and interval-based scheduling
- **Background Processing**: Asynchronous job execution using Celery workers
- **Job Monitoring**: Real-time monitoring and execution history tracking
- **Retry Logic**: Configurable retry policies with exponential backoff
- **API Authentication**: Secure API access with API key authentication
- **Scalable Architecture**: Designed for horizontal scaling and high availability

##  Current Architecture

`mermaid
graph TB
    subgraph "Client Layer"
        C[Client Applications]
        API[API Documentation]
    end
    
    subgraph "API Layer"
        F[FastAPI Application]
        A[Authentication]
        V[Validation]
    end
    
    subgraph "Business Logic Layer"
        JS[Job Service]
        S[Scheduler Engine]
        V2[Validation Layer]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL)]
        R[(Redis)]
    end
    
    subgraph "Background Processing"
        W[Celery Workers]
        B[Celery Beat]
        F2[Flower Monitoring]
    end
    
    subgraph "Code Execution"
        PY[Python Code]
        SH[Shell Scripts]
        NC[Number Crunching]
    end
    
    C --> F
    API --> F
    F --> A
    F --> V
    F --> JS
    JS --> S
    JS --> V2
    JS --> DB
    S --> R
    B --> R
    W --> R
    W --> DB
    W --> PY
    W --> SH
    W --> NC
    F2 --> R
`

##  Technologies Used

### Core Framework
- **FastAPI**: Modern, fast web framework for building APIs
- **Pydantic**: Data validation and settings management
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migration management

### Background Processing
- **Celery**: Distributed task queue
- **Redis**: Message broker and result backend
- **Flower**: Celery monitoring tool

### Database
- **PostgreSQL**: Primary database for job storage
- **AsyncPG**: Asynchronous PostgreSQL driver

### Scheduling
- **Croniter**: Cron expression parsing and calculation
- **Pytz**: Timezone handling

### Code Execution
- **Python**: Native Python code execution
- **NumPy**: Scientific computing for number crunching
- **Subprocess**: Shell script execution
- **Tempfile**: Secure temporary file handling

### Development & Testing
- **Pytest**: Testing framework
- **HTTPX**: Async HTTP client for testing
- **Black**: Code formatting
- **isort**: Import sorting
- **Flake8**: Linting
- **MyPy**: Type checking

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **GitHub Actions**: CI/CD pipeline

##  Prerequisites

Before setting up the Scheduler Service, ensure you have the following installed:

- **Docker** (version 20.10+)
- **Docker Compose** (version 2.0+)
- **Python** (version 3.11+) - for local development
- **Git** - for cloning the repository

##  Installation Guide

### Quick Setup (Recommended)

1. **Clone the repository**
   `ash
   git clone <repository-url>
   cd SchedulerService
   `

2. **Start all services**
   `ash
   docker-compose up -d
   `

3. **Wait for services to be ready** (about 30 seconds)

4. **Verify installation**
   `ash
   # Check API health
   curl http://localhost:8000/health
   
   # Check Flower monitoring
   curl http://localhost:5555
   `

5. **Access the services**
   - **API Documentation**: http://localhost:8000/docs
   - **Flower Monitoring**: http://localhost:5555
   - **API Health**: http://localhost:8000/health

### Manual Setup

1. **Clone and navigate to repository**
   `ash
   git clone <repository-url>
   cd SchedulerService
   `

2. **Create virtual environment**
   `ash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   `

3. **Install dependencies**
   `ash
   pip install -r requirements.txt
   `

4. **Set up environment variables**
   `ash
   cp .env.example .env
   # Edit .env with your configuration
   `

5. **Start PostgreSQL and Redis**
   `ash
   # Using Docker
   docker run -d --name postgres -e POSTGRES_DB=scheduler_db -e POSTGRES_USER=scheduler -e POSTGRES_PASSWORD=scheduler -p 5432:5432 postgres:15-alpine
   docker run -d --name redis -p 6379:6379 redis:7-alpine
   `

6. **Run database migrations**
   `ash
   alembic upgrade head
   `

7. **Start the services**
   `ash
   # Terminal 1: Start API
   uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload
   
   # Terminal 2: Start Celery Worker
   celery -A src.app.celery_app worker --loglevel=info
   
   # Terminal 3: Start Celery Beat
   celery -A src.app.celery_app beat --loglevel=info
   
   # Terminal 4: Start Flower (optional)
   celery -A src.app.celery_app flower --port=5555
   `

##  Usage Guide

### Job Types Supported

The scheduler supports various job types for different use cases:

#### 1. Python Code Execution
Execute actual Python code with full access to libraries:

`json
{
  "name": "Data Analysis Job",
  "schedule_expr": "0 2 * * *",
  "timezone": "UTC",
  "payload": {
    "type": "python_code",
    "code": "import pandas as pd\nimport numpy as np\n\n# Your analysis code here\ndata = pd.read_csv('data.csv')\nresult = data.describe()\nprint(result)"
  }
}
`

#### 2. Number Crunching Operations
Built-in mathematical operations:

`json
{
  "name": "Fibonacci Calculator",
  "schedule_expr": "*/5 * * * *",
  "timezone": "UTC",
  "payload": {
    "type": "number_crunching",
    "operation": "fibonacci",
    "n": 100
  }
}
`

#### 3. Shell Script Execution
Execute shell commands and scripts:

`json
{
  "name": "System Backup",
  "schedule_expr": "0 3 * * *",
  "timezone": "UTC",
  "payload": {
    "type": "shell_script",
    "script": "#!/bin/bash\ntar -czf /backup/data-backup.tar.gz /data"
  }
}
`

### Setting Up a Job

1. **Create a Python code execution job**
   `ash
   curl -X POST "http://localhost:8000/api/v1/jobs" \
     -H "X-API-Key: your-secret-api-key-here" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Mathematical Analysis",
       "schedule_expr": "*/10 * * * *",
       "timezone": "UTC",
       "payload": {
         "type": "python_code",
         "code": "import math\nimport numpy as np\n\n# Calculate complex mathematical operations\nresult = np.sum([i**2 for i in range(1000)])\nprint(f\"Sum of squares: {result}\")\n\n# Calculate pi using Monte Carlo method\npoints = np.random.random((10000, 2))\ndistances = np.sqrt(points[:,0]**2 + points[:,1]**2)\npi_estimate = 4 * np.sum(distances <= 1) / len(distances)\nprint(f\"Pi estimate: {pi_estimate}\")"
       },
       "retry_policy": {
         "max_retries": 3,
         "retry_delay": 60
       },
       "owner_id": "math_team"
     }'
   `

2. **Create a number crunching job**
   `ash
   curl -X POST "http://localhost:8000/api/v1/jobs" \
     -H "X-API-Key: your-secret-api-key-here" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Prime Number Calculator",
       "schedule_expr": "0 */6 * * *",
       "timezone": "UTC",
       "payload": {
         "type": "number_crunching",
         "operation": "prime_numbers",
         "limit": 10000
       },
       "retry_policy": {
         "max_retries": 2,
         "retry_delay": 30
       },
       "owner_id": "math_team"
     }'
   `

3. **List all jobs**
   `ash
   curl -X GET "http://localhost:8000/api/v1/jobs" \
     -H "X-API-Key: your-secret-api-key-here"
   `

4. **Get job details**
   `ash
   curl -X GET "http://localhost:8000/api/v1/jobs/{job_id}" \
     -H "X-API-Key: your-secret-api-key-here"
   `

5. **Run job immediately**
   `ash
   curl -X POST "http://localhost:8000/api/v1/jobs/{job_id}/run" \
     -H "X-API-Key: your-secret-api-key-here"
   `

6. **Check job execution history**
   `ash
   curl -X GET "http://localhost:8000/api/v1/jobs/{job_id}/runs" \
     -H "X-API-Key: your-secret-api-key-here"
   `

### Example: Advanced Number Crunching Job

Let's create a comprehensive number crunching job that performs multiple mathematical operations:

1. **Create an advanced mathematical analysis job**
   `ash
   curl -X POST "http://localhost:8000/api/v1/jobs" \
     -H "X-API-Key: your-secret-api-key-here" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Advanced Mathematical Analysis",
       "schedule_expr": "*/15 * * * *",
       "timezone": "UTC",
       "payload": {
         "type": "python_code",
         "code": "import numpy as np\nimport math\nfrom datetime import datetime\n\nprint(f\"Starting analysis at {datetime.now()}\")\n\n# Generate large dataset\nnp.random.seed(42)\ndata = np.random.normal(100, 15, 100000)\n\n# Statistical analysis\nmean_val = np.mean(data)\nstd_val = np.std(data)\nmedian_val = np.median(data)\n\nprint(f\"Dataset size: {len(data)}\")\nprint(f\"Mean: {mean_val:.4f}\")\nprint(f\"Standard Deviation: {std_val:.4f}\")\nprint(f\"Median: {median_val:.4f}\")\n\n# Matrix operations\nmatrix_size = 100\nA = np.random.rand(matrix_size, matrix_size)\nB = np.random.rand(matrix_size, matrix_size)\nC = np.dot(A, B)\n\nprint(f\"Matrix multiplication ({matrix_size}x{matrix_size}):\")\nprint(f\"Sum of result matrix: {np.sum(C):.4f}\")\nprint(f\"Largest eigenvalue: {np.max(np.linalg.eigvals(C)):.4f}\")\n\n# Prime number calculation\ndef is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(math.sqrt(n)) + 1):\n        if n % i == 0:\n            return False\n    return True\n\nprimes = [i for i in range(2, 1000) if is_prime(i)]\nprint(f\"Found {len(primes)} prime numbers up to 1000\")\nprint(f\"Largest prime found: {max(primes)}\")\n\nprint(f\"Analysis completed at {datetime.now()}\")"
       },
       "retry_policy": {
         "max_retries": 2,
         "retry_delay": 120
       },
       "owner_id": "research_team"
     }'
   `

2. **Wait for execution** (15 minutes for the first run)

3. **Check job runs to validate execution**
   `ash
   curl -X GET "http://localhost:8000/api/v1/jobs/{job_id}/runs" \
     -H "X-API-Key: your-secret-api-key-here"
   `

4. **Expected response with real execution results**
   `json
   {
     "runs": [
       {
         "id": 1,
         "job_id": 1,
         "status": "success",
         "started_at": "2024-01-15T10:30:00",
         "finished_at": "2024-01-15T10:30:05",
         "logs": "Starting analysis at 2024-01-15 10:30:00.123456\nDataset size: 100000\nMean: 99.9876\nStandard Deviation: 14.9876\nMedian: 99.9876\nMatrix multiplication (100x100):\nSum of result matrix: 5000.1234\nLargest eigenvalue: 50.1234\nFound 168 prime numbers up to 1000\nLargest prime found: 997\nAnalysis completed at 2024-01-15 10:30:05.123456",
         "retry_count": 0
       }
     ],
     "total": 1,
     "page": 1,
     "size": 10
   }
   `

5. **Monitor in Flower**
   - Visit http://localhost:5555
   - Check the "Tasks" tab to see execution details
   - Monitor worker performance in the "Workers" tab

##  Design Patterns Used

### SOLID Principles Implementation

1. **Single Responsibility Principle (SRP)**
   - JobService: Handles only job-related business logic
   - Scheduler: Manages only scheduling calculations
   - JobRun: Represents only job execution data

2. **Open/Closed Principle (OCP)**
   - Job execution strategies can be extended without modifying existing code
   - New schedule types can be added through the Strategy pattern

3. **Liskov Substitution Principle (LSP)**
   - All job execution strategies implement the same interface
   - Different database backends can be swapped seamlessly

4. **Interface Segregation Principle (ISP)**
   - Separate interfaces for job management, scheduling, and execution
   - Clients only depend on methods they actually use

5. **Dependency Inversion Principle (DIP)**
   - High-level modules depend on abstractions, not concretions
   - Database and external service dependencies are injected

### Design Patterns

1. **Strategy Pattern**
   - Different job execution strategies (Python code, shell scripts, number crunching)
   - Different scheduling strategies (cron, datetime, interval)

2. **Repository Pattern**
   - JobService acts as a repository for job operations
   - Abstracts database access from business logic

3. **Factory Pattern**
   - Job creation with different configurations
   - Database session factory

4. **Observer Pattern**
   - Job execution monitoring and logging
   - Event-driven architecture for job state changes

5. **Template Method Pattern**
   - Common job execution flow with customizable steps
   - Retry logic implementation

6. **Dependency Injection**
   - Services injected into API endpoints
   - Database sessions injected into services

##  Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | postgresql+asyncpg://scheduler:scheduler@localhost:5432/scheduler_db |
| REDIS_URL | Redis connection string | edis://localhost:6379/0 |
| API_KEY | API authentication key | your-secret-api-key-here |
| LOG_LEVEL | Logging level | INFO |
| ENVIRONMENT | Environment (development/production) | development |

### Job Configuration

- **Schedule Expressions**: Support for cron (*/5 * * * *), datetime (2024-12-31T23:59:59Z), and interval (5m, 1h, 30s)
- **Retry Policies**: Configurable max retries, delay, and backoff factor
- **Payload**: JSON data passed to job execution
- **Timezone**: Support for any valid timezone

### Code Execution Security

- **Temporary Files**: Code is executed in secure temporary files
- **Timeouts**: 5-minute timeout for code execution
- **Resource Limits**: Memory and CPU limits can be configured
- **Sandboxing**: Code execution is isolated from the main application

##  Testing

### Run Tests
`ash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api.py
`

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **API Tests**: HTTP endpoint testing
- **Database Tests**: Data persistence testing
- **Code Execution Tests**: Real code execution testing

##  Monitoring

### Health Checks
- **API Health**: GET /health
- **Database Health**: Automatic connection monitoring
- **Redis Health**: Broker connectivity monitoring

### Metrics
- **Job Execution Rate**: Success/failure rates
- **Execution Time**: Average job duration
- **Queue Length**: Pending job count
- **Worker Status**: Active worker count

### Logging
- **Structured Logging**: JSON-formatted logs
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Correlation IDs**: Request tracing across services

##  Deployment

### Docker Deployment
`ash
# Build and start all services
docker-compose up -d --build

# Scale workers
docker-compose up -d --scale worker=3

# View logs
docker-compose logs -f api
`

### Production Considerations
- Use environment-specific configuration
- Set up proper logging aggregation
- Configure monitoring and alerting
- Implement backup strategies
- Set up SSL/TLS termination
- Configure rate limiting
- Implement code execution sandboxing

##  API Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

##  Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

##  License

This project is licensed under the MIT License - see the LICENSE file for details.

##  Support

For support and questions:
- Create an issue in the repository
- Check the API documentation
- Review the logs for error details
- Monitor the Flower dashboard for job status
