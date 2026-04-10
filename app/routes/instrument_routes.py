"""Instrument cache management routes."""

import os
import logging
from flask import Blueprint, request, jsonify
from app.middleware.auth import requires_basic_auth
from app.services import get_kite_client
from app.database import (
    init_instruments_db,
    populate_instruments_db,
    get_instrument_by_key,
    search_instruments_by_symbol,
    get_instruments_count,
    check_cache_exists,
    DB_PATH
)
from app.utils import cache_empty_response

instruments_bp = Blueprint('instruments', __name__)


@instruments_bp.route("/cache_instruments")
@requires_basic_auth
def cache_instruments():
    """Cache all instruments from Kite API into SQLite database."""
    try:
        # Initialize database if not exists
        init_instruments_db()
        
        kite = get_kite_client()
        
        # Fetch all instruments from Kite API
        logging.info("Fetching instruments from Kite API...")
        instruments = kite.instruments()
        
        # Populate SQLite database
        logging.info(f"Populating database with {len(instruments)} instruments...")
        total_cached = populate_instruments_db(instruments)
        
        return jsonify({
            'status': 'success',
            'message': f'Cached {total_cached} instruments in SQLite database',
            'total_instruments': total_cached,
            'database_path': DB_PATH
        }), 200
        
    except Exception as e:
        logging.error(f"Error caching instruments: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@instruments_bp.route("/get_instrument")
def get_instrument():
    """Retrieve instrument details by tradingsymbol and optional exchange."""
    tradingsymbol = request.args.get('tradingsymbol')
    exchange = request.args.get('exchange', '')  # Optional exchange parameter
    
    if not tradingsymbol:
        return jsonify({
            'status': 'error',
            'message': 'tradingsymbol parameter is required'
        }), 400
    
    # Check if cache database exists
    if not check_cache_exists():
        return cache_empty_response()
    
    try:
        # If exchange is provided, look for exact match
        if exchange:
            instrument = get_instrument_by_key(tradingsymbol, exchange)
            
            if instrument:
                return jsonify({
                    'status': 'success',
                    'data': instrument
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'Instrument {tradingsymbol} not found for exchange {exchange}'
                }), 404
        
        # If no exchange provided, search across all exchanges
        matching_instruments = search_instruments_by_symbol(tradingsymbol)
        
        if not matching_instruments:
            return jsonify({
                'status': 'error',
                'message': f'Instrument {tradingsymbol} not found'
            }), 404
        
        if len(matching_instruments) == 1:
            return jsonify({
                'status': 'success',
                'data': matching_instruments[0]
            }), 200
        else:
            # Multiple instruments found across exchanges
            return jsonify({
                'status': 'success',
                'message': f'Found {len(matching_instruments)} instruments with tradingsymbol {tradingsymbol}',
                'data': matching_instruments
            }), 200
            
    except Exception as e:
        logging.error(f"Error fetching instrument: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@instruments_bp.route("/cache_status")
def cache_status():
    """Get status of the instruments cache."""
    try:
        exists = check_cache_exists()
        count = get_instruments_count() if exists else 0
        
        if os.path.exists(DB_PATH):
            db_size = os.path.getsize(DB_PATH)
            db_size_mb = db_size / (1024 * 1024)
        else:
            db_size = 0
            db_size_mb = 0
        
        return jsonify({
            'status': 'success',
            'cache_exists': exists,
            'total_instruments': count,
            'database_path': DB_PATH,
            'database_size_bytes': db_size,
            'database_size_mb': round(db_size_mb, 2)
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting cache status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@instruments_bp.route("/clear_cache")
@requires_basic_auth
def clear_cache():
    """Clear the instruments cache by deleting the database file."""
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            logging.info(f"Deleted cache database: {DB_PATH}")
            return jsonify({
                'status': 'success',
                'message': 'Cache cleared successfully'
            }), 200
        else:
            return jsonify({
                'status': 'success',
                'message': 'Cache was already empty'
            }), 200
            
    except Exception as e:
        logging.error(f"Error clearing cache: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
