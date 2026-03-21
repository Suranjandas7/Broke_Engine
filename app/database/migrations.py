"""
Database migration utilities for schema updates.
"""

import logging
import sqlite3
from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


def run_migrations():
    """
    Run all pending database migrations on startup.
    This function is idempotent - safe to run multiple times.
    """
    logger.info("Starting database migrations...")
    
    try:
        add_oi_columns_to_historical_tables()
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Error running migrations: {e}", exc_info=True)
        # Don't raise - allow app to start even if migrations fail
        # (in case it's just missing tables, which is fine)


def add_oi_columns_to_historical_tables():
    """
    Add Open Interest (OI) columns to existing historical data tables.
    
    Adds three columns to all *_history tables:
    - oi: Open Interest value (default 0)
    - oi_day_high: Highest OI during the day (default 0)
    - oi_day_low: Lowest OI during the day (default 0)
    
    These columns are essential for options analysis but will be 0 for stocks.
    Note: Kite's historical_data API doesn't provide historical OI, so these
    will be 0 initially. Future enhancements could add real-time OI tracking.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            # Get all table names that end with '_history'
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE '%_history'
            """)
            
            history_tables = [row[0] for row in cursor.fetchall()]
            
            if not history_tables:
                logger.info("No historical data tables found - skipping OI column migration")
                return
            
            logger.info(f"Found {len(history_tables)} historical data tables")
            
            migrated_count = 0
            skipped_count = 0
            
            for table_name in history_tables:
                # Check if OI columns already exist
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'oi' in columns:
                    # Columns already exist, skip
                    skipped_count += 1
                    continue
                
                # Add OI columns
                logger.info(f"Adding OI columns to table: {table_name}")
                
                try:
                    # SQLite doesn't support adding multiple columns at once
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN oi REAL DEFAULT 0")
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN oi_day_high REAL DEFAULT 0")
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN oi_day_low REAL DEFAULT 0")
                    
                    migrated_count += 1
                    logger.info(f"Successfully added OI columns to {table_name}")
                    
                except sqlite3.OperationalError as e:
                    # Column might already exist from partial migration
                    if "duplicate column name" in str(e).lower():
                        logger.debug(f"OI columns already exist in {table_name} (partial migration)")
                        skipped_count += 1
                    else:
                        raise
            
            conn.commit()
            
            logger.info(
                f"OI column migration complete: "
                f"{migrated_count} tables migrated, {skipped_count} tables already up-to-date"
            )
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add OI columns: {e}", exc_info=True)
            raise


def check_migration_status():
    """
    Check the migration status of historical data tables.
    
    Returns:
        dict: Migration status summary
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '%_history'
        """)
        
        history_tables = [row[0] for row in cursor.fetchall()]
        
        if not history_tables:
            return {
                "status": "no_tables",
                "message": "No historical data tables found",
                "total_tables": 0,
                "migrated_tables": 0,
                "pending_tables": 0
            }
        
        migrated_tables = []
        pending_tables = []
        
        for table_name in history_tables:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'oi' in columns and 'oi_day_high' in columns and 'oi_day_low' in columns:
                migrated_tables.append(table_name)
            else:
                pending_tables.append(table_name)
        
        return {
            "status": "complete" if not pending_tables else "pending",
            "message": f"{len(migrated_tables)}/{len(history_tables)} tables migrated",
            "total_tables": len(history_tables),
            "migrated_tables": len(migrated_tables),
            "pending_tables": len(pending_tables),
            "pending_table_names": pending_tables
        }
