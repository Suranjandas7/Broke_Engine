"""
Historical data fetching service.
Handles API calls to Zerodha Kite with rate limiting and chunking logic.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from kiteconnect import KiteConnect

from app.database.instruments import get_instrument_by_key
from app.database.historical_data import (
    get_last_timestamp,
    check_year_cached,
    get_cache_metadata
)

logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_DELAY = 0.35  # seconds between API calls (allows ~2.86 req/sec, safe for 3 req/sec limit)

# Kite API limits
MAX_DAYS_PER_REQUEST = 60  # Maximum days for 1-minute data

# Market hours (Indian stock market)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30


def is_option_instrument(instrument: Dict) -> bool:
    """
    Check if an instrument is an option (CE/PE) or futures contract.
    
    Args:
        instrument: Instrument dictionary from database
    
    Returns:
        True if instrument is an option/future (CE/PE/FUT), False otherwise
    
    Note:
        Options and futures have Open Interest (OI) data, while stocks don't.
        This is auto-detected from the instrument_type field in the database.
    """
    instrument_type = instrument.get('instrument_type', '').upper()
    is_option = instrument_type in ['CE', 'PE', 'FUT']
    
    if is_option:
        logger.info(
            f"Detected {instrument_type} instrument: "
            f"{instrument.get('tradingsymbol')}:{instrument.get('exchange')}"
        )
    
    return is_option


def validate_ticker_exists(ticker: str, exchange: str) -> Optional[Dict]:
    """
    Validate that ticker exists in instruments cache.
    
    Args:
        ticker: Trading symbol
        exchange: Exchange name
    
    Returns:
        Instrument dictionary if found, None otherwise
    """
    instrument = get_instrument_by_key(ticker, exchange)
    if not instrument:
        logger.warning(f"Ticker {ticker}:{exchange} not found in instruments cache")
        return None
    
    logger.info(f"Validated ticker {ticker}:{exchange} - token: {instrument['instrument_token']}")
    return instrument


def get_year_date_range(year: int, is_current_year: bool = False) -> Tuple[datetime, datetime]:
    """
    Get start and end datetime for a year, respecting market hours.
    For current year, ends at yesterday.
    
    Args:
        year: Year to get range for
        is_current_year: Whether this is the current year
    
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    start_dt = datetime(year, 1, 1, MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE, 0)
    
    if is_current_year:
        # End at yesterday's market close
        yesterday = datetime.now() - timedelta(days=1)
        end_dt = datetime(
            yesterday.year,
            yesterday.month,
            yesterday.day,
            MARKET_CLOSE_HOUR,
            MARKET_CLOSE_MINUTE,
            0
        )
    else:
        # End at year's last day market close
        end_dt = datetime(year, 12, 31, MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE, 0)
    
    return start_dt, end_dt


def chunk_date_range_into_intervals(
    start_dt: datetime,
    end_dt: datetime,
    max_days: int = MAX_DAYS_PER_REQUEST
) -> List[Tuple[datetime, datetime]]:
    """
    Split a date range into chunks of max_days.
    
    Args:
        start_dt: Start datetime
        end_dt: End datetime
        max_days: Maximum days per chunk (default 60)
    
    Returns:
        List of (from_datetime, to_datetime) tuples
    """
    chunks = []
    current = start_dt
    
    while current < end_dt:
        chunk_end = min(current + timedelta(days=max_days), end_dt)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(seconds=1)
    
    logger.info(f"Split date range into {len(chunks)} chunks of max {max_days} days")
    return chunks


