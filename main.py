"""
Broke Engine - Zerodha Kite Connect API Server

A Flask-based API server for interacting with Zerodha Kite Connect.
Provides endpoints for instrument caching, historical data, and token management.
"""

import logging
from app import create_app
from app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create Flask application
app = create_app()

if __name__ == "__main__":
    logging.info(f"Starting Broke Engine on {Config.HOST}:{Config.PORT}")
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=False
    )
