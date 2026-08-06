#!/bin/bash
set -e

echo "=== Container Starting ==="
echo "PORT=${PORT}"
echo "RAILWAY_PUBLIC_DOMAIN=${RAILWAY_PUBLIC_DOMAIN}"
echo "Python version: $(python3 --version)"

# Ensure data directory exists
mkdir -p /app/data
echo "Data directory ready"

# Start gunicorn
echo "Starting gunicorn on port ${PORT:-5000}..."
exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --timeout 120 --access-logfile - --error-logfile - app:app