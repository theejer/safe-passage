"""Application factory for SafePassage backend.

This module wires Flask app configuration, extension initialization,
and blueprint registration. Route modules expose API endpoints and
call service modules; services may persist data through model wrappers.
"""

from flask import Flask
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
    
    # Enable CORS for web frontend and mobile clients
    CORS(app, resources={r"/*": {"origins": "*"}})
    
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
    app.register_blueprint(heartbeats_bp, url_prefix="/heartbeats")

    return app
