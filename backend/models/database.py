"""
Database models and connection management for Budget API
"""
import logging
from typing import Optional, Generator, Dict
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, Date, DateTime, 
    Text, ForeignKey, Index, event
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from sqlalchemy.sql import func
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from config.settings import settings

logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()


def create_database_engine() -> Engine:
    """Create database engine with optimizations"""
    try:
        # Check if encrypted database is requested
        if settings.database.enable_encryption:
            from database_encrypted import get_encrypted_engine, verify_encrypted_db, migrate_to_encrypted_db
            
            if not verify_encrypted_db():
                logger.info("Migration to encrypted database required")
                if migrate_to_encrypted_db():
                    logger.info("✅ Migration to encrypted database successful")
                else:
                    logger.warning("❌ Migration failed - using standard database")
                    return _create_standard_engine()
            
            engine = get_encrypted_engine()
            logger.info("🔐 Using encrypted SQLCipher database")
            return engine
            
    except ImportError:
        logger.warning("⚠️ Encryption module unavailable - using standard database")
    except Exception as e:
        logger.error(f"Database encryption error: {e} - using standard database")
    
    return _create_standard_engine()


def _create_standard_engine() -> Engine:
    """Create standard SQLite engine with connection pooling"""
    engine = create_engine(
        settings.database.database_url,
        future=True,
        echo=settings.database.echo_sql,
        connect_args={
            "check_same_thread": False,
            "timeout": settings.database.connection_timeout
        },
        pool_pre_ping=settings.database.pool_pre_ping,
        pool_recycle=settings.database.pool_recycle,
        poolclass=StaticPool
    )
    logger.info("📁 Using standard SQLite database")
    return engine


# Global engine instance
engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database Models

class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    full_name = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    created_by = Column(String(50), nullable=True)
    
    # Critical authentication indexes
    __table_args__ = (
        Index('idx_users_username_active', 'username', 'is_active'),
        Index('idx_users_email_active', 'email', 'is_active'),
        Index('idx_users_active_admin', 'is_active', 'is_admin'),
        Index('idx_users_last_login', 'last_login'),
        Index('idx_users_locked_until', 'locked_until'),
    )


class Config(Base):
    """Configuration model for budget settings"""
    __tablename__ = "config"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Member configuration
    member1 = Column(String, default="diana")
    member2 = Column(String, default="thomas")
    rev1 = Column(Float, default=0.0)
    rev2 = Column(Float, default=0.0)
    
    # Split configuration
    split_mode = Column(String, default="revenus")  # revenus | manuel
    split1 = Column(Float, default=0.5)  # if manuel
    split2 = Column(Float, default=0.5)
    other_split_mode = Column(String, default="clé")  # clé|50/50
    
    # Variable expenses configuration
    var_percent = Column(Float, default=30.0)  # Percentage of income for variable expenses
    max_var = Column(Float, default=0.0)       # Maximum variable expenses ceiling
    min_fixed = Column(Float, default=0.0)     # Minimum fixed charges
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Legacy fields - kept temporarily for compatibility
    loan_equal = Column(Boolean, default=True, nullable=True)
    loan_amount = Column(Float, default=0.0, nullable=True)
    other_fixed_simple = Column(Boolean, default=True, nullable=True)
    other_fixed_monthly = Column(Float, default=0.0, nullable=True)
    taxe_fonciere_ann = Column(Float, default=0.0, nullable=True)
    copro_montant = Column(Float, default=0.0, nullable=True)
    copro_freq = Column(String, default="mensuelle", nullable=True)
    vac_percent = Column(Float, default=0.0, nullable=True)
    vac_base = Column(String, default="2", nullable=True)


