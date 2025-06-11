#!/bin/bash
# Simple script to start the RAG evaluation system

# Check if Akvo RAG is running
echo "Checking if Akvo RAG is running..."
if ! curl -s http://localhost:8000/api/health > /dev/null; then
  echo "Akvo RAG doesn't seem to be running. Please start it with 'docker compose up -d'"
  exit 1
fi

# Check if override file is in place
if [ ! -f "../../docker-compose.override.yml" ]; then
  echo "Copying Docker override file to expose Streamlit port..."
  cp docker-compose.override.yml ../../
  
  echo "Restarting containers with override..."
  cd ../../
  docker compose down
  docker compose up -d
  cd - > /dev/null
fi

# Install dependencies if needed
echo "Installing dependencies..."
docker exec -it akvo-rag-backend pip install -r /app/RAG_evaluation/requirements.txt

# Run the evaluation dashboard
echo "Starting evaluation dashboard..."
docker exec -it akvo-rag-backend python /app/RAG_evaluation/run_evaluation.py "$@"