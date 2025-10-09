#!/bin/sh
set -e

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
# Function to safely run MCP discovery
# -------------------------------------------
run_mcp_discovery_manager() {
    echo "🚀 Running MCP discovery manager..."
    if ! python mcp_clients/mcp_discovery_manager.py; then
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
    echo "Installing dev dependencies..."
    pip install --no-cache-dir -r requirements.txt

    echo "Starting application in development mode..."
    uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --proxy-headers \
        --forwarded-allow-ips="*" \
        --reload &

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
