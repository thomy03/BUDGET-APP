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
    expense_type = Column(String, default="VARIABLE", index=True)  # FIXED, VARIABLE, PROVISION - for strict separation
    confidence_score = Column(Float, nullable=True, index=True)  # AI classification confidence score (0.0-1.0)
    row_id = Column(String, index=True)  # stable hash
    tags = Column(Text, default="")      # CSV of tags
    import_id = Column(String, nullable=True, index=True)  # UUID of the import that created this transaction
    
    # Critical composite indexes for high-performance queries
    __table_args__ = (
        # Core filtering indexes for dashboard and analytics
        Index('idx_transactions_month_exclude_expense', 'month', 'exclude', 'is_expense'),
        Index('idx_transactions_month_expense_type', 'month', 'expense_type', 'exclude'),  # New index for strict separation
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
        Index('idx_transactions_expense_type_month', 'expense_type', 'is_expense', 'month'),  # New index for filtering by type
        Index('idx_transactions_confidence_expense_type', 'confidence_score', 'expense_type', 'month'),  # AI confidence filtering
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


class TagFixedLineMapping(Base):
    """Mapping table for automatic tag to fixed line conversion"""
    __tablename__ = "tag_fixed_line_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    tag_name = Column(String(100), nullable=False, index=True)  # Tag from transaction
    fixed_line_id = Column(Integer, ForeignKey("fixed_lines.id"), nullable=False)
    
    # Automatic creation settings
    auto_created = Column(Boolean, default=True)  # Was this mapping created automatically?
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String(50), nullable=True)  # Username who created the mapping
    
    # Label recognition settings
    label_pattern = Column(String(200), nullable=True)  # Pattern to match in transaction labels
    is_active = Column(Boolean, default=True, index=True)
    
    # Usage statistics
    usage_count = Column(Integer, default=0)  # How many times this mapping was used
    last_used = Column(DateTime, nullable=True)
    
    # Relationship to fixed line
    fixed_line = relationship("FixedLine", back_populates="tag_mappings")
    
    # Performance indexes
    __table_args__ = (
        Index('idx_tag_mappings_tag_active', 'tag_name', 'is_active'),
        Index('idx_tag_mappings_fixed_line_active', 'fixed_line_id', 'is_active'),
        Index('idx_tag_mappings_auto_created', 'auto_created', 'created_at'),
        Index('idx_tag_mappings_usage', 'usage_count', 'last_used'),
        Index('idx_tag_mappings_pattern', 'label_pattern', 'is_active'),
    )


# Add relationship to FixedLine
FixedLine.tag_mappings = relationship("TagFixedLineMapping", back_populates="fixed_line")


class LabelTagMapping(Base):
    """
    Mapping table for automatic label to tag suggestions
    
    This table stores learned associations between transaction labels and tags
    to provide intelligent tagging suggestions for future transactions.
    """
    __tablename__ = "label_tag_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    label_pattern = Column(String(200), nullable=False, index=True)  # Transaction label pattern
    suggested_tags = Column(String(500), nullable=False)  # Comma-separated tags to suggest
    
    # Learning and confidence metrics
    confidence_score = Column(Float, default=1.0)  # How confident we are in this mapping (0-1)
    usage_count = Column(Integer, default=1, index=True)  # How many times this mapping was used
    success_rate = Column(Float, default=1.0)  # % of times user accepted this suggestion
    
    # Pattern matching settings  
    match_type = Column(String(20), default="exact")  # "exact", "contains", "starts_with", "regex"
    case_sensitive = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String(50), nullable=True)  # Username who created the mapping
    last_used = Column(DateTime, nullable=True)
    last_suggested = Column(DateTime, nullable=True)
    
    # Statistics tracking
    accepted_count = Column(Integer, default=0)  # How many times user accepted suggestion
    rejected_count = Column(Integer, default=0)  # How many times user rejected suggestion
    modified_count = Column(Integer, default=0)  # How many times user modified suggestion
    
    # Performance indexes
    __table_args__ = (
        Index('idx_label_mappings_pattern_active', 'label_pattern', 'is_active'),
        Index('idx_label_mappings_confidence', 'confidence_score', 'usage_count'),
        Index('idx_label_mappings_success_rate', 'success_rate', 'is_active'),
        Index('idx_label_mappings_usage', 'usage_count', 'last_used'),
        Index('idx_label_mappings_match_type', 'match_type', 'case_sensitive'),
    )


