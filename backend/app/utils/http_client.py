"""HTTP client wrapper.

Centralizes outbound web/LLM requests so retries, timeouts, and logging
can be consistently applied by service modules.
"""

import requests


def get_json(url: str, timeout_seconds: int = 10) -> dict:
    """Fetch JSON from URL with a conservative default timeout."""
    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    return response.json()


def post_json(url: str, payload: dict, timeout_seconds: int = 15) -> dict:
    """Post JSON payload and return response JSON body."""
    response = requests.post(url, json=payload, timeout=timeout_seconds)
    response.raise_for_status()
    return response.json()
