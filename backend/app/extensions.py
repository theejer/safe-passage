"""Shared extension/client initialization.

This module initializes reusable infrastructure objects used across
models and services, such as the Supabase client and logger.
"""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask
from supabase import Client, create_client

supabase_client: Client | None = None


def init_extensions(app: Flask) -> None:
    """Initialize external clients and framework-wide logging.

    Interactions:
    - Reads credentials from Flask config (loaded in app factory)
    - Exposes Supabase client consumed by app.models.* wrappers
    """
    global supabase_client

    logging.basicConfig(level=logging.INFO)

    url = app.config.get("SUPABASE_URL")
    key = app.config.get("SUPABASE_KEY")
    if url and key:
        supabase_client = create_client(url, key)
    else:
        app.logger.warning("Supabase credentials are missing; DB calls may fail.")


def get_supabase() -> Client:
    """Return initialized Supabase client or raise clear startup error."""
    if supabase_client is None:
        raise RuntimeError("Supabase client not initialized. Check app config.")
    return supabase_client
