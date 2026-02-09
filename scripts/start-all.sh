#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🚀 MRRPulse Startup Script"
echo "=========================="
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Docker Desktop is installed
if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker Desktop.${NC}"
    exit 1
fi

# Check if Docker Desktop is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Docker Desktop is not running. Starting...${NC}"
    open -a Docker

    # Wait for Docker to start (max 60 seconds)
    echo "   Waiting for Docker to start..."
    count=0
    while ! docker info > /dev/null 2>&1; do
        sleep 2
        count=$((count + 2))
        if [ $count -ge 60 ]; then
            echo -e "${RED}❌ Docker failed to start within 60 seconds${NC}"
            exit 1
        fi
        echo -n "."
    done
    echo ""
    echo -e "${GREEN}✅ Docker Desktop is running${NC}"
else
    echo -e "${GREEN}✅ Docker Desktop is already running${NC}"
fi

echo ""

# Check if docker-compose services are running
echo "📦 Checking services..."
SERVICES_RUNNING=$(docker compose ps --services --filter "status=running" 2>/dev/null | wc -l)

if [ "$SERVICES_RUNNING" -eq 4 ]; then
    echo -e "${GREEN}✅ All services are already running${NC}"
    echo ""
    echo "📊 Service Status:"
    docker compose ps
else
    echo -e "${YELLOW}⚠️  Starting services...${NC}"
    docker compose up -d

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ All services started successfully${NC}"

        # Wait a few seconds for services to be ready
        echo "   Waiting for services to be ready..."
        sleep 5

        echo ""
        echo "📊 Service Status:"
        docker compose ps
    else
        echo -e "${RED}❌ Failed to start services${NC}"
        exit 1
    fi
fi

echo ""
echo "🌐 Services are accessible at:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""

# Check for test user script
if [ -f "backend/scripts/create_test_user.py" ]; then
    echo -e "${YELLOW}ℹ️  To create a test user, run:${NC}"
    echo "   docker compose exec backend python scripts/create_test_user.py"
    echo ""
fi

echo -e "${GREEN}✨ All systems ready!${NC}"
