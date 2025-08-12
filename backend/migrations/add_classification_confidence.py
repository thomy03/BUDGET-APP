#!/usr/bin/env python3
"""
Migration: Add confidence_score and classification_source to transactions table
Version: 2025-08-12_001
Author: Claude Code - Backend API Architect

Adds support for ML confidence tracking and classification source attribution:
- confidence_score: Float (0.0-1.0) for AI classification confidence
- classification_source: String to track classification origin (AI, USER, BATCH, etc.)
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Migration metadata
MIGRATION_VERSION = "2025-08-12_001"
MIGRATION_NAME = "add_classification_confidence"

def get_database_path():
    """Get database path relative to script location"""
    script_dir = Path(__file__).parent.parent
    return script_dir / "budget.db"

def migration_up(db_path: str = None):
    """
    Apply migration: Add confidence_score and classification_source columns
    
    Args:
        db_path: Path to database file (optional, defaults to standard location)
    """
    if db_path is None:
        db_path = str(get_database_path())
    
    logger.info(f"🔄 Starting migration {MIGRATION_VERSION}: {MIGRATION_NAME}")
    logger.info(f"Database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(transactions);")
        columns = [row[1] for row in cursor.fetchall()]
        
        changes_applied = 0
        
        # Add confidence_score column if it doesn't exist
        if 'confidence_score' not in columns:
            logger.info("Adding confidence_score column...")
            cursor.execute("""
                ALTER TABLE transactions 
                ADD COLUMN confidence_score FLOAT DEFAULT 0.5
            """)
            changes_applied += 1
            logger.info("✅ confidence_score column added")
        else:
            logger.info("ℹ️ confidence_score column already exists")
        
        # Add classification_source column if it doesn't exist
        if 'classification_source' not in columns:
            logger.info("Adding classification_source column...")
            cursor.execute("""
                ALTER TABLE transactions 
                ADD COLUMN classification_source VARCHAR(50) DEFAULT 'UNKNOWN'
            """)
            changes_applied += 1
            logger.info("✅ classification_source column added")
        else:
            logger.info("ℹ️ classification_source column already exists")
        
        # Create index for performance on confidence_score queries
        if changes_applied > 0:
            logger.info("Creating performance indexes...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_confidence_score 
                ON transactions (confidence_score, expense_type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_classification_source 
                ON transactions (classification_source, month)
            """)
            logger.info("✅ Performance indexes created")
        
        # Update existing classifications to have proper metadata
        if changes_applied > 0:
            logger.info("Updating existing transaction classifications...")
            
            # Set confidence_score based on existing expense_type
            cursor.execute("""
                UPDATE transactions 
                SET confidence_score = CASE 
                    WHEN expense_type = 'FIXED' AND tags != '' THEN 0.8
                    WHEN expense_type = 'VARIABLE' AND tags != '' THEN 0.7
                    ELSE 0.5
                END,
                classification_source = CASE
                    WHEN expense_type IN ('FIXED', 'VARIABLE') AND tags != '' THEN 'LEGACY_MIGRATION'
                    ELSE 'UNKNOWN'
                END
                WHERE confidence_score = 0.5 AND classification_source = 'UNKNOWN'
            """)
            
            updated_rows = cursor.rowcount
            logger.info(f"✅ Updated {updated_rows} existing transactions with confidence metadata")
        
        # Commit all changes
        conn.commit()
        logger.info(f"✅ Migration {MIGRATION_VERSION} completed successfully")
        logger.info(f"Changes applied: {changes_applied} columns added")
        
        # Verify the migration
        cursor.execute("PRAGMA table_info(transactions);")
        all_columns = [row[1] for row in cursor.fetchall()]
        
        required_columns = ['confidence_score', 'classification_source']
        missing_columns = [col for col in required_columns if col not in all_columns]
        
        if missing_columns:
            raise Exception(f"Migration verification failed - missing columns: {missing_columns}")
        
        logger.info("✅ Migration verification passed - all required columns present")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

