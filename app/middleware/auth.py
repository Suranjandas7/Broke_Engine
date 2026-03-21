"""Basic authentication middleware."""

from functools import wraps
from flask import request, Response
from app.config import Config


def check_auth(username, password):
    """Verify basic auth credentials."""
    return username == Config.AUTH_USER and password == Config.AUTH_PASSWORD


def requires_basic_auth(f):
    """Decorator to require basic authentication for a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response(
                'Authentication required',
                401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'}
            )
        return f(*args, **kwargs)
    return decorated
