"""Configuration objects for SafePassage backend.

This module centralizes environment-driven settings used by routes,
services, and external integrations (Supabase, model provider, alerts).
"""

import os


class BaseConfig:
    """Base runtime config shared by local/dev/prod environments."""

    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai")
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")


class DevelopmentConfig(BaseConfig):
    """Developer-friendly defaults for local execution."""

    DEBUG = True


class ProductionConfig(BaseConfig):
    """Production runtime configuration."""

    DEBUG = False


def get_config(config_name: str | None = None):
    """Return config class for app factory based on environment hint."""
    name = (config_name or os.getenv("APP_CONFIG") or "development").lower()
    if name == "production":
        return ProductionConfig
    return DevelopmentConfig
