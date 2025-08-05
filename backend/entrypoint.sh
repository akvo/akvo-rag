#!/bin/sh

# exit on error
set -e

echo "Waiting for MySQL..."
DB_HOST=${MYSQL_SERVER:-db}
DB_PORT=${MYSQL_PORT:-3306}
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "MySQL started"

echo "Running migrations..."
if alembic upgrade head; then
  echo "Migrations completed successfully"
else
  echo "Migration failed"
  exit 1
fi

echo "Starting application..."
if [ "$ENVIRONMENT" = "development" ]; then
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*" --reload
else
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"
fi
