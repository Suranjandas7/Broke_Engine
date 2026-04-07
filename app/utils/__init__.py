"""Utility functions."""

from datetime import date, datetime
from decimal import Decimal
from typing import Tuple


def serializer(obj):
    """Custom JSON serializer for dates and decimals."""
    return isinstance(obj, (date, datetime, Decimal)) and str(obj)


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
