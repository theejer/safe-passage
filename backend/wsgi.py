"""WSGI entrypoint for SafePassage backend.

Gunicorn/WSGI servers import `app` from this module.
"""

from app import create_app

app = create_app()


if __name__ == "__main__":
    # Local fallback runner for quick manual checks.
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=bool(app.config.get("DEBUG", False)),
        use_reloader=False,
    )
