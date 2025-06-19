#!/bin/bash
# Script to run the headless RAG evaluation
#
# Usage: ./run_headless.sh [options]
# Options:
#   -u USERNAME    Username for authentication (default: admin@example.com)
#   -p PASSWORD    Password for authentication (default: password)
#   -a API_URL     RAG API URL (default: http://localhost:8000)
#   -k KB_NAME     Knowledge base name (default: Living Income Benchmark Knowledge Base)

# Default values
USERNAME="admin@example.com"
PASSWORD="password"
RAG_API_URL="http://localhost:8000"
KB_NAME="Living Income Benchmark Knowledge Base"

# Parse command line options
while getopts "u:p:a:k:" opt; do
  case $opt in
    u) USERNAME="$OPTARG" ;;
    p) PASSWORD="$OPTARG" ;;
    a) RAG_API_URL="$OPTARG" ;;
    k) KB_NAME="$OPTARG" ;;
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
docker exec -e OPENAI_API_KEY="${OPENAI_API_KEY}" $CONTAINER_NAME bash -c "cd /app/RAG_evaluation && source venv/bin/activate && python -c \"
from headless_evaluation import run_headless_evaluation
import json
import sys

# Parse arguments
kb_name = '$KB_NAME'
openai_model = 'gpt-4o'
output_file = None
username = '$USERNAME'
password = '$PASSWORD'
rag_api_url = '$RAG_API_URL'

args = sys.argv[1:]
i = 0
while i < len(args):
    if args[i] == '--kb' and i+1 < len(args):
        kb_name = args[i+1]
        i += 2
    elif args[i] == '--openai-model' and i+1 < len(args):
        openai_model = args[i+1]
        i += 2
    elif args[i] == '--output' and i+1 < len(args):
        output_file = args[i+1]
        i += 2
    else:
        i += 1

# Run evaluation
print(f'Running evaluation on knowledge base: {kb_name}')
print(f'Using model: {openai_model}')
print(f'Using credentials: {username}')
print(f'Using API URL: {rag_api_url}')
results = run_headless_evaluation(
    kb_name=kb_name,
    openai_model=openai_model,
    username=username,
    password=password,
    rag_api_url=rag_api_url
)

# Output results
if output_file:
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'Results saved to {output_file}')
else:
    print(json.dumps(results, indent=2))
\" $*"