def fetch_with_rate_limit(
    kite: KiteConnect,
    instrument_token: int,
    from_dt: datetime,
    to_dt: datetime,
    interval: str = "minute"
) -> List[Dict]:
    """
    Fetch historical data with rate limiting.
    Adds delay after each API call to respect rate limits.
    
    Args:
        kite: KiteConnect instance
        instrument_token: Instrument token
        from_dt: Start datetime
        to_dt: End datetime
        interval: Candle interval (default: "minute")
    
    Returns:
        List of candle dictionaries with OHLCV data
    
    Note:
        Kite's historical_data API returns only OHLCV (Open, High, Low, Close, Volume).
        It does NOT provide Open Interest (OI) data for options/futures.
        OI fields will be set to 0 in the database.
        
        Future Enhancement: Could add real-time OI tracking via WebSocket for
        current/future data, or make separate quote API calls for daily OI
        (though this would be very slow due to rate limits).
    """
    try:
        logger.info(f"Fetching data for token {instrument_token} from {from_dt} to {to_dt}")
        
        # Make API call
        data = kite.historical_data(
            instrument_token=instrument_token,
            from_date=from_dt,
            to_date=to_dt,
            interval=interval
        )
        
        # Rate limiting delay
        time.sleep(RATE_LIMIT_DELAY)
        
        logger.info(f"Fetched {len(data)} records")
        return data
        
    except Exception as e:
        logger.error(f"Error fetching data: {e}", exc_info=True)
        raise


def format_candle_data(candles: List[Dict]) -> List[Dict]:
    """
    Format candle data from Kite API to standard format.
    Converts datetime objects to string format.
    
    Args:
        candles: List of candle dictionaries from Kite API
    
    Returns:
        List of formatted candle dictionaries
    """
    formatted = []
    
    for candle in candles:
        formatted.append({
            'date': candle['date'].strftime('%Y-%m-%d %H:%M:%S'),
            'open': float(candle['open']),
            'high': float(candle['high']),
            'low': float(candle['low']),
            'close': float(candle['close']),
            'volume': int(candle['volume'])
        })
    
    return formatted


def determine_fetch_range(
    ticker: str,
    exchange: str,
    year: int,
    is_current_year: bool = False
) -> Optional[Tuple[datetime, datetime]]:
    """
    Determine what date range to fetch based on cache status (update mode).
    
    Args:
        ticker: Trading symbol
        exchange: Exchange name
        year: Year to fetch
        is_current_year: Whether this is the current year
    
    Returns:
        Tuple of (start_datetime, end_datetime) or None if fully cached
    """
    # Get full year range
    year_start, year_end = get_year_date_range(year, is_current_year)
    
    # Check if year is already cached
    last_timestamp_str = get_last_timestamp(ticker, exchange, year)
    
    if not last_timestamp_str:
        # No cache exists, fetch full year
        logger.info(f"No cache found for {ticker}:{exchange} year {year}, fetching full year")
        return (year_start, year_end)
    
    # Parse last timestamp
    last_timestamp = datetime.strptime(last_timestamp_str, '%Y-%m-%d %H:%M:%S')
    
    # If current year, check if we need to update
    if is_current_year:
        yesterday_close = year_end
        if last_timestamp >= yesterday_close:
            logger.info(f"Cache for {ticker}:{exchange} year {year} is up to date (last: {last_timestamp_str})")
            return None
        
        # Fetch from last timestamp + 1 minute to yesterday
        fetch_start = last_timestamp + timedelta(minutes=1)
        logger.info(f"Updating cache for {ticker}:{exchange} year {year} from {fetch_start} to {yesterday_close}")
        return (fetch_start, yesterday_close)
    
    # For past years, if cached, consider it complete
    else:
        metadata = get_cache_metadata(ticker, exchange, year)
        if metadata and metadata.get('record_count', 0) > 0:
            logger.info(f"Year {year} already cached for {ticker}:{exchange} with {metadata['record_count']} records")
            return None
        
        # Edge case: metadata exists but no records, refetch full year
        logger.warning(f"Metadata exists but no records for {ticker}:{exchange} year {year}, refetching")
        return (year_start, year_end)


