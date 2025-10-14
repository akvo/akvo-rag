#!/bin/sh
set -e

# -------------------------------------------
# FOR DEV ONLY: Install dependencies once
# -------------------------------------------
PIP_CACHE_DIR="/app/.pip"

if [ "$ENVIRONMENT" = "development" ]; then
    echo "Installing system dependencies..."
    apt-get update -qq && apt-get install -y -qq \
        build-essential \
        default-libmysqlclient-dev \
        pkg-config \
        netcat-traditional

    echo "⏳ Installing Python dependencies..."
    mkdir -p "$PIP_CACHE_DIR"
    pip install -q --upgrade pip
    pip install -q --cache-dir="$PIP_CACHE_DIR" -r requirements.txt || \
        (echo "Retrying in 5s..." && sleep 5 && pip install -q --cache-dir="$PIP_CACHE_DIR" -r requirements.txt) || \
        (echo "Retrying in 10s..." && sleep 10 && pip install -q --cache-dir="$PIP_CACHE_DIR" -r requirements.txt)

    # Ensure uploads folder exists
    mkdir -p /app/uploads
fi
# -------------------------------------------

echo "Waiting for MySQL..."
DB_HOST=${MYSQL_SERVER:-db}
DB_PORT=${MYSQL_PORT:-3306}
while ! nc -z $DB_HOST $DB_PORT; do
    sleep 1
done
echo "✅ MySQL started"

echo "Running migrations..."
if alembic upgrade head; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed"
    exit 1
fi

# -------------------------------------------
# Function to safely run Seed Prompt
# -------------------------------------------
run_initial_prompt_seeder() {
    echo "🚀 Running MCP discovery manager..."
    if ! python -m app.seeder.seed_prompts; then
        echo "⚠️ Initial prompt seeder failed, continuing startup..."
    else
        echo "✅ Initial prompt seeder finished successfully"
    fi
}

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
# Start FastAPI and MCP discovery
# -------------------------------------------
echo "Starting application..."

if [ "$ENVIRONMENT" = "development" ]; then
    echo "Starting application in development mode..."
    uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --proxy-headers \
        --forwarded-allow-ips="*" \
        --reload &

    # Run initial prompt seeder once at startup
    run_initial_prompt_seeder &

    # Run MCP discovery after API is up
    run_mcp_discovery_manager &

    # Keep both processes running
    wait
else
    echo "Starting application in production mode..."
    uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --proxy-headers \
        --forwarded-allow-ips="*" &

    # Run MCP discovery after API is up
    run_mcp_discovery_manager &

    # Wait for both background processes
    wait
fi
