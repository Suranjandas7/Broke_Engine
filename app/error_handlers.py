"""Centralized error handlers for the Flask application."""

import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    """Register all error handlers with the Flask app."""
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle 400 Bad Request errors."""
        logging.warning(f"Bad request: {str(error)}")
        return jsonify({
            'status': 'error',
            'message': 'Bad request',
            'error': str(error)
        }), 400
    
    @app.errorhandler(401)
    def handle_unauthorized(error):
        """Handle 401 Unauthorized errors."""
        logging.warning(f"Unauthorized access: {str(error)}")
        return jsonify({
            'status': 'error',
            'message': 'Unauthorized',
            'error': str(error)
        }), 401
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors."""
        logging.warning(f"Not found: {str(error)}")
        return jsonify({
            'status': 'error',
            'message': 'Resource not found',
            'error': str(error)
        }), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 Internal Server Error."""
        logging.error(f"Internal server error: {str(error)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(error)
        }), 500
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Handle all uncaught exceptions."""
        # If it's an HTTP exception, let the specific handler deal with it
        if isinstance(error, HTTPException):
            return error
        
        logging.error(f"Unhandled exception: {str(error)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred',
            'error': str(error)
        }), 500
