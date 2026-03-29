"""Kite Connect API client service."""

import logging
from flask import session, request, redirect, url_for, flash
from kiteconnect import KiteConnect
from kiteconnect.exceptions import TokenException
from app.config import Config
from app.database import get_access_token, clear_access_token


def _is_browser_request():
    """Check if request is from browser (wants HTML) or API client (wants JSON)."""
    accept_header = request.headers.get('Accept', '')
    return 'text/html' in accept_header


def _handle_token_expiry():
    """
    Callback for KiteConnect session expiry hook.
    
    This function is called automatically by KiteConnect when a TokenException occurs.
    It handles token cleanup and redirection based on the request type.
    
    Behavior:
    - Clears expired token from database and session
    - Browser requests: Flash error message and redirect to login page
    - API requests: Raise TokenException (caught by error handler for JSON response)
    """
    logging.warning("Token expired - clearing stored token and initiating re-authentication flow")
    
    # Clear the expired token from database
    clear_access_token()
    
    # Clear session token if present
    if "access_token" in session:
        session.pop("access_token", None)
        logging.info("Cleared expired token from session")
    
    # Check if this is a browser request or API request
    if _is_browser_request():
        # Browser request - redirect to login page with error message
        logging.info("Browser request detected - redirecting to login page")
        flash("Your access token has expired. Please login again to continue.", "error")
        return redirect(url_for('auth.index', error='token_expired'))
    else:
        # API request - re-raise TokenException to be caught by error handler
        logging.info("API request detected - raising TokenException for JSON error response")
        raise TokenException("Access token has expired. Please re-authenticate.")


def get_kite_client():
    """Returns a kite client object with persistent token storage and expiry handling."""
    kite = KiteConnect(api_key=Config.KITE_API_KEY)
    
    # Set up session expiry hook for automatic token expiry handling
    kite.set_session_expiry_hook(_handle_token_expiry)
    
    # Try session first (for browser-based flow backward compatibility)
    if "access_token" in session:
        kite.set_access_token(session["access_token"])
        return kite
    
    # Fall back to database (for API-based flow)
    token = get_access_token()
    if token:
        kite.set_access_token(token)
    
    return kite
