@echo off
REM Scheduler Service Startup Script for Windows

echo  Starting Scheduler Service...
echo =================================

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo  Docker is not running. Please start Docker and try again.
    pause
    exit /b 1
)

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  docker-compose is not installed. Please install docker-compose and try again.
    pause
    exit /b 1
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo  Creating .env file from template...
    copy .env.example .env
    echo  .env file created. You can edit it if needed.
)

REM Start services
echo  Starting Docker services...
docker-compose up -d

REM Wait for services to be ready
echo  Waiting for services to be ready...
timeout /t 30 /nobreak >nul

REM Check service health
echo  Checking service health...

REM Check API health
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo  API is healthy
) else (
    echo  API is not responding
    echo  Checking logs...
    docker-compose logs api
    pause
    exit /b 1
)

echo.
echo  Scheduler Service is ready!
echo =================================
echo  API Documentation: http://localhost:8000/docs
echo  Health Check: http://localhost:8000/health
echo  Service Status: docker-compose ps
echo  View Logs: docker-compose logs -f
echo.
echo  To run the demo:
echo    python demo.py
echo.
echo  To stop the service:
echo    docker-compose down
echo.
pause
