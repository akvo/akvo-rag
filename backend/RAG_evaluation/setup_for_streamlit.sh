#!/bin/bash
# Set up the environment for RAG evaluation with Streamlit

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

# Stop any running containers
echo "Stopping any running containers..."
docker compose $COMPOSE_FILES down

# Start with the Streamlit override
echo "Starting containers with Streamlit support..."
docker compose $COMPOSE_FILES -f streamlit-override.yml up -d

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
