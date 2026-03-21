"""Utility functions."""

from datetime import date, datetime
from decimal import Decimal


def serializer(obj):
    """Custom JSON serializer for dates and decimals."""
    return isinstance(obj, (date, datetime, Decimal)) and str(obj)
