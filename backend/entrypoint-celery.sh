#!/bin/sh
set -e

PIP_CACHE_DIR="/app/.pip"

# -------------------------------------------
# Environment setup (same as backend)
# -------------------------------------------
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
fi
# -------------------------------------------

# -------------------------------------------
# Wait for MySQL (needed for DB access in tasks)
# -------------------------------------------
echo "Waiting for MySQL..."
DB_HOST=${MYSQL_SERVER:-db}
DB_PORT=${MYSQL_PORT:-3306}
while ! nc -z $DB_HOST $DB_PORT; do
    sleep 1
done
echo "✅ MySQL started"

# -------------------------------------------
# Start Celery worker
# -------------------------------------------
echo "🚀 Starting Celery worker..."
celery -A app.celery_app.celery_app worker --loglevel=info
