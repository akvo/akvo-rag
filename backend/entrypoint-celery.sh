#!/bin/sh
set -e

# Ensure upload directory exists and permissions are set
UPLOAD_DIR="/mnt/uploads"
mkdir -p $UPLOAD_DIR
chmod 777 $UPLOAD_DIR

PIP_CACHE_DIR="/app/.pip"
MODE=${1:-${CELERY_MODE:-worker}}

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
# Wait for RabbitMQ to be ready ---
# -------------------------------------------
echo "⏳ Waiting for RabbitMQ..."
MAX_RETRIES=30
RETRY_COUNT=0

until timeout 5 bash -c "cat < /dev/null > /dev/tcp/${RABBITMQ_HOST}/${RABBITMQ_PORT:-5672}" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ RabbitMQ not ready after $MAX_RETRIES attempts"
        exit 1
    fi
    echo "   RabbitMQ not ready yet (attempt $RETRY_COUNT/$MAX_RETRIES)..."
    sleep 2
done
echo "✅ RabbitMQ is ready!"

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
echo "Starting Celery in '$MODE' mode..."
if [ "$MODE" = "beat" ]; then
    run_mcp_discovery_manager &
    echo "🚀 Starting Celery Beat..."
    exec celery -A app.celery_app beat \
    --loglevel=INFO
else
    run_mcp_discovery_manager &
    echo "🚀 Starting Celery Worker..."
    # Add concurrency and max-tasks-per-child settings
    exec celery -A app.celery_app worker \
    --loglevel=INFO \
    --concurrency=4 \
    --max-tasks-per-child=1000 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat
fi
