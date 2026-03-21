"""Database module for broke_engine."""

from .connection import get_db_connection, DB_PATH, db_lock
from .instruments import (
    init_instruments_db,
    populate_instruments_db,
    get_instrument_by_key,
    search_instruments_by_symbol,
    get_instruments_count,
    check_cache_exists
)
from .auth_tokens import (
    init_auth_db,
    save_access_token,
    get_access_token,
    clear_access_token
)

__all__ = [
    'get_db_connection',
    'DB_PATH',
    'db_lock',
    'init_instruments_db',
    'populate_instruments_db',
    'get_instrument_by_key',
    'search_instruments_by_symbol',
    'get_instruments_count',
    'check_cache_exists',
    'init_auth_db',
    'save_access_token',
    'get_access_token',
    'clear_access_token'
]
