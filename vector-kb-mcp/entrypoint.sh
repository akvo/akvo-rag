#!/bin/sh
set -e

# ===========================================
# DEV-ONLY dependency installation
# ===========================================
PIP_CACHE_DIR="/app/.pip"
if [ "$ENVIRONMENT" = "development" ]; then
    echo "Installing Python dependencies for vector-kb-mcp..."
    mkdir -p "$PIP_CACHE_DIR"
    pip install -q --upgrade pip
    pip install -q --cache-dir="$PIP_CACHE_DIR" -r requirements.txt || \
    (echo "Retrying in 5s..." && sleep 5 && pip install -q --cache-dir="$PIP_CACHE_DIR" -r requirements.txt) || \
    (echo "Retrying in 10s..." && sleep 10 && pip install -q --cache-dir="$PIP_CACHE_DIR" -r requirements.txt)
fi

if [ "$ENVIRONMENT" = "development" ]; then
    echo "🚀 Starting vector-kb-mcp in development mode with auto-reload..."
    exec watchfiles --filter python "python main.py" /app --ignore-paths "/app/.pip,/app/tests,/app/.pytest_cache"
else
    echo "🚀 Starting vector-kb-mcp in production mode..."
    exec python main.py
fi
