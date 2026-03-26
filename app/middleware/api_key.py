"""JWT authentication middleware."""

import jwt
from datetime import datetime, timedelta, timezone
from flask import request, Response, g
from app.config import Config


def generate_token(username):
    """Generate a JWT token for the given username."""
    payload = {
        'username': username,
        'exp': datetime.now(timezone.utc) + timedelta(days=Config.JWT_EXPIRATION_DAYS),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, str(Config.SECRET_KEY), algorithm='HS256')


def verify_token(token):
    """Verify a JWT token and return the payload if valid."""
    try:
        payload = jwt.decode(token, str(Config.SECRET_KEY), algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_username_from_request():
    """Extract username from JWT token in request for rate limiting."""
    if request.endpoint in ['auth.index', 'auth.login', 'auth.generate_token_endpoint', 'instruments.cache_instruments', 'static']:
        return None
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    token = parts[1]
    payload = verify_token(token)
    if payload:
        return payload.get('username', 'anonymous')
    return None


def check_api_key():
    """Require JWT token for all endpoints except /, /login, /auth/token, /cache_instruments, and static."""
    if request.endpoint in ['auth.index', 'auth.login', 'auth.generate_token_endpoint', 'instruments.cache_instruments', 'static']:
        return None
    
    # Get Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return Response('Missing Authorization header', 401)
    
    # Extract Bearer token
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return Response('Invalid Authorization header format. Use: Bearer <token>', 401)
    
    token = parts[1]
    payload = verify_token(token)
    if not payload:
        return Response('Invalid or expired token', 401)
    
    # Store username in g for rate limiting
    g.user = payload.get('username', 'anonymous')
    
    return None
