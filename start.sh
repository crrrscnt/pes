#!/bin/bash

# PES Scan Web Application Startup Script

echo "Starting PES Scan Web Application..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo " docker-compose is not installed. Please install docker-compose and try again."
    exit 1
fi

# Create .env files if they don't exist
if [ ! -f backend/.env ]; then
    echo " Creating backend/.env from template..."
    cp backend/env.example backend/.env
fi

if [ ! -f frontend/.env ]; then
    echo " Creating frontend/.env from template..."
    cp frontend/env.example frontend/.env
fi

# Start services
echo "Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check if services are running
echo "🔍 Checking service health..."

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U pes_user -d pes_db > /dev/null 2>&1; then
    echo "PostgreSQL is ready"
else
    echo "PostgreSQL is not ready"
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "Redis is ready"
else
    echo "Redis is not ready"
fi

# Check Backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "Backend API is ready"
else
    echo "Backend API is not ready"
fi

# Initialize database
echo "🗄️ Initializing database..."
docker-compose exec -T backend python scripts/seed_data.py

echo ""
echo " PES Scan Web Application is ready!"
echo ""
echo " Frontend: http://localhost:5173"
echo " API Docs: http://localhost:8000/docs"
echo " Test Users:"
echo "   - user@test.com / password123 (regular user)"
echo "   - admin@test.com / admin123 (admin user)"
echo ""
echo " To stop the application, run: docker-compose down"
echo ""
