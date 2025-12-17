#!/bin/sh
set -e

# ===========================================
# Shared filesystem setup
# ===========================================
UPLOAD_DIR="/mnt/uploads"
mkdir -p "$UPLOAD_DIR"
chmod 777 "$UPLOAD_DIR"

PIP_CACHE_DIR="/app/.pip"
MODE=${1:-${CELERY_MODE:-worker}}

# ===========================================
# DEV-ONLY dependency installation
# ===========================================
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
    (echo "Retrying in 5s..." && sleep 5 && pip install -q --cache-dir="$PIP_CACHE_DIR" -r requirements.txt) || \
    (echo "Retrying in 10s..." && sleep 10 && pip install -q --cache-dir="$PIP_CACHE_DIR" -r requirements.txt)
fi

# ===========================================
# Wait for MySQL (required for tasks)
# ===========================================
echo "Waiting for MySQL..."
DB_HOST=${MYSQL_SERVER:-db}
DB_PORT=${MYSQL_PORT:-3306}
while ! nc -z "$DB_HOST" "$DB_PORT"; do
    sleep 1
done
echo "✅ MySQL started"

# ===========================================
# Wait for RabbitMQ
# ===========================================
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

# ===========================================
# MCP Discovery (same guarantees as API entrypoint)
# ===========================================
run_mcp_discovery_manager() {
    echo "🚀 Running MCP discovery manager..."
    echo "⏳ This may take a few moments..."
    
    if python -m mcp_clients.mcp_discovery_manager; then
        echo "✅ MCP discovery manager completed successfully"
        
        if [ -f "mcp_discovery.json" ]; then
            FILE_SIZE=$(stat -f%z "mcp_discovery.json" 2>/dev/null || stat -c%s "mcp_discovery.json" 2>/dev/null || echo "0")
            if [ "$FILE_SIZE" -gt 100 ]; then
                echo "✅ MCP discovery file valid (${FILE_SIZE} bytes)"
                return 0
            else
                echo "⚠️ MCP discovery file too small (${FILE_SIZE} bytes)"
                return 1
            fi
        else
            echo "❌ MCP discovery file not found"
            return 1
        fi
    else
        echo "❌ MCP discovery manager failed"
        return 1
    fi
}

wait_for_mcp_discovery() {
    MAX_ATTEMPTS=3
    ATTEMPT=1
    
    while [ "$ATTEMPT" -le "$MAX_ATTEMPTS" ]; do
        echo "📋 MCP Discovery attempt $ATTEMPT of $MAX_ATTEMPTS"
        if run_mcp_discovery_manager; then
            echo "✅ MCP discovery ready"
            return 0
        fi
        
        if [ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ]; then
            WAIT_TIME=$((ATTEMPT * 10))
            echo "⏳ Waiting ${WAIT_TIME}s before retry..."
            sleep "$WAIT_TIME"
        fi
        ATTEMPT=$((ATTEMPT + 1))
    done
    
    echo "❌ MCP discovery failed after $MAX_ATTEMPTS attempts"
    echo "❌ Celery cannot start without valid MCP discovery data"
    exit 1
}

# ===========================================
# Startup sequence
# ===========================================
echo "=========================================="
echo "🚀 Celery Startup Sequence ($MODE)"
echo "=========================================="

# MCP discovery is BLOCKING for Celery (same as API)
wait_for_mcp_discovery

# ===========================================
# Start Celery
# ===========================================
echo "Starting Celery in '$MODE' mode..."

if [ "$MODE" = "beat" ]; then
    echo "🚀 Starting Celery Beat..."
    exec celery -A app.celery_app beat \
    --loglevel=INFO
else
    echo "🚀 Starting Celery Worker..."
    exec celery -A app.celery_app worker \
    --loglevel=INFO \
    --concurrency=4 \
    --max-tasks-per-child=1000 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat
fi
