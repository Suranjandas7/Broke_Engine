"""
Historical data routes for fetching and retrieving cached 1-minute data.
"""

import logging
from flask import Blueprint, request, jsonify, Response, make_response
from pydantic import ValidationError

from app.services.kite_client import get_kite_client
from app.models.requests import FetchHistoryRequest, GetHistoryRequest
from app.models.responses import HistoricalDataResponse
from app.services.historical_fetcher import (
    validate_ticker_exists,
    fetch_year_data,
    fetch_multiple_years,
    estimate_fetch_time
)
from app.database.historical_data import (
    insert_historical_data,
    update_cache_metadata,
    get_historical_data,
    get_historical_data_by_date_range,
    check_year_cached,
    get_cache_statistics,
    get_all_cached_tickers
)
from app.utils.export_formats import (
    export_to_arrow,
    export_to_parquet,
    export_to_msgpack,
    export_to_csv,
    get_content_type,
    get_file_extension
)
from app.services.greeks_calculator import calculate_option_greeks, is_option_instrument, format_greeks_response
from app.utils import parse_ticker

logger = logging.getLogger(__name__)

# Create blueprint
history_bp = Blueprint('history', __name__)


@history_bp.route('/fetch_history', methods=['GET'])
def fetch_history():
    """
    Fetch and cache historical 1-minute data for ticker across year range.
    
    Query Parameters:
        apikey (str): API key (handled by middleware)
        ticker (str): Format SYMBOL:EXCHANGE
        from_year (int): Start year (e.g., 2023)
        to_year (int): End year (e.g., 2025)
    
    Returns:
        JSON with fetch status and per-year record counts
    
    Example:
        GET /fetch_history?apikey=test&ticker=SBIN:NSE&from_year=2023&to_year=2025
    """
    try:
        # 1. Validate request parameters
        try:
            req = FetchHistoryRequest(
                ticker=request.args.get('ticker'),
                from_year=int(request.args.get('from_year')),
                to_year=int(request.args.get('to_year'))
            )
        except (TypeError, ValueError) as e:
            return jsonify({
                "status": "error",
                "message": f"Invalid parameters: {str(e)}"
            }), 400
        
        # 2. Parse ticker format
        symbol, exchange = parse_ticker(req.ticker)
        logger.info(
            f"Fetch history request: {symbol}:{exchange} "
            f"years {req.from_year}-{req.to_year}"
        )
        
        # 3. Validate ticker exists in instruments cache
        instrument = validate_ticker_exists(symbol, exchange)
        if not instrument:
            return jsonify({
                "status": "error",
                "message": f"Ticker {symbol}:{exchange} not found in instruments cache. "
                           f"Please run /cache_instruments first."
            }), 404
        
        instrument_token = instrument['instrument_token']
        
        # 4. Get Kite client
        try:
            kite = get_kite_client()
        except Exception as e:
            logger.error(f"Failed to get Kite client: {e}")
            return jsonify({
                "status": "error",
                "message": f"Failed to initialize Kite client: {str(e)}"
            }), 500
        
        # 5. Fetch data for all years (ATOMIC - fail if any year fails)
        year_range = range(req.from_year, req.to_year + 1)
        num_years = len(year_range)
        
        logger.info(f"Fetching {num_years} years for {symbol}:{exchange}")
        
        total_records_added = 0
        year_results = {}
        
        try:
            # Use existing fetch_multiple_years function
            results = fetch_multiple_years(
                kite,
                symbol,
                exchange,
                req.from_year,
                req.to_year,
                instrument_token
            )
            
            # Process results for each year
            for year, (candles, last_timestamp) in results.items():
                if candles:  # New data fetched
                    # Store in database
                    records_inserted = insert_historical_data(symbol, exchange, candles)
                    
                    # Update metadata
                    update_cache_metadata(
                        symbol,
                        exchange,
                        instrument_token,
                        year,
                        last_timestamp,
                        records_inserted
                    )
                    
                    total_records_added += records_inserted
                    year_results[year] = {
                        "records_added": records_inserted,
                        "last_timestamp": last_timestamp,
                        "already_cached": False
                    }
                else:  # Already cached
                    year_results[year] = {
                        "records_added": 0,
                        "last_timestamp": None,
                        "already_cached": True
                    }
        
        except Exception as e:
            # ATOMIC: If any year fails, entire request fails
            logger.error(f"Failed to fetch multi-year data: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Failed to fetch data: {str(e)}. No data was cached."
            }), 500
        
        # 6. Return success response
        return jsonify({
            "status": "success",
            "message": f"Successfully processed {num_years} year(s) for {req.ticker}",
            "ticker": req.ticker,
            "from_year": req.from_year,
            "to_year": req.to_year,
            "total_records_added": total_records_added,
            "years": year_results
        })
    
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return jsonify({
            "status": "error",
            "message": "Invalid request parameters",
            "errors": e.errors()
        }), 400
    
    except Exception as e:
        logger.error(f"Unexpected error in fetch_history: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500


@history_bp.route('/get_history', methods=['GET'])
def get_history():
    """
    Export cached historical data by year range OR date range.
    
    Query Parameters (Option 1 - Years):
        apikey, ticker, from_year, to_year, format (optional)
    
    Query Parameters (Option 2 - Dates):
        apikey, ticker, from_date, to_date, format (optional)
    
    Format Options:
        json (default), arrow, parquet, msgpack, csv
    
    Returns:
        Data in requested format (JSON, Arrow, Parquet, MessagePack, or CSV)
    
    Examples:
        Years: /get_history?apikey=test&ticker=SBIN:NSE&from_year=2023&to_year=2024&format=arrow
        Dates: /get_history?apikey=test&ticker=SBIN:NSE&from_date=2024-01-15 09:15:00&to_date=2024-06-30 15:30:00&format=parquet
    """
    try:
        # 1. Validate request parameters
        try:
            req = GetHistoryRequest(
                ticker=request.args.get('ticker'),
                from_year=request.args.get('from_year', type=int),
                to_year=request.args.get('to_year', type=int),
                from_date=request.args.get('from_date'),
                to_date=request.args.get('to_date'),
                format=request.args.get('format', 'json')
            )
        except (TypeError, ValueError) as e:
            return jsonify({
                "status": "error",
                "message": f"Invalid parameters: {str(e)}"
            }), 400
        
        # 2. Parse ticker format
        symbol, exchange = parse_ticker(req.ticker)
        
        # Get instrument info for metadata (to include instrument_type)
        from app.database.instruments import get_instrument_by_key
        instrument = get_instrument_by_key(symbol, exchange)
        instrument_type = instrument.get('instrument_type', 'UNKNOWN') if instrument else 'UNKNOWN'
        
        # 3. Determine query type (year-based or date-based)
        if req.from_date and req.to_date:
            # Date-based query
            logger.info(
                f"Get history (date range): {symbol}:{exchange} "
                f"from {req.from_date} to {req.to_date}, format={req.format}"
            )
            
            try:
                data = get_historical_data_by_date_range(
                    symbol, exchange, req.from_date, req.to_date
                )
            except ValueError as e:
                # Strict: Return error if no data exists
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 400
            except Exception as e:
                logger.error(f"Failed to query date range: {e}", exc_info=True)
                return jsonify({
                    "status": "error",
                    "message": f"Failed to retrieve data: {str(e)}"
                }), 500
            
            # Build metadata for response
            metadata = {
                "status": "success",
                "ticker": symbol,
                "exchange": exchange,
                "instrument_type": instrument_type,
                "from_date": req.from_date,
                "to_date": req.to_date,
                "record_count": len(data)
            }
        
        else:
            # Year-based query
            logger.info(
                f"Get history (year range): {symbol}:{exchange} "
                f"years {req.from_year}-{req.to_year}, format={req.format}"
            )
            
            # Validate all years in range are cached
            missing_years = []
            for year in range(req.from_year, req.to_year + 1):
                if not check_year_cached(symbol, exchange, year):
                    missing_years.append(year)
            
            if missing_years:
                return jsonify({
                    "status": "error",
                    "message": f"Missing cached data for years: {missing_years}. "
                               f"Please fetch these years first using /fetch_history.",
                    "missing_years": missing_years,
                    "ticker": req.ticker
                }), 400
            
            # Query data from database
            try:
                data = get_historical_data(symbol, exchange, req.from_year, req.to_year)
            except Exception as e:
                logger.error(f"Failed to query historical data: {e}", exc_info=True)
                return jsonify({
                    "status": "error",
                    "message": f"Failed to retrieve data: {str(e)}"
                }), 500
            
            # Build metadata for response
            metadata = {
                "status": "success",
                "ticker": symbol,
                "exchange": exchange,
                "instrument_type": instrument_type,
                "from_year": req.from_year,
                "to_year": req.to_year,
                "record_count": len(data)
            }
        
        # Calculate Greeks for options if we have data and it's JSON format
        greeks_param = request.args.get('greeks', 'true').lower()
        include_greeks = greeks_param != 'false' and req.format == 'json'
        
        if include_greeks and instrument and is_option_instrument(instrument_type) and len(data) > 0:
            # Get latest close price from data
            latest_record = data[-1]  # Last record
            latest_close = latest_record.get('close', 0)
            
            if latest_close and latest_close > 0:
                greeks_data = calculate_option_greeks(
                    tradingsymbol=symbol,
                    exchange=exchange,
                    option_price=latest_close
                )
                
                if greeks_data:
                    metadata['greeks'] = format_greeks_response(greeks_data)
                    metadata['latest_close'] = latest_close
                    metadata['strike'] = instrument.get('strike', 0)
                    metadata['expiry'] = instrument.get('expiry', '')
        
        # 4. Export data in requested format
        if req.format == 'json':
            # Default JSON response
            return jsonify({**metadata, "data": data})
        
        elif req.format == 'arrow':
            # Apache Arrow format
            arrow_data = export_to_arrow(data, metadata)
            response = make_response(arrow_data)
            response.headers['Content-Type'] = get_content_type('arrow')
            response.headers['Content-Disposition'] = f'attachment; filename="{symbol}_{exchange}_history.{get_file_extension("arrow")}"'
            return response
        
        elif req.format == 'parquet':
            # Apache Parquet format
            parquet_data = export_to_parquet(data, metadata)
            response = make_response(parquet_data)
            response.headers['Content-Type'] = get_content_type('parquet')
            response.headers['Content-Disposition'] = f'attachment; filename="{symbol}_{exchange}_history.{get_file_extension("parquet")}"'
            return response
        
        elif req.format == 'msgpack':
            # MessagePack format
            msgpack_data = export_to_msgpack(data, metadata)
            response = make_response(msgpack_data)
            response.headers['Content-Type'] = get_content_type('msgpack')
            response.headers['Content-Disposition'] = f'attachment; filename="{symbol}_{exchange}_history.{get_file_extension("msgpack")}"'
            return response
        
        elif req.format == 'csv':
            # CSV format
            csv_data = export_to_csv(data, metadata)
            response = make_response(csv_data)
            response.headers['Content-Type'] = get_content_type('csv')
            response.headers['Content-Disposition'] = f'attachment; filename="{symbol}_{exchange}_history.{get_file_extension("csv")}"'
            return response
        
        else:
            # Should never reach here due to validation
            return jsonify({
                "status": "error",
                "message": f"Unsupported format: {req.format}"
            }), 400
    
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return jsonify({
            "status": "error",
            "message": "Invalid request parameters",
            "errors": e.errors()
        }), 400
    
    except Exception as e:
        logger.error(f"Unexpected error in get_history: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500


@history_bp.route('/history_cache_status', methods=['GET'])
def history_cache_status():
    """
    Get statistics about cached historical data.
    
    Query Parameters:
        apikey (str): API key for authentication (handled by middleware)
    
    Returns:
        JSON with cache statistics and list of cached tickers
    
    Example:
        GET /history_cache_status?apikey=test
    """
    try:
        # Get overall statistics
        stats = get_cache_statistics()
        
        # Get list of cached tickers
        tickers = get_all_cached_tickers()
        
        return jsonify({
            "status": "success",
            "statistics": stats,
            "cached_tickers": tickers
        })
    
    except Exception as e:
        logger.error(f"Error getting cache status: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to get cache status: {str(e)}"
        }), 500
