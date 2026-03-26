"""Flask application factory."""

# for gevent to run properly ->
from gevent import monkey
monkey.patch_all()

import logging
import os
from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.config import Config
from app.database import (
    init_instruments_db,
    init_auth_db,
    get_instruments_count,
    get_access_token
)
from app.database.historical_data import init_historical_db
from app.database.migrations import run_migrations
from app.middleware import check_api_key
from app.middleware.api_key import get_username_from_request
from app.routes import register_blueprints
from app.error_handlers import register_error_handlers


def create_app():
    """Create and configure the Flask application."""
    # Create Flask app instance
    app = Flask(__name__, template_folder='templates')
    
    # Load configuration
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
    
    # Initialize rate limiter with in-memory storage (per API key)
    limiter = Limiter(
        app=app,
        key_func=lambda: get_username_from_request() or get_remote_address(),
        default_limits=[f"{Config.RATE_LIMIT_PER_MINUTE} per minute"],
        storage_uri="memory://",
        strategy="fixed-window"
    )
    
    # Exempt public endpoints from rate limiting
    limiter.exempt(check_api_key)
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        raise
    
    # Initialize databases
    try:
        init_instruments_db()
        init_auth_db()
        init_historical_db()
        
        # Run database migrations for schema updates (e.g., adding OI columns)
        run_migrations()
        
        count = get_instruments_count()
        if count > 0:
            logging.info(f"Instruments database ready with {count} instruments")
        else:
            logging.warning("Instruments database is empty. Call /cache_instruments to populate.")
        
        # Check token status
        token = get_access_token()
        if token:
            logging.info("Access token found in database")
        else:
            logging.warning("No access token found. Please login or call /set_access_token")
            
    except Exception as e:
        logging.error(f"Error initializing database: {str(e)}")
        raise
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register middleware
    app.before_request(check_api_key)
    
    logging.info("Flask application initialized successfully")
    
    return app
