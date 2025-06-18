#!/bin/bash
# Script to run the headless RAG evaluation

# Check if Akvo RAG is running
echo "Checking if Akvo RAG is running..."
if ! curl -s http://localhost:8000/api/health > /dev/null; then
  echo "Akvo RAG doesn't seem to be running. Please ensure it's running with:"
  echo "cd $(dirname $(dirname $(pwd))) && docker compose -f docker-compose.dev.yml up -d"
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

# Run the headless evaluation in the virtual environment
echo "Starting headless evaluation..."
docker exec -e OPENAI_API_KEY="${OPENAI_API_KEY}" $CONTAINER_NAME bash -c "cd /app/RAG_evaluation && source venv/bin/activate && python -c \"
from headless_evaluation import run_headless_evaluation
import json
import sys

# Parse arguments
kb_name = 'Living Income Benchmark Knowledge Base'
openai_model = 'gpt-4o'
output_file = None

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
results = run_headless_evaluation(
    kb_name=kb_name,
    openai_model=openai_model
)

# Output results
if output_file:
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'Results saved to {output_file}')
else:
    print(json.dumps(results, indent=2))
\" $*"