"""Auth helpers for Supabase JWT verification."""

from __future__ import annotations

from flask import Request

from app.extensions import get_supabase


def extract_bearer_token(request: Request) -> str:
    """Extract bearer token from Authorization header."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise ValueError("missing bearer token")
    token = header.removeprefix("Bearer ").strip()
    if not token:
        raise ValueError("empty bearer token")
    return token


def verify_supabase_user_id(token: str) -> str:
    """Verify JWT through Supabase Auth and return subject user id."""
    response = get_supabase().auth.get_user(token)
    user = getattr(response, "user", None)
    user_id = getattr(user, "id", None)
    if not user_id:
        raise ValueError("invalid bearer token")
    return user_id
