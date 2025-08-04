#!/bin/bash

# Backend Test Watcher - Run tests in watch mode (re-runs on file changes)
# Usage: ./test-watch.sh

set -e

echo "👀 Starting backend test watcher..."

# Check if Docker container is running
if ! docker ps | grep -q akvo-rag-backend-1; then
    echo "❌ Error: akvo-rag-backend-1 container is not running"
    echo "💡 Start the development environment first: docker-compose up -d"
    exit 1
fi

# Install test dependencies and pytest-watch if missing and start watching
docker exec -it akvo-rag-backend-1 bash -c "
    cd /app && 
    (pip list | grep -q pytest || (echo '📦 Installing test dependencies...' && pip install -r requirements-test.txt)) &&
    (pip list | grep -q pytest-watch || (echo '📦 Installing pytest-watch...' && pip install pytest-watch)) &&
    echo '👀 Starting test watcher... (Press Ctrl+C to stop)' &&
    ptw tests/ -- -v --tb=short
"