def fetch_year_data(
    kite: KiteConnect,
    ticker: str,
    exchange: str,
    year: int,
    instrument_token: int
) -> Tuple[List[Dict], str]:
    """
    Fetch historical 1-minute data for an entire year (or remaining portion in update mode).
    Automatically chunks requests into 60-day intervals.
    
    Args:
        kite: KiteConnect instance
        ticker: Trading symbol
        exchange: Exchange name
        year: Year to fetch
        instrument_token: Kite instrument token
    
    Returns:
        Tuple of (list of formatted candles, last timestamp)
    """
    current_year = datetime.now().year
    is_current_year = (year == current_year)
    
    # Determine what range to fetch (update mode logic)
    fetch_range = determine_fetch_range(ticker, exchange, year, is_current_year)
    
    if fetch_range is None:
        # Already fully cached
        return ([], None)
    
    start_dt, end_dt = fetch_range
    
    # Split into 60-day chunks
    chunks = chunk_date_range_into_intervals(start_dt, end_dt, MAX_DAYS_PER_REQUEST)
    
    logger.info(f"Fetching {ticker}:{exchange} year {year} in {len(chunks)} chunks")
    
    # Fetch all chunks
    all_candles = []
    
    for i, (chunk_start, chunk_end) in enumerate(chunks, 1):
        logger.info(f"Fetching chunk {i}/{len(chunks)}: {chunk_start} to {chunk_end}")
        
        try:
            chunk_data = fetch_with_rate_limit(
                kite,
                instrument_token,
                chunk_start,
                chunk_end,
                interval="minute"
            )
            
            if chunk_data:
                all_candles.extend(chunk_data)
                logger.info(f"Chunk {i}/{len(chunks)} complete: {len(chunk_data)} records")
            else:
                logger.warning(f"Chunk {i}/{len(chunks)} returned no data (possible non-trading period)")
        
        except Exception as e:
            logger.error(f"Failed to fetch chunk {i}/{len(chunks)}: {e}")
            raise
    
    # Format the data
    formatted_candles = format_candle_data(all_candles)
    
    # Get last timestamp
    last_timestamp = formatted_candles[-1]['date'] if formatted_candles else None
    
    logger.info(f"Completed fetching {ticker}:{exchange} year {year}: {len(formatted_candles)} total records")
    
    return (formatted_candles, last_timestamp)


def fetch_multiple_years(
    kite: KiteConnect,
    ticker: str,
    exchange: str,
    start_year: int,
    end_year: int,
    instrument_token: int
) -> Dict[int, Tuple[List[Dict], str]]:
    """
    Fetch historical data for multiple years.
    
    Args:
        kite: KiteConnect instance
        ticker: Trading symbol
        exchange: Exchange name
        start_year: Start year (inclusive)
        end_year: End year (inclusive)
        instrument_token: Kite instrument token
    
    Returns:
        Dictionary mapping year -> (candles, last_timestamp)
    """
    results = {}
    
    for year in range(start_year, end_year + 1):
        logger.info(f"Processing year {year} for {ticker}:{exchange}")
        
        try:
            candles, last_timestamp = fetch_year_data(
                kite,
                ticker,
                exchange,
                year,
                instrument_token
            )
            
            results[year] = (candles, last_timestamp)
            
        except Exception as e:
            logger.error(f"Failed to fetch year {year} for {ticker}:{exchange}: {e}")
            raise
    
    return results


def estimate_fetch_time(year: int, is_update_mode: bool = False) -> float:
    """
    Estimate how long a fetch will take.
    
    Args:
        year: Year to fetch
        is_update_mode: Whether update mode (partial fetch)
    
    Returns:
        Estimated time in seconds
    """
    days_in_year = 365
    chunks_needed = (days_in_year // MAX_DAYS_PER_REQUEST) + 1
    
    if is_update_mode:
        # Assume partial year, use conservative estimate
        chunks_needed = max(1, chunks_needed // 2)
    
    # Each chunk: API call (~0.5s) + rate limit delay (~0.35s)
    time_per_chunk = 0.85
    
    estimated_time = chunks_needed * time_per_chunk
    
    return estimated_time
