"""API key validation middleware."""

from flask import request, Response
from app.config import Config


def check_api_key():
    """Require API key for all endpoints except / and /login."""
    if request.endpoint in ['auth.index', 'auth.login', 'static']:
        return None
    
    api_key_param = request.args.get('apikey')
    if api_key_param != Config.API_KEY:
        return Response('Invalid or missing API key', 401)
    
    return None
