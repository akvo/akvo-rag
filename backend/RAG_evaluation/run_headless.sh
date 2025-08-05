#!/bin/bash
# Script to run the headless RAG evaluation
#
# Usage: ./run_headless.sh [options]
# Options:
#   -u USERNAME                 Username for authentication (default: admin@example.com)
#   -p PASSWORD                 Password for authentication (default: password)
#   -a API_URL                  RAG API URL (default: http://localhost:8000)
#   -k KB_NAME                  Knowledge base name (default: Living Income Benchmark Knowledge Base)
#   -c CSV_FILE                 CSV file with 'prompt' column (optional)
#   -o OUTPUT                   CSV output file path (optional, saves to output/ by default)
#   -m METRICS_MODE             Metrics mode: basic (4), full (8), reference-only (4) (default: full)
#   --docker-host-gateway       Replace localhost with host.docker.internal (for Mac users etc.)

# Navigate to script's parent directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Load .env from root
if [ -f "$ROOT_DIR/.env" ]; then
    set -a  # automatically export all variables
    source <(grep -v '^#' "$ROOT_DIR/.env" | grep -v '^$' | sed 's/^/export /')
    set +a  # disable automatic export
else
    echo "⚠️ .env file not found at $ROOT_DIR/.env"
fi

# Fallback port if not defined
BACKEND_PORT=${BACKEND_PORT:-8000}

# Default values
USERNAME=${RAG_USERNAME:-"admin@example.com"}
PASSWORD=${RAG_PASSWORD:-"password"}
RAG_API_URL="http://localhost:${BACKEND_PORT}"
KB_NAME="Living Income Benchmark Knowledge Base"
CSV_FILE=""
OUTPUT_FILE=""
METRICS_MODE="full"
USE_DOCKER_HOST_GATEWAY=false

# First, manually check for long option --docker-host-gateway
for arg in "$@"; do
    if [[ "$arg" == "--docker-host-gateway" ]]; then
        USE_DOCKER_HOST_GATEWAY=true
        # Remove from arguments to avoid conflict with getopts
        set -- "${@/--docker-host-gateway/}"
        break
    fi
done

# Parse short options
while getopts "u:p:a:k:c:o:m:" opt; do
    case $opt in
        u) USERNAME="$OPTARG" ;;
        p) PASSWORD="$OPTARG" ;;
        a) RAG_API_URL="$OPTARG" ;;
        k) KB_NAME="$OPTARG" ;;
        c) CSV_FILE="$OPTARG" ;;
        o) OUTPUT_FILE="$OPTARG" ;;
        m) METRICS_MODE="$OPTARG" ;;
        \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
    esac
done

shift $((OPTIND-1))

# Validate metrics mode
case "$METRICS_MODE" in
    "basic"|"full"|"reference-only")
        echo "📊 Using metrics mode: $METRICS_MODE"
        ;;
    *)
        echo "❌ Invalid metrics mode: $METRICS_MODE"
        echo "Valid options: basic, full, reference-only"
        exit 1
        ;;
esac

# Check if Akvo RAG is running
echo "Checking if Akvo RAG is running at $RAG_API_URL..."
if ! curl -s "${RAG_API_URL}/api/health" > /dev/null; then
    echo "❌ Akvo RAG doesn't seem to be running at $RAG_API_URL"
    if [[ "$RAG_API_URL" == "http://localhost:${BACKEND_PORT}" ]]; then
        echo "💡 Try running:"
        echo "cd $(dirname $(dirname $(pwd))) && docker compose -f docker-compose.dev.yml up -d"
    fi
    exit 1
fi

# Check container name
CONTAINER_NAME=$(docker ps | grep "akvo-rag_backend" | awk '{print $NF}')
if [ -z "$CONTAINER_NAME" ]; then
    CONTAINER_NAME="akvo-rag-backend-1"
fi

# Adjust for Docker if needed
if $USE_DOCKER_HOST_GATEWAY && [[ "$RAG_API_URL" == *"localhost"* ]]; then
    RAG_API_URL_FOR_CONTAINER="${RAG_API_URL//localhost/host.docker.internal}"
    echo "🔁 Rewriting API URL for Docker: $RAG_API_URL → $RAG_API_URL_FOR_CONTAINER"
else
    RAG_API_URL_FOR_CONTAINER="$RAG_API_URL"
fi

echo "✅ Using container: $CONTAINER_NAME"
echo "👤 Using credentials: $USERNAME"
echo "🌐 API URL (host): $RAG_API_URL"
echo "🌐 API URL (container): $RAG_API_URL_FOR_CONTAINER"
if [[ -n "$OUTPUT_FILE" ]]; then
    echo "📄 CSV output: $OUTPUT_FILE"
fi

# Setup virtual environment
echo "⚙️ Setting up virtual environment..."
docker exec $CONTAINER_NAME bash /app/RAG_evaluation/setup_venv.sh

# Run headless evaluation
echo "🚀 Starting headless evaluation..."
docker exec \
    -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
    -e KB_NAME="$KB_NAME" \
    -e USERNAME="$USERNAME" \
    -e PASSWORD="$PASSWORD" \
    -e RAG_API_URL="$RAG_API_URL_FOR_CONTAINER" \
    -e CSV_FILE="$CSV_FILE" \
    -e OUTPUT_FILE="$OUTPUT_FILE" \
    -e METRICS_MODE="$METRICS_MODE" \
    $CONTAINER_NAME bash -c "cd /app/RAG_evaluation && source venv/bin/activate && python run_headless_evaluation.py $*"
