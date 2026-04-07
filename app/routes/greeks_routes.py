"""Greeks calculation API routes."""

import logging
from flask import Blueprint, request, jsonify

from app.services.greeks_calculator import calculate_option_greeks
from app.utils import parse_ticker

logger = logging.getLogger(__name__)

greeks_bp = Blueprint('greeks', __name__)


@greeks_bp.route('/greeks', methods=['GET'])
def get_greeks():
    """
    Calculate Greeks for an option contract.
    
    Query Parameters:
        - apikey: API key for authentication (required)
        - ticker: Trading symbol in format SYMBOL:EXCHANGE (required)
                  Example: HDFCAMC26MAR2880CE:NFO
        - risk_free_rate: Optional risk-free rate override (decimal, e.g., 0.065 for 6.5%)
    
    Returns:
        JSON response with Greeks data:
        {
            "status": "success",
            "ticker": "HDFCAMC26MAR2880CE",
            "exchange": "NFO",
            "option_type": "CE",
            "strike": 2880.0,
            "expiry": "2026-03-26",
            "underlying_symbol": "HDFCAMC",
            "underlying_price": 2950.50,
            "option_price": 125.50,
            "days_to_expiry": 6,
            "time_to_expiry_years": 0.0164,
            "risk_free_rate": 0.065,
            "greeks": {
                "delta": 0.6543,
                "gamma": 0.012,
                "theta": -15.50,
                "vega": 125.30,
                "rho": 8.50
            },
            "implied_volatility": 0.285,
            "theoretical_price": 125.45,
            "intrinsic_value": 70.50,
            "time_value": 55.00,
            "moneyness": "ITM"
        }
    
    Error Responses:
        - 400: Missing or invalid parameters
        - 404: Instrument not found
        - 500: Calculation failed
    
    Notes:
        - Only works for options (CE/PE), returns error for stocks
        - Returns error if option has expired
        - Fetches real-time prices from Kite API
        - Uses Black-Scholes model for European options
    """
    try:
        # Get ticker parameter
        ticker = request.args.get('ticker', '').strip()
        if not ticker:
            return jsonify({
                "status": "error",
                "message": "Missing required parameter: ticker"
            }), 400
        
        # Parse ticker format (SYMBOL:EXCHANGE)
        try:
            tradingsymbol, exchange = parse_ticker(ticker)
        except ValueError:
            return jsonify({
                "status": "error",
                "message": "Invalid ticker format. Expected format: SYMBOL:EXCHANGE (e.g., HDFCAMC26MAR2880CE:NFO)"
            }), 400
        
        # Get optional risk_free_rate override
        risk_free_rate = None
        rfr_param = request.args.get('risk_free_rate', '').strip()
        if rfr_param:
            try:
                risk_free_rate = float(rfr_param)
                if risk_free_rate < 0 or risk_free_rate > 1:
                    return jsonify({
                        "status": "error",
                        "message": "Risk-free rate must be between 0 and 1"
                    }), 400
            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": "Invalid risk_free_rate value"
                }), 400
        
        # Calculate Greeks
        greeks_data = calculate_option_greeks(
            tradingsymbol=tradingsymbol,
            exchange=exchange,
            risk_free_rate=risk_free_rate
        )
        
        if greeks_data is None:
            return jsonify({
                "status": "error",
                "message": f"Failed to calculate Greeks for {ticker}. "
                          "This may be because the instrument is not an option, "
                          "has expired, or required data is unavailable."
            }), 404
        
        # Import instrument data for response
        from app.database.instruments import get_instrument_by_key
        instrument = get_instrument_by_key(tradingsymbol, exchange)
        
        # Build response
        response = {
            "status": "success",
            "ticker": tradingsymbol,
            "exchange": exchange,
            "option_type": instrument.get('instrument_type', ''),
            "strike": instrument.get('strike', 0),
            "expiry": instrument.get('expiry', ''),
            "lot_size": instrument.get('lot_size', 0),
            **greeks_data
        }
        
        # Add risk_free_rate used
        if risk_free_rate is None:
            from app.config import Config
            response['risk_free_rate'] = Config.RISK_FREE_RATE
        else:
            response['risk_free_rate'] = risk_free_rate
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in /greeks endpoint: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500


@greeks_bp.route('/greeks/batch', methods=['POST'])
def get_greeks_batch():
    """
    Calculate Greeks for multiple option contracts in one request.
    
    Request Body (JSON):
        {
            "tickers": [
                "HDFCAMC26MAR2880CE:NFO",
                "HDFCAMC26MAR2900CE:NFO",
                "NIFTY26APR24000PE:NFO"
            ],
            "risk_free_rate": 0.065  // Optional
        }
    
    Returns:
        JSON response with Greeks for all tickers:
        {
            "status": "success",
            "count": 3,
            "results": [
                {
                    "ticker": "HDFCAMC26MAR2880CE:NFO",
                    "greeks": {...},
                    ...
                },
                ...
            ],
            "errors": [
                {
                    "ticker": "INVALID:NSE",
                    "error": "Instrument not found"
                }
            ]
        }
    
    Notes:
        - Processes up to 50 tickers per request
        - Failed calculations are reported in "errors" array
        - Successful calculations are in "results" array
    """
    try:
        # Get request body
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "Request body must be JSON"
            }), 400
        
        tickers = data.get('tickers', [])
        if not isinstance(tickers, list) or len(tickers) == 0:
            return jsonify({
                "status": "error",
                "message": "Must provide 'tickers' array with at least one ticker"
            }), 400
        
        # Limit batch size
        if len(tickers) > 50:
            return jsonify({
                "status": "error",
                "message": "Maximum 50 tickers per batch request"
            }), 400
        
        risk_free_rate = data.get('risk_free_rate')
        
        # Process each ticker
        results = []
        errors = []
        
        for ticker in tickers:
            try:
                try:
                    tradingsymbol, exchange = parse_ticker(ticker)
                except ValueError:
                    errors.append({
                        "ticker": ticker,
                        "error": "Invalid ticker format"
                    })
                    continue
                
                greeks_data = calculate_option_greeks(
                    tradingsymbol=tradingsymbol,
                    exchange=exchange,
                    risk_free_rate=risk_free_rate
                )
                
                if greeks_data is None:
                    errors.append({
                        "ticker": ticker,
                        "error": "Failed to calculate Greeks"
                    })
                    continue
                
                # Get instrument data
                from app.database.instruments import get_instrument_by_key
                instrument = get_instrument_by_key(tradingsymbol, exchange)
                
                results.append({
                    "ticker": tradingsymbol,
                    "exchange": exchange,
                    "option_type": instrument.get('instrument_type', ''),
                    "strike": instrument.get('strike', 0),
                    "expiry": instrument.get('expiry', ''),
                    **greeks_data
                })
                
            except Exception as e:
                logger.error(f"Error processing ticker {ticker}: {e}")
                errors.append({
                    "ticker": ticker,
                    "error": str(e)
                })
        
        return jsonify({
            "status": "success",
            "count": len(results),
            "results": results,
            "errors": errors if errors else []
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /greeks/batch endpoint: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500
