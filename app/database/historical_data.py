"""
Historical data database operations for caching 1-minute OHLCV data.
Uses per-ticker table approach with metadata tracking.
"""

import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from threading import Lock
import pandas as pd
from .connection import DB_PATH, db_lock, get_db_connection

logger = logging.getLogger(__name__)

def sanitize_table_name(ticker: str, exchange: str) -> str:
    """
    Sanitize ticker and exchange to create valid SQLite table name.
    Replaces special characters with underscores.
    
    Args:
        ticker: Trading symbol (e.g., "SBIN", "NIFTY-50")
        exchange: Exchange name (e.g., "NSE", "BSE")
    
    Returns:
        Sanitized table name (e.g., "SBIN_NSE_history", "NIFTY_50_NSE_history")
    """
    safe_ticker = ticker.replace("-", "_").replace(" ", "_").upper()
    safe_exchange = exchange.replace("-", "_").replace(" ", "_").upper()
    return f"{safe_ticker}_{safe_exchange}_history"


def init_historical_db():
    """
    Initialize historical data database.
    Creates metadata table for tracking cached data.
    """
    with db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historical_data_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    instrument_token INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    last_timestamp TEXT,
                    record_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker, exchange, year)
                )
            """)
            
            # Create indexes for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_ticker 
                ON historical_data_cache(ticker, exchange)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_year 
                ON historical_data_cache(year)
            """)
            
            conn.commit()
            logger.info("Historical data database initialized successfully")


def create_ticker_table(ticker: str, exchange: str) -> str:
    """
    Create per-ticker history table if it doesn't exist.
    
    Args:
        ticker: Trading symbol
        exchange: Exchange name
    
    Returns:
        Table name created
    """
    table_name = sanitize_table_name(ticker, exchange)
    
    with db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create table with timestamp as primary key
            # Includes OI (Open Interest) columns for options support
            # OI fields will be 0 for stocks, populated for options
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    timestamp TEXT PRIMARY KEY,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    oi REAL DEFAULT 0,
                    oi_day_high REAL DEFAULT 0,
                    oi_day_low REAL DEFAULT 0,
                    year INTEGER NOT NULL
                )
            """)
            
            # Create indexes for fast year-based queries
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_year 
                ON {table_name}(year)
            """)
            
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp 
                ON {table_name}(timestamp)
            """)
            
            # Create composite index for optimized year+timestamp range queries
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_year_timestamp 
                ON {table_name}(year, timestamp)
            """)
            
            conn.commit()
            logger.info(f"Created table: {table_name}")
    
    return table_name


def get_cache_metadata(ticker: str, exchange: str, year: int) -> Optional[Dict]:
    """
    Get cache metadata for a specific ticker and year.
    
    Args:
        ticker: Trading symbol
        exchange: Exchange name
        year: Year to check
    
    Returns:
        Dictionary with cache metadata or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM historical_data_cache
            WHERE ticker = ? AND exchange = ? AND year = ?
        """, (ticker, exchange, year))
        
        row = cursor.fetchone()
        return dict(row) if row else None


def get_last_timestamp(ticker: str, exchange: str, year: int) -> Optional[str]:
    """
    Get the last cached timestamp for a ticker and year.
    Used for update mode to determine where to resume fetching.
    
    Args:
        ticker: Trading symbol
        exchange: Exchange name
        year: Year to check
    
    Returns:
        Last timestamp string (YYYY-MM-DD HH:MM:SS) or None
    """
    metadata = get_cache_metadata(ticker, exchange, year)
    return metadata['last_timestamp'] if metadata else None


def check_year_cached(ticker: str, exchange: str, year: int) -> bool:
    """
    Check if a specific year is cached for a ticker.
    
    Args:
        ticker: Trading symbol
        exchange: Exchange name
        year: Year to check
    
    Returns:
        True if year has cached data, False otherwise
    """
    metadata = get_cache_metadata(ticker, exchange, year)
    return metadata is not None and metadata.get('record_count', 0) > 0


