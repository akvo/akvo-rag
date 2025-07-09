#!/bin/bash
# Set up the environment for RAG evaluation with Streamlit

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

# Check Docker Compose configuration
echo "Using development configuration"
COMPOSE_FILES="-f docker-compose.dev.yml -f streamlit-override.yml"

# Create a temporary override file specifically for Streamlit
cat > streamlit-override.yml << EOL
services:
  backend:
    ports:
      - "8501:8501"  # Expose Streamlit port
      - "${BACKEND_PORT}:8000"  # Ensure API port is exposed
EOL

echo "Created temporary Streamlit override configuration"

# Check if containers are already running with correct configuration
if docker compose $COMPOSE_FILES ps | grep -q "Up"; then
    echo "Containers already running, checking if restart is needed..."
    # Only restart if the override file changed or containers aren't healthy
    if ! docker compose $COMPOSE_FILES -f streamlit-override.yml ps | grep -q "Up.*healthy\|Up.*running"; then
        echo "Restarting containers with Streamlit support..."
        docker compose $COMPOSE_FILES stop
        docker compose $COMPOSE_FILES -f streamlit-override.yml up -d
    else
        echo "Containers already running with correct configuration"
    fi
else
    echo "Starting containers with Streamlit support..."
    docker compose $COMPOSE_FILES -f streamlit-override.yml up -d
fi

# Check if backend is accessible
echo "Checking if API is accessible..."
for i in {1..10}; do
  if curl -s http://localhost:${BACKEND_PORT}/api/health > /dev/null; then
    echo "API is accessible at http://localhost:${BACKEND_PORT}/api"
    break
  fi
  echo "Waiting for API to become available... ($i/10)"
  sleep 5
  if [ $i -eq 10 ]; then
    echo "Warning: API not responding. You may need to check your Docker configuration."
  fi
done

echo "Streamlit will be accessible at http://localhost:8501"
echo "Setup complete!"