class MerchantKnowledgeBase(Base):
    """
    Dynamic knowledge base for merchants that learns from web research and user corrections
    
    This table stores intelligent merchant information with confidence scoring and 
    machine learning capabilities to improve expense classification over time.
    """
    __tablename__ = "merchant_knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Merchant identification
    merchant_name = Column(String(200), nullable=False, index=True)  # Original merchant name from transaction
    normalized_name = Column(String(200), nullable=False, index=True)  # Normalized merchant name for matching
    
    # Business intelligence
    business_type = Column(String(100), nullable=True)  # e.g., "restaurant", "supermarket", "gas_station"
    category = Column(String(100), nullable=True)  # More specific: fast_food, grocery, electronics, etc.
    sub_category = Column(String(100), nullable=True)  # Even more specific: chinese_restaurant, clothing_store, etc.
    expense_type = Column(String(10), default="VARIABLE", index=True)  # FIXED/VARIABLE classification
    
    # Location information (if detected)
    city = Column(String(100), nullable=True)
    country = Column(String(50), default="France")
    address = Column(String(500), nullable=True)
    location_data = Column(Text, nullable=True)  # JSON: comprehensive location info from research
    
    # Machine learning and confidence
    confidence_score = Column(Float, default=0.5, index=True)  # Overall confidence (0.0-1.0)
    data_sources = Column(Text, nullable=True)  # JSON: {"web": 0.8, "user": 0.9, "osm": 0.7}
    research_keywords = Column(String(500), nullable=True)  # Keywords that led to successful identification
    
    # Usage and learning metrics
    usage_count = Column(Integer, default=1, index=True)  # How many times this merchant was referenced
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_used = Column(DateTime, nullable=True)
    last_verified = Column(DateTime, nullable=True)  # When this entry was last manually verified
    accuracy_rating = Column(Float, default=1.0)  # User feedback on accuracy (0.0-1.0)
    
    # User feedback and corrections
    user_corrections = Column(Integer, default=0)  # Number of user corrections applied
    auto_classifications = Column(Integer, default=0)  # Number of automatic classifications
    success_rate = Column(Float, default=1.0)  # Success rate of auto-classifications
    
    # Expense classification suggestions
    suggested_expense_type = Column(String(20), nullable=True)  # FIXED, VARIABLE, PROVISION
    suggested_tags = Column(String(500), nullable=True)  # Comma-separated suggested tags
    
    # Web data extracted
    website_url = Column(String(500), nullable=True)  # Official website if found
    phone_number = Column(String(50), nullable=True)  # Phone number if found
    description = Column(Text, nullable=True)  # Description from web sources
    business_hours = Column(Text, nullable=True)  # JSON: operating hours
    
    # Learning metadata
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String(50), default="auto_learning")  # "auto_learning", username
    research_date = Column(DateTime, nullable=True)  # When web research was performed
    research_quality = Column(Float, default=0.0)  # Quality of research results
    research_duration_ms = Column(Integer, default=0)  # Time taken for research
    search_queries_used = Column(Text, nullable=True)  # JSON array of search queries used
    
    # Validation and status
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False, index=True)  # Manually verified by user
    is_validated = Column(Boolean, default=False)  # Has been validated by user
    needs_review = Column(Boolean, default=False, index=True)  # Flagged for manual review
    needs_update = Column(Boolean, default=False, index=True)  # Flag for entries needing re-research
    
    # Advanced analytics and pattern recognition
    seasonal_patterns = Column(Text, nullable=True)  # JSON: seasonal usage patterns
    transaction_patterns = Column(Text, nullable=True)  # JSON: typical transaction amounts/frequencies
    label_patterns = Column(Text, nullable=True)  # JSON array of label patterns that match this merchant
    
    # Performance indexes for knowledge base
    __table_args__ = (
        # Core search indexes
        Index('idx_merchant_kb_merchant_confidence', 'merchant_name', 'confidence_score'),
        Index('idx_merchant_kb_normalized_active', 'normalized_name', 'is_active'),
        Index('idx_merchant_kb_name_normalized', 'merchant_name', 'normalized_name'),
        
        # Business classification indexes
        Index('idx_merchant_kb_business_type', 'business_type', 'category'),
        Index('idx_merchant_kb_type_confidence', 'business_type', 'confidence_score'),
        Index('idx_merchant_kb_expense_type_confidence', 'expense_type', 'confidence_score'),
        
        # Location-based indexes
        Index('idx_merchant_kb_city_country', 'city', 'country'),
        Index('idx_merchant_kb_location_type', 'city', 'business_type'),
        
        # Usage and learning indexes
        Index('idx_merchant_kb_usage_updated', 'usage_count', 'last_updated'),
        Index('idx_merchant_kb_usage_verified', 'usage_count', 'is_verified'),
        Index('idx_merchant_kb_success_rate', 'success_rate', 'usage_count'),
        
        # Research quality indexes
        Index('idx_merchant_kb_accuracy_confidence', 'accuracy_rating', 'confidence_score'),
        Index('idx_merchant_kb_research_date', 'research_date', 'last_verified'),
        Index('idx_merchant_kb_research_quality', 'research_quality', 'confidence_score'),
        
        # Status and validation indexes
        Index('idx_merchant_kb_needs_review', 'needs_review', 'confidence_score'),
        Index('idx_merchant_kb_needs_update', 'needs_update', 'last_verified'),
        Index('idx_merchant_kb_validated_active', 'is_validated', 'is_active'),
        Index('idx_merchant_kb_created_research', 'created_at', 'research_date'),
        
        # Performance monitoring indexes
        Index('idx_merchant_kb_usage_accuracy', 'usage_count', 'accuracy_rating', 'is_active'),
        Index('idx_merchant_kb_sources_confidence', 'data_sources', 'confidence_score'),
    )


