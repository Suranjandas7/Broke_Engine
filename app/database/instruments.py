"""Instruments database operations."""

import os
import logging
from .connection import get_db_connection, db_lock, DB_PATH


def init_instruments_db():
    """Initialize the instruments database table with indexes."""
    with db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS instruments (
                    tradingsymbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    instrument_token INTEGER PRIMARY KEY,
                    exchange_token INTEGER,
                    name TEXT,
                    last_price REAL,
                    expiry TEXT,
                    strike REAL,
                    tick_size REAL,
                    lot_size INTEGER,
                    instrument_type TEXT,
                    segment TEXT,
                    UNIQUE(tradingsymbol, exchange)
                )
            ''')
            # Create index for fast tradingsymbol lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tradingsymbol 
                ON instruments(tradingsymbol)
            ''')
            conn.commit()
            logging.info("Instruments database initialized")


def populate_instruments_db(instruments):
    """Bulk insert instruments into SQLite database using transactions."""
    with db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Clear existing data
            cursor.execute('DELETE FROM instruments')
            
            # Prepare data for bulk insert
            data = []
            for instrument in instruments:
                data.append((
                    instrument['tradingsymbol'],
                    instrument['exchange'],
                    instrument['instrument_token'],
                    instrument['exchange_token'],
                    instrument.get('name', ''),
                    instrument.get('last_price', 0),
                    str(instrument.get('expiry', '')),
                    instrument.get('strike', 0),
                    instrument.get('tick_size', 0),
                    instrument.get('lot_size', 0),
                    instrument.get('instrument_type', ''),
                    instrument.get('segment', '')
                ))
            
            # Bulk insert with transaction
            cursor.executemany('''
                INSERT OR REPLACE INTO instruments 
                (tradingsymbol, exchange, instrument_token, exchange_token, 
                 name, last_price, expiry, strike, tick_size, lot_size, 
                 instrument_type, segment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)
            
            conn.commit()
            return len(data)


def get_instrument_by_key(tradingsymbol, exchange):
    """Get a single instrument by tradingsymbol and exchange."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM instruments 
            WHERE tradingsymbol = ? AND exchange = ?
        ''', (tradingsymbol, exchange))
        row = cursor.fetchone()
        
        return _row_to_dict(row) if row else None


def _row_to_dict(row):
    """Convert a database row to instrument dictionary."""
    return {
        'instrument_token': row['instrument_token'],
        'exchange_token': row['exchange_token'],
        'tradingsymbol': row['tradingsymbol'],
        'exchange': row['exchange'],
        'name': row['name'],
        'last_price': row['last_price'],
        'expiry': row['expiry'],
        'strike': row['strike'],
        'tick_size': row['tick_size'],
        'lot_size': row['lot_size'],
        'instrument_type': row['instrument_type'],
        'segment': row['segment']
    }


def search_instruments_by_symbol(tradingsymbol):
    """Search for all instruments matching a tradingsymbol across exchanges."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM instruments 
            WHERE tradingsymbol = ?
        ''', (tradingsymbol,))
        rows = cursor.fetchall()
        
        return [_row_to_dict(row) for row in rows]


def get_instruments_count():
    """Get the total count of instruments in the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM instruments')
        row = cursor.fetchone()
        return row['count'] if row else 0


def check_cache_exists():
    """Check if the instruments cache database exists and has data."""
    if not os.path.exists(DB_PATH):
        return False
    
    try:
        count = get_instruments_count()
        return count > 0
    except Exception:
        return False
