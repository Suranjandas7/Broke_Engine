"""Database connection management."""

import os
import sqlite3
import threading
from contextlib import contextmanager

# SQLite database configuration for instruments cache
# Use data directory for persistence in Docker
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, 'instruments.db')
db_lock = threading.Lock()  # Thread safety for SQLite operations


@contextmanager
def get_db_connection():
    """Context manager for SQLite database connections."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    try:
        yield conn
    finally:
        conn.close()
