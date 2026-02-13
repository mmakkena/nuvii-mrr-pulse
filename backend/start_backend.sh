#!/bin/bash
# Kill any process on port 8000
lsof -i :8000 | tail -n +2 | awk '{print $2}' | xargs kill -9 2>/dev/null || true
sleep 2

# Start backend
cd /Users/ravi/otherapps/nuvii-mrr-pulse/backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000 &

# Wait for startup
sleep 8

# Test health endpoint
curl -s http://localhost:8000/health || echo "Backend not ready"
