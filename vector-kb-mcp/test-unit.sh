#!/bin/bash

# Vector-KB Unit Test Runner - Run isolated unit tests only
# Usage: ./test-unit.sh

set -e

echo "🧪 Running Vector-KB unit tests..."

# Check if Docker container is running
if ! docker ps | grep -q akvo-rag-vector-kb-mcp-1; then
    echo "❌ Error: akvo-rag-vector-kb-mcp-1 container is not running"
    echo "💡 Start the development environment first: docker-compose up -d"
    exit 1
fi

# Run unit tests only
docker exec akvo-rag-vector-kb-mcp-1 python -m pytest tests/ -v -k "not integration"

echo "✅ Vector-KB unit tests completed!"
