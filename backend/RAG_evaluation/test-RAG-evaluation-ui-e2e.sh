#!/bin/bash

# End-to-End Test Runner for RAG Evaluation UI
# Runs with headed browser on host machine

set -e

echo "RAG Evaluation UI - End-to-End Test"
echo "=================================="

# Check preconditions
if ! curl -s http://localhost:8501 > /dev/null; then
    echo "❌ ERROR: Streamlit not accessible on localhost:8501"
    echo "PRECONDITION: Run './rag-evaluate' from project root first"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY environment variable not set"
    echo "Set with: export OPENAI_API_KEY=your_key"
    exit 1
fi

echo "✓ Streamlit is running on localhost:8501"
echo "✓ OPENAI_API_KEY is set"

# Create virtual environment and install dependencies
VENV_DIR="$(dirname "$0")/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install dependencies in virtual environment
if ! python -c "import playwright" 2>/dev/null; then
    echo "Installing Playwright in virtual environment..."
    pip install playwright python-dotenv pytest pytest-asyncio
    echo "Installing Playwright browsers..."
    playwright install chromium
fi

if ! python -c "import dotenv" 2>/dev/null; then
    echo "Installing python-dotenv in virtual environment..."
    pip install python-dotenv
fi

echo "✓ Dependencies installed in virtual environment"

# Run the headed test
echo ""
echo "🎬 Starting headed browser test..."
echo "   You'll see the browser automation in action!"
echo ""

cd "$(dirname "$0")"
python tests/test_eight_metrics_e2e.py

echo ""
echo "✅ E2E test completed!"