class ResearchCache(Base):
    """
    Cache for web research results to avoid redundant searches and improve performance
    
    This table stores research results with intelligent caching and confidence scoring.
    """
    __tablename__ = "research_cache"
    
    search_term = Column(String(200), primary_key=True, index=True)  # Primary search term
    research_results = Column(Text, nullable=False)  # JSON: complete research results
    
    # Confidence and quality metrics
    confidence_score = Column(Float, default=0.5, index=True)  # Research result confidence
    result_quality = Column(Float, default=0.5)  # Quality of research data
    sources_count = Column(Integer, default=0)  # Number of sources used
    
    # Cache management
    created_at = Column(DateTime, server_default=func.now(), index=True)
    last_used = Column(DateTime, nullable=True, index=True)
    usage_count = Column(Integer, default=1, index=True)
    
    # Research metadata
    research_method = Column(String(50), default="web_search")  # "web_search", "api", "osm", "hybrid"
    data_freshness = Column(Float, default=1.0)  # How fresh the data is (1.0 = very fresh)
    search_duration_ms = Column(Integer, default=0)  # Time taken for research
    
    # Validation and status
    is_valid = Column(Boolean, default=True, index=True)
    needs_refresh = Column(Boolean, default=False, index=True)  # Cache needs updating
    
    # Success tracking
    successful_matches = Column(Integer, default=0)  # How many times this cache helped
    failed_matches = Column(Integer, default=0)  # How many times this cache was insufficient
    
    # Performance indexes for research cache
    __table_args__ = (
        Index('idx_research_cache_confidence_fresh', 'confidence_score', 'data_freshness'),
        Index('idx_research_cache_used_count', 'last_used', 'usage_count'),
        Index('idx_research_cache_valid_needs_refresh', 'is_valid', 'needs_refresh'),
        Index('idx_research_cache_success_ratio', 'successful_matches', 'failed_matches'),
        Index('idx_research_cache_quality_sources', 'result_quality', 'sources_count'),
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
            
            if "expense_type" not in cols:
                conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN expense_type TEXT DEFAULT 'VARIABLE'")
                logger.info("Added 'expense_type' column to transactions table")
                
            if "confidence_score" not in cols:
                conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN confidence_score FLOAT")
                logger.info("Added 'confidence_score' column to transactions table")
            
            # Create comprehensive performance indexes
            critical_indexes = [
                # Transaction performance indexes - most critical for application performance
                "CREATE INDEX IF NOT EXISTS idx_transactions_month_exclude_expense ON transactions(month, exclude, is_expense)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_month_expense_type ON transactions(month, expense_type, exclude)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_month_category ON transactions(month, category)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_date_exclude ON transactions(date_op, exclude)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_category_amount ON transactions(category, amount)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_import_month ON transactions(import_id, month)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_row_id_unique ON transactions(row_id)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_tags_month ON transactions(tags, month)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_account_month ON transactions(account_label, month)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_month_date_exclude ON transactions(month, date_op, exclude)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_expense_category_month ON transactions(is_expense, category, month)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_expense_type_month ON transactions(expense_type, is_expense, month)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_confidence_expense_type ON transactions(confidence_score, expense_type, month)",
                
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
            
            # Migration for tag_fixed_line_mappings table
            try:
                conn.exec_driver_sql("SELECT 1 FROM tag_fixed_line_mappings LIMIT 1")
                logger.info("Table tag_fixed_line_mappings already exists")
            except Exception:
                logger.info("Creating tag_fixed_line_mappings table for automatic tag to fixed line conversion")
                conn.exec_driver_sql("""
                    CREATE TABLE IF NOT EXISTS tag_fixed_line_mappings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tag_name VARCHAR(100) NOT NULL,
                        fixed_line_id INTEGER NOT NULL,
                        auto_created BOOLEAN DEFAULT TRUE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        created_by VARCHAR(50),
                        label_pattern VARCHAR(200),
                        is_active BOOLEAN DEFAULT TRUE,
                        usage_count INTEGER DEFAULT 0,
                        last_used DATETIME,
                        FOREIGN KEY (fixed_line_id) REFERENCES fixed_lines (id) ON DELETE CASCADE
                    )
                """)
                
                # Create performance indexes for tag mappings
                tag_mapping_indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_tag_mappings_tag_active ON tag_fixed_line_mappings(tag_name, is_active)",
                    "CREATE INDEX IF NOT EXISTS idx_tag_mappings_fixed_line_active ON tag_fixed_line_mappings(fixed_line_id, is_active)",
                    "CREATE INDEX IF NOT EXISTS idx_tag_mappings_auto_created ON tag_fixed_line_mappings(auto_created, created_at)",
                    "CREATE INDEX IF NOT EXISTS idx_tag_mappings_usage ON tag_fixed_line_mappings(usage_count, last_used)",
                    "CREATE INDEX IF NOT EXISTS idx_tag_mappings_pattern ON tag_fixed_line_mappings(label_pattern, is_active)",
                ]
                
                for index_sql in tag_mapping_indexes:
                    conn.exec_driver_sql(index_sql)
                
                logger.info("✅ Table tag_fixed_line_mappings created with performance indexes")
            
            # Migration for label_tag_mappings table (new intelligent tagging system)
            try:
                conn.exec_driver_sql("SELECT 1 FROM label_tag_mappings LIMIT 1")
                logger.info("Table label_tag_mappings already exists")
            except Exception:
                logger.info("Creating label_tag_mappings table for intelligent tag suggestions")
                conn.exec_driver_sql("""
                    CREATE TABLE IF NOT EXISTS label_tag_mappings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        label_pattern VARCHAR(200) NOT NULL,
                        suggested_tags VARCHAR(500) NOT NULL,
                        confidence_score FLOAT DEFAULT 1.0,
                        usage_count INTEGER DEFAULT 1,
                        success_rate FLOAT DEFAULT 1.0,
                        match_type VARCHAR(20) DEFAULT 'exact',
                        case_sensitive BOOLEAN DEFAULT FALSE,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        created_by VARCHAR(50),
                        last_used DATETIME,
                        last_suggested DATETIME,
                        accepted_count INTEGER DEFAULT 0,
                        rejected_count INTEGER DEFAULT 0,
                        modified_count INTEGER DEFAULT 0
                    )
                """)
                
                # Create performance indexes for label tag mappings
                label_mapping_indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_label_mappings_pattern_active ON label_tag_mappings(label_pattern, is_active)",
                    "CREATE INDEX IF NOT EXISTS idx_label_mappings_confidence ON label_tag_mappings(confidence_score, usage_count)",
                    "CREATE INDEX IF NOT EXISTS idx_label_mappings_success_rate ON label_tag_mappings(success_rate, is_active)",
                    "CREATE INDEX IF NOT EXISTS idx_label_mappings_usage ON label_tag_mappings(usage_count, last_used)",
                    "CREATE INDEX IF NOT EXISTS idx_label_mappings_match_type ON label_tag_mappings(match_type, case_sensitive)",
                    "CREATE INDEX IF NOT EXISTS idx_label_mappings_created_by ON label_tag_mappings(created_by, is_active)",
                ]
                
                for index_sql in label_mapping_indexes:
                    conn.exec_driver_sql(index_sql)
                
                logger.info("✅ Table label_tag_mappings created with performance indexes")
            
            # Migration for merchant_knowledge_base table (intelligent merchant learning)
            try:
                conn.exec_driver_sql("SELECT 1 FROM merchant_knowledge_base LIMIT 1")
                logger.info("Table merchant_knowledge_base already exists")
            except Exception:
                logger.info("Creating merchant_knowledge_base table for intelligent merchant classification")
                conn.exec_driver_sql("""
                    CREATE TABLE IF NOT EXISTS merchant_knowledge_base (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        merchant_name VARCHAR(200) NOT NULL,
                        normalized_name VARCHAR(200) NOT NULL,
                        business_type VARCHAR(100),
                        category VARCHAR(100),
                        sub_category VARCHAR(100),
                        expense_type VARCHAR(10) DEFAULT 'VARIABLE',
                        city VARCHAR(100),
                        country VARCHAR(50) DEFAULT 'France',
                        address VARCHAR(500),
                        location_data TEXT,
                        confidence_score FLOAT DEFAULT 0.5,
                        data_sources TEXT,
                        research_keywords VARCHAR(500),
                        usage_count INTEGER DEFAULT 1,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_used DATETIME,
                        accuracy_rating FLOAT DEFAULT 1.0,
                        user_corrections INTEGER DEFAULT 0,
                        auto_classifications INTEGER DEFAULT 0,
                        success_rate FLOAT DEFAULT 1.0,
                        suggested_expense_type VARCHAR(20),
                        suggested_tags VARCHAR(500),
                        website_url VARCHAR(500),
                        phone_number VARCHAR(50),
                        description TEXT,
                        business_hours TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        created_by VARCHAR(50) DEFAULT 'auto_learning',
                        research_date DATETIME,
                        research_quality FLOAT DEFAULT 0.0,
                        research_duration_ms INTEGER DEFAULT 0,
                        search_queries_used TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        is_verified BOOLEAN DEFAULT FALSE,
                        is_validated BOOLEAN DEFAULT FALSE,
                        needs_review BOOLEAN DEFAULT FALSE,
                        needs_update BOOLEAN DEFAULT FALSE,
                        seasonal_patterns TEXT,
                        transaction_patterns TEXT,
                        label_patterns TEXT
                    )
                """)
                
                # Create performance indexes for merchant knowledge base
                merchant_kb_indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_merchant_confidence ON merchant_knowledge_base(merchant_name, confidence_score)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_normalized_active ON merchant_knowledge_base(normalized_name, is_active)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_name_normalized ON merchant_knowledge_base(merchant_name, normalized_name)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_business_type ON merchant_knowledge_base(business_type, category)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_type_confidence ON merchant_knowledge_base(business_type, confidence_score)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_expense_type_confidence ON merchant_knowledge_base(expense_type, confidence_score)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_city_country ON merchant_knowledge_base(city, country)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_location_type ON merchant_knowledge_base(city, business_type)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_usage_updated ON merchant_knowledge_base(usage_count, last_updated)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_usage_verified ON merchant_knowledge_base(usage_count, is_verified)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_success_rate ON merchant_knowledge_base(success_rate, usage_count)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_accuracy_confidence ON merchant_knowledge_base(accuracy_rating, confidence_score)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_research_date ON merchant_knowledge_base(research_date, last_verified)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_research_quality ON merchant_knowledge_base(research_quality, confidence_score)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_needs_review ON merchant_knowledge_base(needs_review, confidence_score)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_needs_update ON merchant_knowledge_base(needs_update, last_verified)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_validated_active ON merchant_knowledge_base(is_validated, is_active)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_created_research ON merchant_knowledge_base(created_at, research_date)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_usage_accuracy ON merchant_knowledge_base(usage_count, accuracy_rating, is_active)",
                    "CREATE INDEX IF NOT EXISTS idx_merchant_kb_sources_confidence ON merchant_knowledge_base(data_sources, confidence_score)",
                ]
                
                for index_sql in merchant_kb_indexes:
                    conn.exec_driver_sql(index_sql)
                
                logger.info("✅ Table merchant_knowledge_base created with performance indexes")
            
            # Migration for research_cache table (web research caching)
            try:
                conn.exec_driver_sql("SELECT 1 FROM research_cache LIMIT 1")
                logger.info("Table research_cache already exists")
            except Exception:
                logger.info("Creating research_cache table for web research caching")
                conn.exec_driver_sql("""
                    CREATE TABLE IF NOT EXISTS research_cache (
                        search_term VARCHAR(200) PRIMARY KEY,
                        research_results TEXT NOT NULL,
                        confidence_score FLOAT DEFAULT 0.5,
                        result_quality FLOAT DEFAULT 0.5,
                        sources_count INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_used DATETIME,
                        usage_count INTEGER DEFAULT 1,
                        research_method VARCHAR(50) DEFAULT 'web_search',
                        data_freshness FLOAT DEFAULT 1.0,
                        search_duration_ms INTEGER DEFAULT 0,
                        is_valid BOOLEAN DEFAULT TRUE,
                        needs_refresh BOOLEAN DEFAULT FALSE,
                        successful_matches INTEGER DEFAULT 0,
                        failed_matches INTEGER DEFAULT 0
                    )
                """)
                
                # Create performance indexes for research cache
                research_cache_indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_research_cache_confidence_fresh ON research_cache(confidence_score, data_freshness)",
                    "CREATE INDEX IF NOT EXISTS idx_research_cache_used_count ON research_cache(last_used, usage_count)",
                    "CREATE INDEX IF NOT EXISTS idx_research_cache_valid_needs_refresh ON research_cache(is_valid, needs_refresh)",
                    "CREATE INDEX IF NOT EXISTS idx_research_cache_success_ratio ON research_cache(successful_matches, failed_matches)",
                    "CREATE INDEX IF NOT EXISTS idx_research_cache_quality_sources ON research_cache(result_quality, sources_count)",
                ]
                
                for index_sql in research_cache_indexes:
                    conn.exec_driver_sql(index_sql)
                
                logger.info("✅ Table research_cache created with performance indexes")
            
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
        tables = ['config', 'transactions', 'fixed_lines', 'custom_provisions', 'import_metadata', 'export_history', 'users', 'merchant_knowledge_base', 'research_cache', 'label_tag_mappings', 'tag_fixed_line_mappings']
        
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