class Transaction(Base):
    """Transaction model for budget entries"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    month = Column(String, index=True)  # "YYYY-MM" (derived from date_op)
    date_op = Column(Date, index=True, nullable=True)
    label = Column(Text, default="")
    category = Column(Text, default="")
    category_parent = Column(Text, default="")
    amount = Column(Float, default=0.0)
    account_label = Column(Text, default="")
    is_expense = Column(Boolean, default=False)
    exclude = Column(Boolean, default=False, index=True)
    row_id = Column(String, index=True)  # stable hash
    tags = Column(Text, default="")      # CSV of tags
    import_id = Column(String, nullable=True, index=True)  # UUID of the import that created this transaction
    
    # Critical composite indexes for high-performance queries
    __table_args__ = (
        # Core filtering indexes for dashboard and analytics
        Index('idx_transactions_month_exclude_expense', 'month', 'exclude', 'is_expense'),
        Index('idx_transactions_month_category', 'month', 'category'),
        Index('idx_transactions_date_exclude', 'date_op', 'exclude'),
        Index('idx_transactions_category_amount', 'category', 'amount'),
        
        # Import and audit indexes
        Index('idx_transactions_import_month', 'import_id', 'month'),
        Index('idx_transactions_row_id_unique', 'row_id'),
        
        # Search and filtering indexes
        Index('idx_transactions_tags_month', 'tags', 'month'),
        Index('idx_transactions_account_month', 'account_label', 'month'),
        
        # Performance critical compound indexes
        Index('idx_transactions_month_date_exclude', 'month', 'date_op', 'exclude'),
        Index('idx_transactions_expense_category_month', 'is_expense', 'category', 'month'),
    )


class FixedLine(Base):
    """Fixed expenses model"""
    __tablename__ = "fixed_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, default="")
    amount = Column(Float, default=0.0)
    freq = Column(String, default="mensuelle")  # mensuelle|trimestrielle|annuelle
    split_mode = Column(String, default="clé")  # clé|50/50|m1|m2|manuel
    split1 = Column(Float, default=0.5)         # used if manuel
    split2 = Column(Float, default=0.5)
    category = Column(String, default="autres")  # logement|transport|services|loisirs|santé|autres
    active = Column(Boolean, default=True, index=True)
    
    # Performance indexes for fixed lines
    __table_args__ = (
        Index('idx_fixed_lines_active_freq', 'active', 'freq'),
        Index('idx_fixed_lines_category_active', 'category', 'active'),
        Index('idx_fixed_lines_amount_active', 'amount', 'active'),
    )


class ImportMetadata(Base):
    """Import metadata for tracking CSV imports"""
    __tablename__ = "import_metadata"
    
    id = Column(String, primary_key=True)  # UUID of the import
    filename = Column(String, nullable=False)
    created_at = Column(Date, nullable=False, index=True)
    user_id = Column(String, nullable=True)  # For audit
    months_detected = Column(Text, nullable=True)  # JSON of detected months
    duplicates_count = Column(Integer, default=0)
    warnings = Column(Text, nullable=True)  # JSON of warnings
    processing_ms = Column(Integer, default=0)
    
    # Performance indexes for import metadata
    __table_args__ = (
        Index('idx_import_metadata_created_user', 'created_at', 'user_id'),
        Index('idx_import_metadata_filename_date', 'filename', 'created_at'),
    )


class ExportHistory(Base):
    """Export history tracking"""
    __tablename__ = "export_history"
    
    id = Column(String, primary_key=True)  # UUID of the export
    user_id = Column(String, nullable=False, index=True)
    format = Column(String, nullable=False)  # csv, excel, pdf, json, zip
    scope = Column(String, nullable=False)   # transactions, analytics, config, all
    created_at = Column(Date, nullable=False, index=True)
    filename = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    download_count = Column(Integer, default=0)
    filters_applied = Column(Text, nullable=True)  # JSON of applied filters
    processing_ms = Column(Integer, default=0)
    status = Column(String, default="completed", index=True)  # pending, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Performance indexes for export history
    __table_args__ = (
        Index('idx_export_history_user_date_status', 'user_id', 'created_at', 'status'),
        Index('idx_export_history_format_scope', 'format', 'scope'),
        Index('idx_export_history_status_date', 'status', 'created_at'),
    )


class CustomProvision(Base):
    """Custom provision model for flexible budget provisions"""
    __tablename__ = "custom_provisions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # e.g., "Investment", "Japan Trip", "Renovation"
    description = Column(String(500))  # Optional description
    
    # Calculation configuration
    percentage = Column(Float, nullable=False)  # Percentage of income (0-100)
    base_calculation = Column(String(20), default="total")  # "total", "member1", "member2", "fixed"
    fixed_amount = Column(Float, default=0)  # If base_calculation = "fixed"
    
    # Member split configuration
    split_mode = Column(String(20), default="key")  # "key", "50/50", "custom", "100/0", "0/100"
    split_member1 = Column(Float, default=50)  # Member 1 percentage if split_mode="custom"
    split_member2 = Column(Float, default=50)  # Member 2 percentage if split_mode="custom"
    
    # Display configuration
    icon = Column(String(50), default="💰")  # Emoji or icon name
    color = Column(String(7), default="#6366f1")  # Hexadecimal color
    display_order = Column(Integer, default=999)  # Display order
    
    # Status and metadata
    is_active = Column(Boolean, default=True, index=True)
    is_temporary = Column(Boolean, default=False)  # For temporary provisions
    start_date = Column(DateTime)  # Start date (optional)
    end_date = Column(DateTime)  # End date (optional)
    
    # Target and tracking
    target_amount = Column(Float)  # Target amount to reach
    current_amount = Column(Float, default=0)  # Amount already saved
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    created_by = Column(String(100))  # Username of creator
    
    # Category for grouping
    category = Column(String(50), default="custom")  # "savings", "investment", "project", "custom"
    
    # Enhanced indexes for custom provisions performance
    __table_args__ = (
        Index('idx_custom_provisions_active_created_by', 'is_active', 'created_by'),
        Index('idx_custom_provisions_active_dates', 'is_active', 'start_date', 'end_date'),
        Index('idx_custom_provisions_category_active', 'category', 'is_active'),
        Index('idx_custom_provisions_display_order_active', 'display_order', 'is_active', 'name'),
        Index('idx_custom_provisions_target_current', 'target_amount', 'current_amount'),
        Index('idx_custom_provisions_temporary_dates', 'is_temporary', 'start_date', 'end_date'),
    )


# Database events for optimization

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for optimal performance and monitoring"""
    if 'sqlite' in str(engine.url):
        cursor = dbapi_connection.cursor()
        
        # Performance optimizations
        cursor.execute("PRAGMA journal_mode=WAL")          # Better concurrency
        cursor.execute("PRAGMA synchronous=NORMAL")        # Balance safety/performance
        cursor.execute("PRAGMA cache_size=2000")           # Increased cache (2MB)
        cursor.execute("PRAGMA temp_store=MEMORY")         # In-memory temp tables
        cursor.execute("PRAGMA mmap_size=67108864")        # 64MB memory mapping
        cursor.execute("PRAGMA optimize")                  # Enable query optimizer
        
        # Query performance monitoring (development only)
        try:
            from config.settings import settings
            if hasattr(settings, 'database') and getattr(settings.database, 'enable_query_logging', False):
                # Enable query analysis for slow query detection
                cursor.execute("PRAGMA analysis_limit=1000")
                logger.info("Query performance monitoring enabled")
        except Exception:
            pass  # Fail silently if config not available
        
        cursor.close()
        logger.debug("SQLite performance pragmas applied")


