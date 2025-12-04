#!/bin/sh
set -e

# Ensure upload directory exists and permissions are set
UPLOAD_DIR="/mnt/uploads"
mkdir -p $UPLOAD_DIR
chmod 777 $UPLOAD_DIR

PIP_CACHE_DIR="/app/.pip"

# -------------------------------------------
# Environment setup (shared for both modes)
# -------------------------------------------
if [ "$ENVIRONMENT" = "development" ]; then
    echo "Installing system dependencies..."
    apt-get update -qq && apt-get install -y -qq \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    netcat-traditional
    
    echo "Installing Python dependencies..."
    mkdir -p "$PIP_CACHE_DIR"
    pip install -q --upgrade pip
    pip install -q --cache-dir="$PIP_CACHE_DIR" -r requirements.txt || \
    (echo "Retrying in 5s..." && sleep 5 && pip install -q --cache-dir="$PIP_CACHE_DIR" -r requirements.txt)
fi
# -------------------------------------------

# -------------------------------------------
# Wait for MySQL (needed for tasks)
# -------------------------------------------
echo "Waiting for MySQL..."
DB_HOST=${MYSQL_SERVER:-db}
DB_PORT=${MYSQL_PORT:-3306}

while ! nc -z $DB_HOST $DB_PORT; do
    sleep 1
done
echo "MySQL started"

# -------------------------------------------
# Function to safely run MCP discovery
# -------------------------------------------
run_mcp_discovery_manager() {
    echo "🚀 Running MCP discovery manager..."
    if ! python -m mcp_clients.mcp_discovery_manager; then
        echo "⚠️ MCP discovery manager failed, continuing startup..."
    else
        echo "✅ MCP discovery manager finished successfully"
    fi
}

# -------------------------------------------
# Decide what to run
# -------------------------------------------
if [ "$CELERY_MODE" = "beat" ]; then
    run_mcp_discovery_manager &
    echo "🚀 Starting Celery Beat..."
    exec celery -A app.celery_app.celery_app beat --loglevel=info
else
    run_mcp_discovery_manager &
    echo "🚀 Starting Celery Worker..."
    exec celery -A app.celery_app.celery_app worker --loglevel=info
fi
