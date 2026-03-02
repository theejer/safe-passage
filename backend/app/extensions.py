"""Shared extension/client initialization.

This module initializes reusable infrastructure objects used across
models and services, with SQLAlchemy as the primary data engine.
"""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask
from supabase import Client, create_client
from sqlalchemy import Engine, create_engine

supabase_client: Client | None = None
sqlalchemy_engine: Engine | None = None


def init_extensions(app: Flask) -> None:
    """Initialize external clients and framework-wide logging.

    Interactions:
    - Initializes SQLAlchemy engine for persistence
    - Optionally initializes Supabase client for auth-related integrations
    """
    global supabase_client, sqlalchemy_engine

    logging.basicConfig(level=logging.WARNING)

    url = app.config.get("SUPABASE_URL")
    key = app.config.get("SUPABASE_KEY")

    if url and key and not url.startswith("https://your-"):
        try:
            supabase_client = create_client(url, key)
        except Exception as e:
            app.logger.warning(f"Supabase initialization failed: {e}. Continuing in degraded mode.")
    else:
        app.logger.debug("Supabase auth integration not configured; continuing with SQLAlchemy-backed data access.")

    sqlalchemy_uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    if sqlalchemy_uri:
        sqlalchemy_engine = create_engine(sqlalchemy_uri, pool_pre_ping=True)
    else:
        app.logger.warning("SQLALCHEMY_DATABASE_URI is missing; SQLAlchemy DB calls may fail.")


def get_supabase() -> Client:
    """Return initialized Supabase client or raise clear startup error."""
    if supabase_client is None:
        raise RuntimeError("Supabase client not initialized. Check app config.")
    return supabase_client


def get_db_engine() -> Engine:
    """Return initialized SQLAlchemy engine or raise clear startup error."""
    if sqlalchemy_engine is None:
        raise RuntimeError("SQLAlchemy engine not initialized. Check SQLALCHEMY_DATABASE_URI.")
    return sqlalchemy_engine
