"""Routes module for broke_engine."""

from .auth_routes import auth_bp
from .instrument_routes import instruments_bp
from .market_routes import market_bp
from .token_routes import tokens_bp
from .history_routes import history_bp
from .greeks_routes import greeks_bp


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(instruments_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(tokens_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(greeks_bp)