def migration_down(db_path: str = None):
    """
    Rollback migration: Remove confidence_score and classification_source columns
    
    Note: SQLite doesn't support DROP COLUMN directly, so we'll use table recreation
    
    Args:
        db_path: Path to database file (optional, defaults to standard location)
    """
    if db_path is None:
        db_path = str(get_database_path())
    
    logger.info(f"🔄 Rolling back migration {MIGRATION_VERSION}: {MIGRATION_NAME}")
    logger.warning("⚠️ This rollback will remove confidence and classification source data!")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create backup table with original schema
        logger.info("Creating backup table with original schema...")
        cursor.execute("""
            CREATE TABLE transactions_backup AS
            SELECT 
                id, month, date_op, label, category, category_parent,
                amount, account_label, is_expense, exclude, row_id, 
                tags, import_id, expense_type
            FROM transactions
        """)
        
        # Drop original table
        logger.info("Dropping original transactions table...")
        cursor.execute("DROP TABLE transactions")
        
        # Recreate table with original schema
        logger.info("Recreating transactions table with original schema...")
        cursor.execute("""
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY,
                month VARCHAR,
                date_op DATE,
                label TEXT DEFAULT '',
                category TEXT DEFAULT '',
                category_parent TEXT DEFAULT '',
                amount FLOAT DEFAULT 0.0,
                account_label TEXT DEFAULT '',
                is_expense BOOLEAN DEFAULT 0,
                exclude BOOLEAN DEFAULT 0,
                row_id VARCHAR,
                tags TEXT DEFAULT '',
                import_id TEXT,
                expense_type TEXT DEFAULT 'VARIABLE'
            )
        """)
        
        # Restore data from backup
        logger.info("Restoring data from backup...")
        cursor.execute("""
            INSERT INTO transactions 
            SELECT * FROM transactions_backup
        """)
        
        # Recreate original indexes
        logger.info("Recreating original indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_transactions_month ON transactions (month)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_transactions_date_op ON transactions (date_op)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_transactions_exclude ON transactions (exclude)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_transactions_expense_type ON transactions (expense_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_transactions_row_id ON transactions (row_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_transactions_import_id ON transactions (import_id)")
        
        # Drop backup table
        logger.info("Cleaning up backup table...")
        cursor.execute("DROP TABLE transactions_backup")
        
        # Commit rollback
        conn.commit()
        logger.info(f"✅ Migration {MIGRATION_VERSION} rollback completed successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration rollback failed: {str(e)}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

def get_migration_status(db_path: str = None):
    """
    Check if migration has been applied
    
    Args:
        db_path: Path to database file (optional, defaults to standard location)
    
    Returns:
        dict: Migration status information
    """
    if db_path is None:
        db_path = str(get_database_path())
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("PRAGMA table_info(transactions);")
        columns = [row[1] for row in cursor.fetchall()]
        
        has_confidence = 'confidence_score' in columns
        has_source = 'classification_source' in columns
        
        # Count transactions with confidence data
        confidence_count = 0
        if has_confidence:
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE confidence_score != 0.5")
            confidence_count = cursor.fetchone()[0]
        
        status = {
            'migration_applied': has_confidence and has_source,
            'has_confidence_score': has_confidence,
            'has_classification_source': has_source,
            'transactions_with_confidence': confidence_count,
            'migration_version': MIGRATION_VERSION,
            'migration_name': MIGRATION_NAME
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        return {'error': str(e)}
        
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python add_classification_confidence.py [up|down|status] [db_path]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    db_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if command == "up":
        success = migration_up(db_path)
        sys.exit(0 if success else 1)
    elif command == "down":
        success = migration_down(db_path)
        sys.exit(0 if success else 1)
    elif command == "status":
        status = get_migration_status(db_path)
        print(f"Migration Status: {status}")
        sys.exit(0)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)