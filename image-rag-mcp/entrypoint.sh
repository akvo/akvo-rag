#!/bin/sh

# exit on error
set -e

echo "Starting application..."
if [ "$ENVIRONMENT" = "development" ]; then
    uvicorn app.main:app --host 0.0.0.0 --port 8600 --proxy-headers --forwarded-allow-ips="*" --reload
else
    uvicorn app.main:app --host 0.0.0.0 --port 8600 --proxy-headers --forwarded-allow-ips="*"
fi