def update_cache_metadata(
    ticker: str,
    exchange: str,
    instrument_token: int,
    year: int,
    last_timestamp: str,
    records_added: int
):
    """
    Update cache metadata after fetching data.
    
    Args:
        ticker: Trading symbol
        exchange: Exchange name
        instrument_token: Kite instrument token
        year: Year that was fetched
        last_timestamp: Last timestamp in the fetched data
        records_added: Number of records added in this fetch
    """
    table_name = sanitize_table_name(ticker, exchange)
    
    with db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if metadata exists
            existing = get_cache_metadata(ticker, exchange, year)
            
            if existing:
                # Update existing record
                new_count = existing['record_count'] + records_added
                cursor.execute("""
                    UPDATE historical_data_cache
                    SET last_timestamp = ?,
                        record_count = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE ticker = ? AND exchange = ? AND year = ?
                """, (last_timestamp, new_count, ticker, exchange, year))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO historical_data_cache
                    (ticker, exchange, table_name, instrument_token, year, last_timestamp, record_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ticker, exchange, table_name, instrument_token, year, last_timestamp, records_added))
            
            conn.commit()
            logger.info(f"Updated metadata for {ticker}:{exchange} year {year} - {records_added} records added")


def insert_historical_data(ticker: str, exchange: str, data: List[Dict]) -> int:
    """
    Bulk insert historical OHLCV data into ticker-specific table.
    Uses INSERT OR REPLACE to handle duplicate timestamps.
    
    Args:
        ticker: Trading symbol
        exchange: Exchange name
        data: List of candle dictionaries with keys: date, open, high, low, close, volume
              Optional keys: oi, oi_day_high, oi_day_low (for options)
    
    Returns:
        Number of records inserted
    
    Note:
        OI (Open Interest) fields are optional and default to 0.
        Kite's historical_data API doesn't provide OI, so these will be 0 initially.
    """
    if not data:
        return 0
    
    table_name = sanitize_table_name(ticker, exchange)
    
    # Ensure table exists
    create_ticker_table(ticker, exchange)
    
    # Prepare data for bulk insert
    records = []
    for candle in data:
        timestamp = candle['date']
        year = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').year
        
        # Extract OI fields (default to 0 if not present)
        oi = candle.get('oi', 0)
        oi_day_high = candle.get('oi_day_high', 0)
        oi_day_low = candle.get('oi_day_low', 0)
        
        records.append((
            timestamp,
            candle['open'],
            candle['high'],
            candle['low'],
            candle['close'],
            candle['volume'],
            oi,
            oi_day_high,
            oi_day_low,
            year
        ))
    
    with db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Bulk insert with REPLACE to handle duplicates
            cursor.executemany(f"""
                INSERT OR REPLACE INTO {table_name}
                (timestamp, open, high, low, close, volume, oi, oi_day_high, oi_day_low, year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records)
            
            conn.commit()
            count = cursor.rowcount
            logger.info(f"Inserted {count} records into {table_name}")
    
    return count


def get_historical_data(
    ticker: str,
    exchange: str,
    from_year: int,
    to_year: int
) -> List[Dict]:
    """
    Retrieve historical data for a ticker across a year range.
    
    Args:
        ticker: Trading symbol
        exchange: Exchange name
        from_year: Start year (inclusive)
        to_year: End year (inclusive)
    
    Returns:
        List of candle dictionaries sorted by timestamp
    """
    table_name = sanitize_table_name(ticker, exchange)
    
    with get_db_connection() as conn:
        # Use pandas read_sql for faster DataFrame loading
        query = f"""
            SELECT timestamp as date, open, high, low, close, volume, 
                   oi, oi_day_high, oi_day_low
            FROM {table_name}
            WHERE year >= ? AND year <= ?
            ORDER BY timestamp ASC
        """
        
        df = pd.read_sql_query(query, conn, params=(from_year, to_year))
        
        # Convert DataFrame to list of dictionaries
        data = df.to_dict('records')
        logger.info(f"Retrieved {len(data)} records from {table_name} for years {from_year}-{to_year}")
    
    return data


def get_historical_data_by_date_range(
    ticker: str,
    exchange: str,
    from_date: str,
    to_date: str
) -> List[Dict]:
    """
    Retrieve historical data by specific date range.
    
    Args:
        ticker: Trading symbol
        exchange: Exchange name
        from_date: Start datetime (YYYY-MM-DD HH:MM:SS)
        to_date: End datetime (YYYY-MM-DD HH:MM:SS)
    
    Returns:
        List of candle dictionaries sorted by timestamp
        
    Raises:
        ValueError: If no data exists in the specified date range
    """
    table_name = sanitize_table_name(ticker, exchange)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if table exists first
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        
        if not cursor.fetchone():
            raise ValueError(f"No cached data found for {ticker}:{exchange}")
        
        # Use pandas read_sql for faster DataFrame loading
        query = f"""
            SELECT timestamp as date, open, high, low, close, volume,
                   oi, oi_day_high, oi_day_low
            FROM {table_name}
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
        """
        
        df = pd.read_sql_query(query, conn, params=(from_date, to_date))
        
        # Strict validation: error if no data
        if df.empty:
            raise ValueError(
                f"No cached data found for {ticker}:{exchange} "
                f"between {from_date} and {to_date}. "
                f"Please fetch this date range first using /fetch_history."
            )
        
        # Convert DataFrame to list of dictionaries
        data = df.to_dict('records')
        logger.info(
            f"Retrieved {len(data)} records from {table_name} "
            f"for date range {from_date} to {to_date}"
        )
    
    return data


def get_all_cached_tickers() -> List[Dict]:
    """
    Get list of all tickers with cached data.
    
    Returns:
        List of dictionaries with ticker, exchange, years, and record counts
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticker, exchange, 
                   GROUP_CONCAT(year) as years,
                   SUM(record_count) as total_records
            FROM historical_data_cache
            GROUP BY ticker, exchange
            ORDER BY ticker, exchange
        """)
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_cache_statistics() -> Dict:
    """
    Get overall cache statistics.
    
    Returns:
        Dictionary with cache stats (total tickers, years, records, db size)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Count unique tickers
        cursor.execute("""
            SELECT COUNT(DISTINCT ticker || ':' || exchange) as ticker_count
            FROM historical_data_cache
        """)
        ticker_count = cursor.fetchone()['ticker_count']
        
        # Count total years cached
        cursor.execute("""
            SELECT COUNT(*) as year_count
            FROM historical_data_cache
        """)
        year_count = cursor.fetchone()['year_count']
        
        # Sum total records
        cursor.execute("""
            SELECT SUM(record_count) as total_records
            FROM historical_data_cache
        """)
        total_records = cursor.fetchone()['total_records'] or 0
        
    # Get database file size
    import os
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    
    return {
        'total_tickers': ticker_count,
        'total_years_cached': year_count,
        'total_records': total_records,
        'database_size_mb': round(db_size / (1024 * 1024), 2)
    }


def delete_year_cache(ticker: str, exchange: str, year: int) -> bool:
    """
    Delete cached data for a specific ticker and year.
    
    Args:
        ticker: Trading symbol
        exchange: Exchange name
        year: Year to delete
    
    Returns:
        True if deletion successful, False otherwise
    """
    table_name = sanitize_table_name(ticker, exchange)
    
    with db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Delete data from ticker table
            cursor.execute(f"""
                DELETE FROM {table_name}
                WHERE year = ?
            """, (year,))
            
            # Delete metadata entry
            cursor.execute("""
                DELETE FROM historical_data_cache
                WHERE ticker = ? AND exchange = ? AND year = ?
            """, (ticker, exchange, year))
            
            conn.commit()
            logger.info(f"Deleted cache for {ticker}:{exchange} year {year}")
    
    return True
