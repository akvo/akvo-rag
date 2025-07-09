#!/bin/bash
# Script to start the RAG evaluation system using a virtual environment

# The streamlit-override.yml is already set up by the rag-evaluate script
# No need to run setup_for_streamlit.sh again, just check if API is running

# Navigate to script's parent directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Load .env from root
if [ -f "$ROOT_DIR/.env" ]; then
  export $(grep -v '^#' "$ROOT_DIR/.env" | xargs)
else
  echo "⚠️ .env file not found at $ROOT_DIR/.env"
fi

# Fallback port if not defined
BACKEND_PORT=${BACKEND_PORT:-8000}

# Check if Akvo RAG is running
echo "Checking if Akvo RAG is running..."
if ! curl -s http://localhost:${BACKEND_PORT}/api/health > /dev/null; then
  echo "Akvo RAG doesn't seem to be running. Please ensure it's running with:"
  echo "cd $(dirname $(dirname $(pwd))) && docker compose -f docker-compose.dev.yml -f streamlit-override.yml up -d"
  exit 1
fi

# Check container name
CONTAINER_NAME=$(docker ps | grep "akvo-rag_backend" | awk '{print $NF}')
if [ -z "$CONTAINER_NAME" ]; then
  CONTAINER_NAME="akvo-rag-backend-1"  # fallback name
fi
echo "Using container: $CONTAINER_NAME"

# Setup virtual environment if needed
echo "Setting up virtual environment..."
docker exec $CONTAINER_NAME bash /app/RAG_evaluation/setup_venv.sh

# Run the evaluation dashboard in the virtual environment
echo "Starting evaluation dashboard in virtual environment..."
docker exec $CONTAINER_NAME bash -c "source /app/RAG_evaluation/venv/bin/activate && python /app/RAG_evaluation/run_evaluation.py $*"