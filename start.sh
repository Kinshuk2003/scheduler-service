#!/bin/bash

# Scheduler Service Startup Script

echo " Starting Scheduler Service..."
echo "================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo " Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo " docker-compose is not installed. Please install docker-compose and try again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo " Creating .env file from template..."
    cp .env.example .env
    echo " .env file created. You can edit it if needed."
fi

# Start services
echo " Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo " Waiting for services to be ready..."
sleep 30

# Check service health
echo " Checking service health..."

# Check API health
if curl -s http://localhost:8000/health > /dev/null; then
    echo " API is healthy"
else
    echo " API is not responding"
    echo " Checking logs..."
    docker-compose logs api
    exit 1
fi

# Check database
if docker-compose exec -T db pg_isready -U scheduler > /dev/null 2>&1; then
    echo " Database is ready"
else
    echo " Database is not ready"
    exit 1
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo " Redis is ready"
else
    echo " Redis is not ready"
    exit 1
fi

echo ""
echo " Scheduler Service is ready!"
echo "================================="
echo " API Documentation: http://localhost:8000/docs"
echo " Health Check: http://localhost:8000/health"
echo " Service Status: docker-compose ps"
echo " View Logs: docker-compose logs -f"
echo ""
echo " To run the demo:"
echo "   python demo.py"
echo ""
echo " To stop the service:"
echo "   docker-compose down"
echo ""
