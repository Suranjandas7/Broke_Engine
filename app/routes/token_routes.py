"""Access token management routes."""

import logging
from flask import Blueprint, request, jsonify
from app.database import save_access_token, get_access_token, clear_access_token

tokens_bp = Blueprint('tokens', __name__)


@tokens_bp.route("/set_access_token")
def set_access_token():
    """
    Set the access token programmatically (requires apikey).
    
    Query Parameters:
    - apikey: API key for authentication
    - access_token: Zerodha access token to store
    
    Example:
    /set_access_token?apikey=test&access_token=your_token_here
    """
    access_token = request.args.get('access_token')
    
    if not access_token:
        return jsonify({
            'status': 'error',
            'message': 'access_token parameter is required'
        }), 400
    
    try:
        save_access_token(access_token)
        logging.info("Access token updated via API")
        return jsonify({
            'status': 'success',
            'message': 'Access token saved successfully'
        }), 200
    except Exception as e:
        logging.error(f"Error saving access token: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@tokens_bp.route("/get_token_status")
def get_token_status():
    """
    Check if access token is set (requires apikey).
    
    Query Parameters:
    - apikey: API key for authentication
    
    Returns token status and masked preview for security.
    """
    try:
        token = get_access_token()
        
        if token:
            # Mask token for security (show last 4 chars only)
            token_preview = f"...{token[-4:]}" if len(token) >= 4 else "****"
            return jsonify({
                'status': 'success',
                'token_exists': True,
                'token_preview': token_preview,
                'message': 'Access token is configured'
            }), 200
        else:
            return jsonify({
                'status': 'success',
                'token_exists': False,
                'message': 'No access token found. Please login via browser or call /set_access_token'
            }), 200
    except Exception as e:
        logging.error(f"Error checking token status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@tokens_bp.route("/clear_token")
def clear_token():
    """
    Clear the stored access token (requires apikey).
    Useful for forcing re-authentication.
    """
    try:
        clear_access_token()
        logging.info("Access token cleared via API")
        return jsonify({
            'status': 'success',
            'message': 'Access token cleared successfully'
        }), 200
    except Exception as e:
        logging.error(f"Error clearing access token: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
