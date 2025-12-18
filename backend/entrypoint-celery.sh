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
# Wait for MySQL (tasks depend on DB)
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
echo "✅ RabbitMQ is ready"

# ===========================================
# MCP Discovery (BLOCKING, authoritative)
# ===========================================
ALLOW_FALLBACK=${MCP_DISCOVERY_ALLOW_FALLBACK:-true}

echo "Running MCP discovery (allow_fallback=$ALLOW_FALLBACK)..."

python -m mcp_clients.mcp_discovery_manager \
$( [ "$ALLOW_FALLBACK" = "true" ] && echo "--allow-fallback" )

echo "✅ MCP discovery ready"

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
