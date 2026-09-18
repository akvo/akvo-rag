#!/bin/bash

# Backend Test Runner - Run all tests
# Usage: ./test.sh

set -e

echo "🧪 Running backend tests..."

# Check if Docker container is running
if ! docker ps | grep -q akvo-rag-backend-1; then
    echo "❌ Error: akvo-rag-backend-1 container is not running"
    echo "💡 Start the development environment first: docker-compose up -d"
    exit 1
fi

# Install test dependencies if missing and run tests
docker exec akvo-rag-backend-1 bash -c "
    cd /app && 
    (pip list | grep -q pytest-cov || (echo '📦 Installing test dependencies...' && pip install -r requirements-test.txt)) &&
    echo '🚀 Running all tests with coverage...' &&
    python -m pytest tests/ -v --cov=app --cov=mcp_clients --cov-report=term-missing
"

echo "✅ Tests completed!"