def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def migrate_schema():
    """Enhanced schema migration with comprehensive performance indexes"""
    with engine.connect() as conn:
        try:
            # Migration for transactions table
            info = conn.exec_driver_sql("PRAGMA table_info('transactions')").fetchall()
            cols = [r[1] for r in info]
            
            if "tags" not in cols:
                conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN tags TEXT DEFAULT ''")
                logger.info("Added 'tags' column to transactions table")
                
            if "import_id" not in cols:
                conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN import_id TEXT")
                logger.info("Added 'import_id' column to transactions table")
            
            # Create comprehensive performance indexes
            critical_indexes = [
                # Transaction performance indexes - most critical for application performance
                "CREATE INDEX IF NOT EXISTS idx_transactions_month_exclude_expense ON transactions(month, exclude, is_expense)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_month_category ON transactions(month, category)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_date_exclude ON transactions(date_op, exclude)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_category_amount ON transactions(category, amount)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_import_month ON transactions(import_id, month)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_row_id_unique ON transactions(row_id)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_tags_month ON transactions(tags, month)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_account_month ON transactions(account_label, month)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_month_date_exclude ON transactions(month, date_op, exclude)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_expense_category_month ON transactions(is_expense, category, month)",
                
                # Fixed lines performance indexes
                "CREATE INDEX IF NOT EXISTS idx_fixed_lines_active_freq ON fixed_lines(active, freq)",
                "CREATE INDEX IF NOT EXISTS idx_fixed_lines_category_active ON fixed_lines(category, active)",
                "CREATE INDEX IF NOT EXISTS idx_fixed_lines_amount_active ON fixed_lines(amount, active)",
                
                # Custom provisions performance indexes
                "CREATE INDEX IF NOT EXISTS idx_custom_provisions_active_created_by ON custom_provisions(is_active, created_by)",
                "CREATE INDEX IF NOT EXISTS idx_custom_provisions_active_dates ON custom_provisions(is_active, start_date, end_date)",
                "CREATE INDEX IF NOT EXISTS idx_custom_provisions_category_active ON custom_provisions(category, is_active)",
                "CREATE INDEX IF NOT EXISTS idx_custom_provisions_display_order_active ON custom_provisions(display_order, is_active, name)",
                "CREATE INDEX IF NOT EXISTS idx_custom_provisions_target_current ON custom_provisions(target_amount, current_amount)",
                "CREATE INDEX IF NOT EXISTS idx_custom_provisions_temporary_dates ON custom_provisions(is_temporary, start_date, end_date)",
                
                # Import/Export metadata indexes
                "CREATE INDEX IF NOT EXISTS idx_import_metadata_created_user ON import_metadata(created_at, user_id)",
                "CREATE INDEX IF NOT EXISTS idx_import_metadata_filename_date ON import_metadata(filename, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_export_history_user_date_status ON export_history(user_id, created_at, status)",
                "CREATE INDEX IF NOT EXISTS idx_export_history_format_scope ON export_history(format, scope)",
                "CREATE INDEX IF NOT EXISTS idx_export_history_status_date ON export_history(status, created_at)",
                
                # Legacy indexes for compatibility
                "CREATE INDEX IF NOT EXISTS idx_transactions_import_id ON transactions(import_id)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_month_exclude ON transactions(month, exclude)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_category_month ON transactions(category, month)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_tags ON transactions(tags)",
                "CREATE INDEX IF NOT EXISTS idx_fixed_lines_active ON fixed_lines(active)",
                "CREATE INDEX IF NOT EXISTS idx_import_metadata_created_at ON import_metadata(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_export_history_user_created ON export_history(user_id, created_at)",
            ]
            
            logger.info(f"Creating {len(critical_indexes)} performance-critical database indexes...")
            
            for i, index_sql in enumerate(critical_indexes, 1):
                try:
                    conn.exec_driver_sql(index_sql)
                    if i % 10 == 0:  # Progress logging every 10 indexes
                        logger.info(f"Created {i}/{len(critical_indexes)} indexes...")
                except Exception as e:
                    logger.warning(f"Failed to create index {i}: {e}")
            
            logger.info("✅ Comprehensive database indexes created for optimal performance")
            
            # Migration for custom_provisions - check if table exists
            try:
                conn.exec_driver_sql("SELECT 1 FROM custom_provisions LIMIT 1")
                logger.info("Table custom_provisions already exists")
            except Exception:
                logger.info("Creating custom_provisions table with optimized structure")
                conn.exec_driver_sql("""
                    CREATE TABLE IF NOT EXISTS custom_provisions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(100) NOT NULL,
                        description VARCHAR(500),
                        percentage FLOAT NOT NULL,
                        base_calculation VARCHAR(20) DEFAULT 'total',
                        fixed_amount FLOAT DEFAULT 0,
                        split_mode VARCHAR(20) DEFAULT 'key',
                        split_member1 FLOAT DEFAULT 50,
                        split_member2 FLOAT DEFAULT 50,
                        icon VARCHAR(50) DEFAULT '💰',
                        color VARCHAR(7) DEFAULT '#6366f1',
                        display_order INTEGER DEFAULT 999,
                        is_active BOOLEAN DEFAULT TRUE,
                        is_temporary BOOLEAN DEFAULT FALSE,
                        start_date DATETIME,
                        end_date DATETIME,
                        target_amount FLOAT,
                        current_amount FLOAT DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME,
                        created_by VARCHAR(100),
                        category VARCHAR(50) DEFAULT 'custom'
                    )
                """)
                
                logger.info("✅ Table custom_provisions created successfully")
            
            # Migration for users table for enhanced authentication
            try:
                conn.exec_driver_sql("SELECT 1 FROM users LIMIT 1")
                logger.info("Table users already exists")
            except Exception:
                logger.info("Creating users table for enhanced authentication")
                conn.exec_driver_sql("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        email VARCHAR(100) UNIQUE,
                        full_name VARCHAR(100),
                        hashed_password VARCHAR(255) NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        is_admin BOOLEAN DEFAULT FALSE,
                        last_login DATETIME,
                        failed_login_attempts INTEGER DEFAULT 0,
                        locked_until DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME,
                        created_by VARCHAR(50)
                    )
                """)
                
                # Create authentication indexes
                auth_indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_users_username_active ON users(username, is_active)",
                    "CREATE INDEX IF NOT EXISTS idx_users_email_active ON users(email, is_active)",
                    "CREATE INDEX IF NOT EXISTS idx_users_active_admin ON users(is_active, is_admin)",
                    "CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login)",
                    "CREATE INDEX IF NOT EXISTS idx_users_locked_until ON users(locked_until)",
                ]
                
                for index_sql in auth_indexes:
                    conn.exec_driver_sql(index_sql)
                
                logger.info("✅ Table users created with authentication indexes")
            
            # Analyze query performance statistics
            try:
                conn.exec_driver_sql("ANALYZE")
                logger.info("Database statistics updated for query optimizer")
            except Exception as e:
                logger.warning(f"Could not update database statistics: {e}")
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Schema migration error: {e}")
            conn.rollback()
            raise


def ensure_default_config(db: Session):
    """Ensure default configuration exists"""
    cfg = db.query(Config).first()
    if not cfg:
        cfg = Config()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
        logger.info("Created default configuration")
    return cfg


def get_database_info():
    """Get comprehensive database information for monitoring and performance analysis"""
    with engine.connect() as conn:
        # Get table sizes and performance metrics
        tables_info = {}
        index_info = {}
        tables = ['config', 'transactions', 'fixed_lines', 'custom_provisions', 'import_metadata', 'export_history', 'users']
        
        total_records = 0
        for table in tables:
            try:
                # Record count
                result = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {table}").fetchone()
                count = result[0] if result else 0
                tables_info[table] = count
                total_records += count
                
                # Get index information for performance analysis
                try:
                    index_result = conn.exec_driver_sql(f"PRAGMA index_list('{table}')").fetchall()
                    index_info[table] = len(index_result)
                except Exception:
                    index_info[table] = 0
                    
            except Exception as e:
                tables_info[table] = f"Error: {e}"
                index_info[table] = 0
        
        # Get database performance metrics
        performance_metrics = {}
        try:
            # SQLite performance statistics
            cache_result = conn.exec_driver_sql("PRAGMA cache_size").fetchone()
            performance_metrics['cache_size'] = cache_result[0] if cache_result else 'Unknown'
            
            journal_result = conn.exec_driver_sql("PRAGMA journal_mode").fetchone()
            performance_metrics['journal_mode'] = journal_result[0] if journal_result else 'Unknown'
            
            sync_result = conn.exec_driver_sql("PRAGMA synchronous").fetchone()
            performance_metrics['synchronous'] = sync_result[0] if sync_result else 'Unknown'
            
        except Exception as e:
            performance_metrics['error'] = str(e)
        
        return {
            'engine_url': str(engine.url),
            'total_records': total_records,
            'tables': tables_info,
            'indexes_per_table': index_info,
            'performance_metrics': performance_metrics,
            'encrypted': hasattr(engine.url, 'database') and 'pysqlcipher' in str(engine.url),
            'optimization_level': 'high_performance' if total_records > 1000 else 'standard'
        }


# Initialize database
create_tables()
migrate_schema()

def get_slow_queries_report(db: Session, limit: int = 10) -> Dict:
    """Generate a report of potentially slow queries for monitoring"""
    try:
        # Analyze table statistics for query optimization recommendations
        slow_query_indicators = []
        
        # Check transactions table size vs indexes
        transaction_count = db.query(Transaction).count()
        if transaction_count > 10000:
            slow_query_indicators.append({
                'table': 'transactions',
                'issue': 'large_table_size',
                'records': transaction_count,
                'recommendation': 'Ensure composite indexes are utilized for month/category filtering'
            })
        
        # Check for missing date filters
        recent_queries_without_date = db.query(Transaction).filter(
            Transaction.date_op == None
        ).count()
        
        if recent_queries_without_date > 100:
            slow_query_indicators.append({
                'table': 'transactions',
                'issue': 'missing_date_values',
                'records': recent_queries_without_date,
                'recommendation': 'Add date validation on import to improve query performance'
            })
        
        return {
            'analyzed_at': dt.datetime.now().isoformat(),
            'indicators': slow_query_indicators,
            'total_transactions': transaction_count,
            'performance_status': 'good' if len(slow_query_indicators) == 0 else 'needs_attention'
        }
        
    except Exception as e:
        logger.error(f"Error analyzing slow queries: {e}")
        return {
            'analyzed_at': dt.datetime.now().isoformat(),
            'error': str(e),
            'performance_status': 'unknown'
        }


def optimize_database_performance(db: Session) -> Dict:
    """Run database optimization and return performance metrics"""
    start_time = dt.datetime.now()
    
    try:
        # Run SQLite optimization commands
        db.execute("PRAGMA optimize")
        db.execute("ANALYZE")
        db.commit()
        
        # Get updated statistics
        db_info = get_database_info()
        
        optimization_time = (dt.datetime.now() - start_time).total_seconds()
        
        return {
            'optimized_at': start_time.isoformat(),
            'optimization_time_seconds': optimization_time,
            'database_info': db_info,
            'status': 'completed'
        }
        
    except Exception as e:
        logger.error(f"Database optimization error: {e}")
        return {
            'optimized_at': start_time.isoformat(),
            'error': str(e),
            'status': 'failed'
        }


logger.info("Database models with performance optimization initialized successfully")