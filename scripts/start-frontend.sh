#!/bin/bash

# Navigate to frontend directory
cd "$(dirname "$0")/frontend"

# Set environment variables
export NEXT_PUBLIC_API_URL=http://localhost:8000

echo "Starting frontend on http://localhost:3000"
npm run dev
