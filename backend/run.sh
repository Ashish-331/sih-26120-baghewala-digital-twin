#!/bin/bash
source venv/bin/activate

# Start API server in background
python main.py &
API_PID=$!

echo "Waiting for API server to start..."
sleep 3

# Start simulator
python simulator.py &
SIM_PID=$!

echo "Backend services are running."
echo "API Server PID: $API_PID"
echo "Simulator PID: $SIM_PID"

# Handle graceful shutdown
trap "kill $API_PID $SIM_PID; exit" SIGINT SIGTERM

# Wait for both processes
wait $API_PID
wait $SIM_PID
