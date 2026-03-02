"""Configuration objects for SafePassage backend.

This module centralizes environment-driven settings used by routes,
services, and external integrations.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class BaseConfig:
    """Base runtime config shared by local/dev/prod environments."""

    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI") or f"sqlite:///{BASE_DIR / 'safepassage.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai")
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_BOT_ENABLED = os.getenv("TELEGRAM_BOT_ENABLED", "0") == "1"
    TELEGRAM_POLL_INTERVAL_SECONDS = int(os.getenv("TELEGRAM_POLL_INTERVAL_SECONDS", "2"))

    ENABLE_HEARTBEAT_SCHEDULER = os.getenv("ENABLE_HEARTBEAT_SCHEDULER", "0") == "1"
    HEARTBEAT_WATCHDOG_INTERVAL_MINUTES = int(os.getenv("HEARTBEAT_WATCHDOG_INTERVAL_MINUTES", "5"))
    HEARTBEAT_WATCHDOG_KEY = os.getenv("HEARTBEAT_WATCHDOG_KEY", "")
    HEARTBEAT_FORCE_STAGE_1_TEST_MODE = os.getenv("HEARTBEAT_FORCE_STAGE_1_TEST_MODE", "0") == "1"

    _cors_origins = os.getenv("CORS_ORIGINS") or os.getenv("ALLOWED_ORIGINS", "*")
    CORS_ORIGINS = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()] or ["*"]
    CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "0") == "1"


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
