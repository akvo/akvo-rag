#!/bin/bash

# Vector-KB Integration Test Runner - Run live container integration tests
# Usage: ./test-integration.sh

set -e

echo "🧪 Running Vector-KB live integration tests..."

# Check if Docker container is running
if ! docker ps | grep -q akvo-rag-vector-kb-mcp-1; then
    echo "❌ Error: akvo-rag-vector-kb-mcp-1 container is not running"
    echo "💡 Start the development environment first: docker-compose up -d"
    exit 1
fi

# Run integration tests only
docker exec akvo-rag-vector-kb-mcp-1 python -m pytest tests/ -v -k "integration"

echo "✅ Vector-KB integration tests completed!"
