"""Authentication token database operations."""

import logging
from .connection import get_db_connection, db_lock


def init_auth_db():
    """Initialize authentication token storage."""
    with db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    access_token TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            logging.info("Auth token database initialized")


def save_access_token(access_token: str) -> bool:
    """Save or update access token in database."""
    with db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO auth_tokens (id, access_token, updated_at)
                VALUES (1, ?, CURRENT_TIMESTAMP)
            ''', (access_token,))
            conn.commit()
            return True


def get_access_token():
    """Retrieve current access token from database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT access_token FROM auth_tokens WHERE id = 1')
        row = cursor.fetchone()
        return row['access_token'] if row else None


def clear_access_token() -> bool:
    """Remove stored access token."""
    with db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM auth_tokens WHERE id = 1')
            conn.commit()
            return True
