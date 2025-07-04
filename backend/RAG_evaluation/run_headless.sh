#!/bin/bash
# Script to run the headless RAG evaluation
#
# Usage: ./run_headless.sh [options]
# Options:
#   -u USERNAME    Username for authentication (default: admin@example.com)
#   -p PASSWORD    Password for authentication (default: password)
#   -a API_URL     RAG API URL (default: http://localhost:8000)
#   -k KB_NAME     Knowledge base name (default: Living Income Benchmark Knowledge Base)
#   -c CSV_FILE    CSV file with 'prompt' column (optional, uses default prompts if not provided)

# Default values
USERNAME="admin@example.com"
PASSWORD="password"
RAG_API_URL="http://localhost:8000"
KB_NAME="Living Income Benchmark Knowledge Base"
CSV_FILE=""

# Parse command line options
while getopts "u:p:a:k:c:" opt; do
  case $opt in
    u) USERNAME="$OPTARG" ;;
    p) PASSWORD="$OPTARG" ;;
    a) RAG_API_URL="$OPTARG" ;;
    k) KB_NAME="$OPTARG" ;;
    c) CSV_FILE="$OPTARG" ;;
    \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
  esac
done

shift $((OPTIND-1))

# Check if Akvo RAG is running
echo "Checking if Akvo RAG is running at $RAG_API_URL..."
if ! curl -s "${RAG_API_URL}/api/health" > /dev/null; then
  echo "Akvo RAG doesn't seem to be running at $RAG_API_URL"
  if [ "$RAG_API_URL" = "http://localhost:8000" ]; then
    echo "Please ensure it's running with:"
    echo "cd $(dirname $(dirname $(pwd))) && docker compose -f docker-compose.dev.yml up -d"
  fi
  exit 1
fi

# Check container name
CONTAINER_NAME=$(docker ps | grep "akvo-rag_backend" | awk '{print $NF}')
if [ -z "$CONTAINER_NAME" ]; then
  CONTAINER_NAME="akvo-rag-backend-1"  # fallback name
fi
echo "Using container: $CONTAINER_NAME"
echo "Using credentials: $USERNAME"

# Setup virtual environment if needed
echo "Setting up virtual environment..."
docker exec $CONTAINER_NAME bash /app/RAG_evaluation/setup_venv.sh

# Run the headless evaluation in the virtual environment
echo "Starting headless evaluation..."
docker exec -e OPENAI_API_KEY="${OPENAI_API_KEY}" -e KB_NAME="$KB_NAME" -e USERNAME="$USERNAME" -e PASSWORD="$PASSWORD" -e RAG_API_URL="$RAG_API_URL" -e CSV_FILE="$CSV_FILE" $CONTAINER_NAME bash -c "cd /app/RAG_evaluation && source venv/bin/activate && python run_headless_evaluation.py $*"