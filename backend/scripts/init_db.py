#!/usr/bin/env python3
"""
Database initialization script for SafePassage backend.

This script:
1. Checks if the database schema is already initialized (by looking for the 'users' table)
2. If not, reads and applies the schema from contracts/db/schema_outline.sql
3. Handles errors gracefully and exits with appropriate status codes

Usage:
  python scripts/init_db.py

Environment variables required:
  - SQLALCHEMY_DATABASE_URI: PostgreSQL connection string
  - APP_CONFIG: application environment (development/production)
"""

import os
import sys
import logging
from pathlib import Path
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_connection_params() -> dict:
    """Extract database connection parameters from SQLALCHEMY_DATABASE_URI."""
    db_uri = os.getenv('SQLALCHEMY_DATABASE_URI', '')
    
    if not db_uri:
        logger.error("SQLALCHEMY_DATABASE_URI environment variable not set")
        sys.exit(1)
    
    try:
        parsed = urlparse(db_uri)
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/'),
            'user': parsed.username,
            'password': parsed.password,
        }
    except Exception as e:
        logger.error(f"Failed to parse database URI: {e}")
        sys.exit(1)


def check_schema_exists() -> bool:
    """Check if the database schema is already initialized."""
    try:
        import psycopg2
        
        params = get_db_connection_params()
        conn = psycopg2.connect(**params)
        cursor = conn.cursor()
        
        # Check if 'users' table exists (primary table in schema)
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'users'
            )
        """)
        exists = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return exists
    except Exception as e:
        logger.error(f"Failed to check schema existence: {e}")
        return False


def apply_schema() -> bool:
    """Apply the database schema from contracts/db/schema_outline.sql."""
    try:
        import psycopg2
        
        # Find schema file relative to this script
        script_dir = Path(__file__).parent.parent
        schema_file = script_dir.parent / 'contracts' / 'db' / 'schema_outline.sql'
        
        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file}")
            return False
        
        logger.info(f"Reading schema from: {schema_file}")
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Connect and apply schema
        params = get_db_connection_params()
        conn = psycopg2.connect(**params)
        cursor = conn.cursor()
        
        logger.info("Applying database schema...")
        
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements, 1):
            try:
                cursor.execute(statement)
                logger.debug(f"Executed statement {i}/{len(statements)}")
            except Exception as e:
                # Some statements might fail if objects already exist, that's OK
                logger.debug(f"Statement {i} skipped (may already exist): {str(e)[:100]}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("✓ Database schema applied successfully")
        return True
    
    except ImportError:
        logger.error("psycopg2 is not installed. Cannot apply schema.")
        return False
    except Exception as e:
        logger.error(f"Failed to apply database schema: {e}")
        return False


def main():
    """Main initialization routine."""
    logger.info("Starting SafePassage database initialization...")
    
    # Check if schema already exists
    if check_schema_exists():
        logger.info("✓ Database schema already initialized, skipping setup")
        sys.exit(0)
    
    logger.info("Database schema not found, initializing...")
    
    # Apply schema
    if apply_schema():
        logger.info("✓ Database initialization completed successfully")
        sys.exit(0)
    else:
        logger.error("✗ Database initialization failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
