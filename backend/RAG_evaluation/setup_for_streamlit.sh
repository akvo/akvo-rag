#!/bin/bash
# Set up the environment for RAG evaluation with Streamlit

# Check Docker Compose configuration
echo "Using development configuration"
COMPOSE_FILES="-f docker-compose.dev.yml -f streamlit-override.yml"

# Create a temporary override file specifically for Streamlit
cat > streamlit-override.yml << EOL
version: '3'

services:
  backend:
    ports:
      - "8501:8501"  # Expose Streamlit port
      - "8000:8000"  # Ensure API port is exposed
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
  if curl -s http://localhost:8000/api/health > /dev/null; then
    echo "API is accessible at http://localhost:8000/api"
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
