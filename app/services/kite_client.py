"""Kite Connect API client service."""

from flask import session
from kiteconnect import KiteConnect
from app.config import Config
from app.database import get_access_token


def get_kite_client():
    """Returns a kite client object with persistent token storage."""
    kite = KiteConnect(api_key=Config.KITE_API_KEY)
    
    # Try session first (for browser-based flow backward compatibility)
    if "access_token" in session:
        kite.set_access_token(session["access_token"])
        return kite
    
    # Fall back to database (for API-based flow)
    token = get_access_token()
    if token:
        kite.set_access_token(token)
    
    return kite
