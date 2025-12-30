#!/bin/bash

# Navigate to script directory
cd "$(dirname "$0")"

echo "Starting SwapList App..."

# Check for node_modules
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

# Start Backend (Background)
# Using uv to run in managed environment
echo "Starting Backend on port 8000..."
uv run -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Start Frontend (Background)
echo "Starting Frontend on port 5173..."
cd frontend
npm run dev -- --host &
FRONTEND_PID=$!

# Cleanup on exit
trap "echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM EXIT

# Wait
wait
