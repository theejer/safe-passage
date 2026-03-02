#!/bin/bash
# SafePassage Backend Docker Entrypoint
# 
# This script:
# 1. Initializes the PostgreSQL database schema (if not already done)
# 2. Waits for database readiness with retry logic
# 3. Starts the Gunicorn WSGI server
#
# Environment variables:
#   PORT: HTTP server port (default: 5000, set by Railway)
#   SQLALCHEMY_DATABASE_URI: PostgreSQL connection string (required)
#   APP_CONFIG: Application configuration (development/production)

set -e

# Configuration
MAX_RETRIES=30
RETRY_DELAY=2
PORT=${PORT:-5000}

# Colors for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Initialize database schema
log_info "Step 1: Initializing database schema..."
if python scripts/init_db.py; then
    log_info "Database initialization completed"
else
    log_warn "Database initialization encountered issues (may be expected on retry)"
fi

# 2. Wait for PostgreSQL readiness
log_info "Step 2: Waiting for PostgreSQL readiness..."
if [ -n "$SQLALCHEMY_DATABASE_URI" ]; then
    RETRY_COUNT=0
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if python -c "
import os
import psycopg2
from urllib.parse import urlparse

try:
    uri = os.getenv('SQLALCHEMY_DATABASE_URI')
    parsed = urlparse(uri)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip('/'),
        user=parsed.username,
        password=parsed.password,
        connect_timeout=3
    )
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    cursor.close()
    conn.close()
    print('Connection successful')
except Exception as e:
    print(f'Connection failed: {e}')
    exit(1)
" 2>/dev/null; then
            log_info "✓ PostgreSQL is ready"
            break
        else
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                log_warn "PostgreSQL not ready yet (attempt $RETRY_COUNT/$MAX_RETRIES), retrying in ${RETRY_DELAY}s..."
                sleep $RETRY_DELAY
            else
                log_error "PostgreSQL failed to become ready after $MAX_RETRIES attempts"
                exit 1
            fi
        fi
    done
else
    log_warn "SQLALCHEMY_DATABASE_URI not set, skipping PostgreSQL readiness check"
fi

# 3. Start Gunicorn
log_info "Step 3: Starting Gunicorn WSGI server..."
log_info "Binding to 0.0.0.0:$PORT"

if [ "$APP_CONFIG" = "production" ]; then
    log_info "Running in production mode"
    exec gunicorn \
        --bind 0.0.0.0:$PORT \
        --workers 2 \
        --worker-class sync \
        --timeout 120 \
        --access-logfile - \
        --error-logfile - \
        --log-level info \
        wsgi:app
else
    log_info "Running in development mode"
    exec gunicorn \
        --bind 0.0.0.0:$PORT \
        --workers 1 \
        --worker-class sync \
        --timeout 120 \
        --reload \
        --access-logfile - \
        --error-logfile - \
        --log-level debug \
        wsgi:app
fi
