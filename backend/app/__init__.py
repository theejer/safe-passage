"""Application factory for SafePassage backend.

This module wires Flask app configuration, extension initialization,
and blueprint registration. Route modules expose API endpoints and
call service modules; services may persist data through model wrappers.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from flask import Flask
from flask_cors import CORS
from flask_cors import CORS

from app.config import get_config
from app.extensions import init_extensions
from app.routes.reports import reports_bp

def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application instance.

    Interactions:
    - Loads settings from app.config
    - Initializes shared clients/logging from app.extensions
    - Registers route blueprints from app.routes.*
    """
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))
    CORS(
        app,
        resources={r"/*": {"origins": app.config.get("CORS_ORIGINS", ["*"])}},
        supports_credentials=app.config.get("CORS_ALLOW_CREDENTIALS", False),
        allow_headers=["Authorization", "Content-Type"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    app.register_blueprint(reports_bp)
    init_extensions(app)

    from app.routes.healthcheck import healthcheck_bp
    from app.routes.users import users_bp
    from app.routes.trips import trips_bp
    from app.routes.itinerary_analysis import itinerary_analysis_bp
    from app.routes.heartbeats import heartbeats_bp
    from app.routes.auth import auth_bp

    app.register_blueprint(healthcheck_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(users_bp, url_prefix="/users")
    app.register_blueprint(users_bp, url_prefix="/api/users", name="api_users")
    app.register_blueprint(trips_bp, url_prefix="/trips")
    app.register_blueprint(trips_bp, url_prefix="/api/trips", name="api_trips")
    app.register_blueprint(itinerary_analysis_bp, url_prefix="/itinerary")
    app.register_blueprint(heartbeats_bp, url_prefix="/heartbeat", name="heartbeat_alias")
    app.register_blueprint(heartbeats_bp, url_prefix="/heartbeats")

    if app.config.get("ENABLE_HEARTBEAT_SCHEDULER", False):
        from app.tasks.monitor_offline import run_watchdog_task

        def _run_watchdog_job() -> None:
            with app.app_context():
                run_watchdog_task()

        scheduler = BackgroundScheduler(timezone="UTC")
        scheduler.add_job(
            func=_run_watchdog_job,
            trigger=IntervalTrigger(minutes=app.config.get("HEARTBEAT_WATCHDOG_INTERVAL_MINUTES", 5)),
            id="heartbeat-watchdog",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        app.extensions["heartbeat_scheduler"] = scheduler
        app.logger.info("Heartbeat watchdog scheduler started.")

    return app
