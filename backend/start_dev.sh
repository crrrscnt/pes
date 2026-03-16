#!/bin/bash
# Number of workers (can be changed)
NUM_WORKERS=4

echo "Starting $NUM_WORKERS RQ workers..."
for i in $(seq 1 $NUM_WORKERS); do
  # Run RQ worker in the background
  rq worker pes_queue &
done

# Start FastAPI server
uvicorn app.main:app --reload
