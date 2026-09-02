#!/bin/bash

# Vector-KB Test Runner - Run all tests with coverage report
# Usage: ./test.sh

set -e

echo "🧪 Running Vector-KB tests..."

# Check if Docker container is running
if ! docker ps | grep -q akvo-rag-vector-kb-mcp-1; then
    echo "❌ Error: akvo-rag-vector-kb-mcp-1 container is not running"
    echo "💡 Start the development environment first: docker-compose up -d"
    exit 1
fi

# Run test suite with coverage
docker exec akvo-rag-vector-kb-mcp-1 python -m pytest tests/ -v --cov=. --cov-report=term-missing

echo "✅ Vector-KB tests completed!"
