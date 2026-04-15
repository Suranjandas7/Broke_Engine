"""Utility functions."""

from datetime import date, datetime
from decimal import Decimal
from typing import Tuple
from flask import jsonify


def serializer(obj):
    """Custom JSON serializer for dates and decimals."""
    if isinstance(obj, (date, datetime, Decimal)):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def parse_ticker(ticker: str) -> Tuple[str, str]:
    """
    Parse ticker string into (symbol, exchange).
    
    Args:
        ticker: Ticker in format "SYMBOL:EXCHANGE"
        
    Returns:
        Tuple of (tradingsymbol, exchange)
        
    Raises:
        ValueError: If ticker format is invalid
    """
    if ':' not in ticker:
        raise ValueError("Invalid format. Use TRADINGSYMBOL:EXCHANGE")
    parts = ticker.split(':')
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Invalid format. Use TRADINGSYMBOL:EXCHANGE")
    return parts[0], parts[1]


def cache_empty_response():
    """Return standard error response for empty instruments cache."""
    return jsonify({
        'status': 'error',
        'message': 'Instruments cache is empty. Please call /cache_instruments first.'
    }), 404
