"""Market data routes (historical data, etc.)."""

import logging
from flask import Blueprint, request, jsonify
from app.services import get_kite_client
from app.database import get_instrument_by_key, check_cache_exists
from app.services.greeks_calculator import calculate_option_greeks, is_option_instrument, format_greeks_response

market_bp = Blueprint('market', __name__)

@market_bp.route("/ltp")
def last_traded_price():
    """
    Fetch last traded price (LTP) for one or more instruments.
    
    Query Parameters:
    - tickers: Comma-separated list in format "TRADINGSYMBOL:EXCHANGE"
               (e.g., "SBIN:NSE,RELIANCE:NSE" or "HDFCAMC26MAR2880CE:NFO")
    - apikey: API key for authentication
    - greeks: Optional, set to "true" to include Greeks for options (default: true)
    
    Returns:
    JSON response with LTP for each ticker
    
    For stocks:
    {
        "status": "success",
        "results": {
            "SBIN:NSE": {
                "instrument_token": 779521,
                "tradingsymbol": "SBIN",
                "exchange": "NSE",
                "ltp": 850.50
            }
        }
    }
    
    For options (with Greeks):
    {
        "status": "success",
        "results": {
            "HDFCAMC26MAR2880CE:NFO": {
                "instrument_token": 12345678,
                "tradingsymbol": "HDFCAMC26MAR2880CE",
                "exchange": "NFO",
                "instrument_type": "CE",
                "strike": 2880.0,
                "expiry": "2026-03-26",
                "ltp": 125.50,
                "greeks": {
                    "delta": 0.6543,
                    "gamma": 0.012,
                    "theta": -15.50,
                    "vega": 125.30,
                    "rho": 8.50,
                    "implied_volatility": 0.285,
                    "underlying_price": 2950.50,
                    "moneyness": "ITM"
                }
            }
        }
    }
    
    Notes:
    - Supports both stocks (NSE/BSE) and options/futures (NFO/MCX)
    - Options are automatically detected from instruments cache
    - Greeks are calculated automatically for options using Black-Scholes model
    - Set greeks=false to disable Greeks calculation for faster response
    """
    tickers = request.args.get('tickers')
    if not tickers:
        return jsonify({
            'status': 'error',
            'message': 'tickers parameter is required'}), 400
    
    # Check if Greeks should be included (default: true for options)
    include_greeks = request.args.get('greeks', 'true').lower() != 'false'
    
    # Check if cache is populated
    if not check_cache_exists():
        return jsonify({
            'status': 'error',
            'message': 'Instruments cache is empty. Please call /cache_instruments first.'
        }), 404

    ticker_list = [t.strip() for t in tickers.split(',')]

    try:
        kite = get_kite_client()
        results = {}
        errors = {}

        for ticker in ticker_list:
            # Parse ticker format: TRADINGSYMBOL:EXCHANGE
            if ':' not in ticker:
                errors[ticker] = 'Invalid format. Use TRADINGSYMBOL:EXCHANGE'
                continue
            
            parts = ticker.split(':')
            if len(parts) != 2:
                errors[ticker] = 'Invalid format. Use TRADINGSYMBOL:EXCHANGE'
                continue
            
            tradingsymbol, exchange = parts
            
            # Look up instrument token from database
            instrument = get_instrument_by_key(tradingsymbol, exchange)
            
            if not instrument:
                errors[ticker] = f'Instrument not found in cache'
                continue
            
            instrument_token = instrument['instrument_token']
            instrument_type = instrument.get('instrument_type', '')
            
            try:
                # Fetch LTP data (kite.ltp accepts list and returns dict)
                ltp_response = kite.ltp([instrument_token])
                
                # Extract LTP value from response
                # Response format: {instrument_token: {'instrument_token': xxx, 'last_price': yyy}}
                ltp_value = ltp_response.get(instrument_token, {}).get('last_price', 0)
                
                result = {
                    'instrument_token': instrument_token,
                    'tradingsymbol': tradingsymbol,
                    'exchange': exchange,
                    'ltp': ltp_value
                }
                
                # Add instrument_type for options
                if instrument_type:
                    result['instrument_type'] = instrument_type
                
                # Calculate Greeks for options if enabled
                if include_greeks and is_option_instrument(instrument_type):
                    # Add strike and expiry for options
                    result['strike'] = instrument.get('strike', 0)
                    result['expiry'] = instrument.get('expiry', '')
                    
                    greeks_data = calculate_option_greeks(
                        tradingsymbol=tradingsymbol,
                        exchange=exchange,
                        option_price=ltp_value
                    )
                    
                    if greeks_data:
                        # Include Greeks in response
                        result['greeks'] = format_greeks_response(greeks_data)
                
                results[ticker] = result
                
            except Exception as e:
                errors[ticker] = str(e)
        
        # Build response
        response = {
            'status': 'success' if results else 'error',
            'results': results
        }
        
        if errors:
            response['errors'] = errors
        
        return jsonify(response), 200
        
    except Exception as e:
        logging.error(f"Error fetching LTP data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500               

@market_bp.route("/historical_data")
def historical_data():
    """
    Fetch historical data for one or more instruments.
    
    Query Parameters:
    - tickers: Comma-separated list of tickers in format "TRADINGSYMBOL:EXCHANGE" 
               (e.g., "SBIN:NSE,RELIANCE:NSE" or "HDFCAMC26MAR2880CE:NFO")
    - from: Start date-time string (e.g., "2025-03-16 09:15:00")
    - to: End date-time string (e.g., "2025-03-16 15:30:00")
    - interval: Candle interval (minute, day, 3minute, 5minute, 10minute, 15minute, 30minute, 60minute)
    - greeks: Optional, set to "true" to include Greeks for options at latest candle (default: true)
    - apikey: API key for authentication (checked by before_request)
    
    Returns:
    JSON response with historical data for each ticker
    
    For options with Greeks enabled, includes Greeks calculated at the latest candle:
    {
        "results": {
            "HDFCAMC26MAR2880CE:NFO": {
                "data": [...candles...],
                "greeks": {
                    "delta": 0.6543,
                    "gamma": 0.012,
                    ...
                },
                "latest_price": 125.50
            }
        }
    }
    
    Notes:
    - Supports both stocks (NSE/BSE) and options/futures (NFO/MCX)
    - Options are automatically detected from instrument_type (CE/PE/FUT)
    - Greeks are calculated using the close price of the latest candle
    - Open Interest (OI) fields are NOT available via this endpoint (Kite API limitation)
    - For cached data with OI support, use /fetch_history and /get_history endpoints
    """
    # Get query parameters
    tickers = request.args.get('tickers')
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    interval = request.args.get('interval', 'day')
    include_greeks = request.args.get('greeks', 'true').lower() != 'false'
    
    # Validate required parameters
    if not tickers:
        return jsonify({
            'status': 'error',
            'message': 'tickers parameter is required (format: "TRADINGSYMBOL:EXCHANGE,TRADINGSYMBOL:EXCHANGE")'
        }), 400
    
    if not from_date:
        return jsonify({
            'status': 'error',
            'message': 'from parameter is required (format: "YYYY-MM-DD HH:MM:SS")'
        }), 400
    
    if not to_date:
        return jsonify({
            'status': 'error',
            'message': 'to parameter is required (format: "YYYY-MM-DD HH:MM:SS")'
        }), 400
    
    # Check if cache is populated
    if not check_cache_exists():
        return jsonify({
            'status': 'error',
            'message': 'Instruments cache is empty. Please call /cache_instruments first.'
        }), 404
    
    # Parse tickers
    ticker_list = [t.strip() for t in tickers.split(',')]
    
    try:
        kite = get_kite_client()
        results = {}
        errors = {}
        
        for ticker in ticker_list:
            # Parse ticker format: TRADINGSYMBOL:EXCHANGE
            if ':' not in ticker:
                errors[ticker] = 'Invalid format. Use TRADINGSYMBOL:EXCHANGE'
                continue
            
            parts = ticker.split(':')
            if len(parts) != 2:
                errors[ticker] = 'Invalid format. Use TRADINGSYMBOL:EXCHANGE'
                continue
            
            tradingsymbol, exchange = parts
            
            # Look up instrument token from database
            instrument = get_instrument_by_key(tradingsymbol, exchange)
            
            if not instrument:
                errors[ticker] = f'Instrument not found in cache'
                continue
            
            instrument_token = instrument['instrument_token']
            instrument_type = instrument.get('instrument_type', '')
            
            try:
                # Fetch historical data using positional args (same as /testing endpoint)
                historical = kite.historical_data(
                    instrument_token,
                    from_date,
                    to_date,
                    interval
                )
                
                # Convert datetime objects to ISO 8601 string format for better compatibility
                formatted_data = []
                latest_close_price = None
                
                for candle in historical:
                    formatted_candle = {
                        'date': candle['date'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(candle['date'], 'strftime') else str(candle['date']),
                        'open': candle['open'],
                        'high': candle['high'],
                        'low': candle['low'],
                        'close': candle['close'],
                        'volume': candle['volume']
                    }
                    formatted_data.append(formatted_candle)
                    latest_close_price = candle['close']  # Keep track of latest price
                
                result = {
                    'instrument_token': instrument_token,
                    'tradingsymbol': tradingsymbol,
                    'exchange': exchange,
                    'data': formatted_data
                }
                
                # Add instrument_type for options
                if instrument_type:
                    result['instrument_type'] = instrument_type
                
                # Calculate Greeks for options if enabled and we have data
                if include_greeks and is_option_instrument(instrument_type) and latest_close_price:
                    result['strike'] = instrument.get('strike', 0)
                    result['expiry'] = instrument.get('expiry', '')
                    result['latest_price'] = latest_close_price
                    
                    greeks_data = calculate_option_greeks(
                        tradingsymbol=tradingsymbol,
                        exchange=exchange,
                        option_price=latest_close_price
                    )
                    
                    if greeks_data:
                        # Include Greeks in response
                        result['greeks'] = format_greeks_response(greeks_data)
                
                results[ticker] = result
                
            except Exception as e:
                errors[ticker] = str(e)
        
        # Build response
        response = {
            'status': 'success' if results else 'error',
            'from': from_date,
            'to': to_date,
            'interval': interval,
            'results': results
        }
        
        if errors:
            response['errors'] = errors
        
        return jsonify(response), 200
        
    except Exception as e:
        logging.error(f"Error fetching historical data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
