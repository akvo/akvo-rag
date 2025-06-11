#!/bin/bash
# Script to start the RAG evaluation system using a virtual environment

# Check if Akvo RAG is running
echo "Checking if Akvo RAG is running..."
if ! curl -s http://localhost:8000/api/health > /dev/null; then
  echo "Akvo RAG doesn't seem to be running. Please start it with 'docker compose up -d'"
  exit 1
fi

# Check container name
CONTAINER_NAME=$(docker ps | grep "akvo-rag_backend" | awk '{print $NF}')
if [ -z "$CONTAINER_NAME" ]; then
  CONTAINER_NAME="akvo-rag-backend-1"  # fallback name
fi
echo "Using container: $CONTAINER_NAME"

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

# Setup virtual environment if needed
echo "Setting up virtual environment..."
docker exec $CONTAINER_NAME bash /app/RAG_evaluation/setup_venv.sh

# Run the evaluation dashboard in the virtual environment
echo "Starting evaluation dashboard in virtual environment..."
docker exec $CONTAINER_NAME bash -c "source /app/RAG_evaluation/venv/bin/activate && python /app/RAG_evaluation/run_evaluation.py $*"