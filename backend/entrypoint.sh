#!/bin/sh
set -e

# ===========================================
# Filesystem setup
# ===========================================
UPLOAD_DIR="/mnt/uploads"
mkdir -p "$UPLOAD_DIR"
chmod 777 "$UPLOAD_DIR"

# ===========================================
# DEV-ONLY dependency installation
# ===========================================
PIP_CACHE_DIR="/app/.pip"
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
    
    mkdir -p /app/uploads
fi

# ===========================================
# Wait for MySQL
# ===========================================
echo "Waiting for MySQL..."
DB_HOST=${MYSQL_SERVER:-db}
DB_PORT=${MYSQL_PORT:-3306}

while ! nc -z "$DB_HOST" "$DB_PORT"; do
    sleep 1
done
echo "✅ MySQL started"

# ===========================================
# Run migrations
# ===========================================
echo "Running migrations..."
alembic upgrade head
echo "✅ Migrations completed"

# ===========================================
# Initial prompt seeder (non-blocking)
# ===========================================
echo "Running initial prompt seeder..."
python -m app.seeder.seed_prompts || \
echo "⚠️ Prompt seeder failed, continuing startup"

# ===========================================
# MCP Discovery (BLOCKING, authoritative)
# ===========================================
ALLOW_FALLBACK=${MCP_DISCOVERY_ALLOW_FALLBACK:-true}

echo "Running MCP discovery (allow_fallback=$ALLOW_FALLBACK)..."

python -m mcp_clients.mcp_discovery_manager \
$( [ "$ALLOW_FALLBACK" = "true" ] && echo "--allow-fallback" )

echo "✅ MCP discovery ready"

# ===========================================
# Start FastAPI
# ===========================================
echo "Starting application..."

if [ "$ENVIRONMENT" = "development" ]; then
    echo "🚀 Starting application in development mode..."
    exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips="*" \
    --reload
else
    echo "🚀 Starting application in development mode..."
    exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips="*"
fi
