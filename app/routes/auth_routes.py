"""Authentication and login routes."""

import json
import logging
from flask import Blueprint, request, session, render_template
from app.config import Config
from app.middleware.auth import requires_basic_auth
from app.services import get_kite_client
from app.database import save_access_token
from app.utils import serializer

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/")
@requires_basic_auth
def index():
    """Index page with Kite Connect login link."""
    return render_template(
        'index.html',
        api_key=Config.KITE_API_KEY,
        redirect_url=Config.REDIRECT_URL,
        console_url=Config.CONSOLE_URL,
        login_url=Config.LOGIN_URL
    )


@auth_bp.route("/login")
def login():
    """OAuth callback handler for Kite Connect login."""
    request_token = request.args.get("request_token")

    if not request_token:
        return """
            <span style="color: red">
                Error while generating request token.
            </span>
            <a href='/'>Try again.<a>"""

    kite = get_kite_client()
    data = kite.generate_session(request_token, api_secret=Config.KITE_API_SECRET)
    
    # Save to both session (backward compat) and database (persistent)
    session["access_token"] = data["access_token"]
    save_access_token(data["access_token"])

    return render_template(
        'login_success.html',
        access_token=data["access_token"]
    )


@auth_bp.route("/testing")
@requires_basic_auth
def testing():
    """Test endpoint for historical data retrieval."""
    kite = get_kite_client()
    historical_data = kite.historical_data(
        "738561", "2025-03-16 15:00:00", "2026-03-16 15:15:00", "day"
    )
    return str(historical_data)
