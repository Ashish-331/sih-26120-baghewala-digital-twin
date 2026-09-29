#!/bin/bash
set -e

# Change directory to backend script directory
cd "$(dirname "$0")"

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Fix #11: Ensure model exists before simulator starts
MODEL_FILE="../ml/dynacard_rf_classifier.pkl"
if [ ! -f "$MODEL_FILE" ]; then
    echo "[SETUP] ML model missing at $MODEL_FILE. Training 5-class Random Forest..."
    python ../ml/train_classifier.py
fi

# Fix #17: Process management cleanly trap signals and use process group
export PYTHONUNBUFFERED=1

# Start API server in background
python main.py &
API_PID=$!

echo "Waiting for API server to start..."
sleep 2

# Start simulator
python simulator.py &
SIM_PID=$!

echo "Backend services are running."
echo "API Server PID: $API_PID"
echo "Simulator PID: $SIM_PID"

# Handle graceful shutdown of both child processes
trap "kill -TERM $API_PID $SIM_PID 2>/dev/null || true; exit 0" SIGINT SIGTERM EXIT

wait $API_PID
wait $SIM_PID
