"""
Centralized configuration management for Budget API
"""
import os
import logging
from typing import List, Optional
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import field_validator, ConfigDict
except ImportError:
    from pydantic import BaseSettings, validator
    field_validator = validator
    # Fallback for older Pydantic versions
    ConfigDict = None
    SettingsConfigDict = None
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Database configuration with performance monitoring"""
    database_url: str = "sqlite:///./budget.db"
    enable_encryption: bool = False
    connection_timeout: int = 20
    pool_pre_ping: bool = True
    pool_recycle: int = 3600
    echo_sql: bool = False
    
    # Performance monitoring settings
    enable_query_logging: bool = False
    slow_query_threshold: float = 1.0  # seconds
    enable_performance_monitoring: bool = True
    max_query_cache_size: int = 1000
    
    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore")

    @field_validator('enable_encryption')
    @classmethod
    def parse_encryption(cls, v):
        if isinstance(v, str):
            return v.lower() == 'true'
        return bool(v)


class SecuritySettings(BaseSettings):
    """Security configuration"""
    secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    min_key_length: int = 32
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_secret_key()
    
    def _validate_secret_key(self):
        """Validate JWT secret key meets security requirements"""
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY environment variable is required")
        
        # Check for default/insecure values
        insecure_keys = [
            "your-secret-key",
            "your-secret-key-change-in-production", 
            "your-secret-key-here-change-me-in-production",
            "changeme",
            "secret",
            "password",
            "admin"
        ]
        
        key_lower = self.secret_key.lower()
        for insecure in insecure_keys:
            if insecure in key_lower:
                raise ValueError(
                    f"Insecure JWT secret key detected. "
                    f"Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
        
        # Check minimum length
        if len(self.secret_key) < self.min_key_length:
            raise ValueError(
                f"JWT secret key must be at least {self.min_key_length} characters long. "
                f"Current length: {len(self.secret_key)}"
            )

    model_config = SettingsConfigDict(env_prefix="JWT_", extra="ignore")


class CORSSettings(BaseSettings):
    """CORS configuration"""
    allowed_origins: List[str] = []
    allow_credentials: bool = True
    allow_methods: List[str] = ["GET", "POST", "PATCH", "DELETE", "PUT", "OPTIONS"]
    allow_headers: List[str] = ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin", "Access-Control-Request-Method", "Access-Control-Request-Headers"]
    max_age: int = 600  # 10 minutes
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.allowed_origins:
            self._set_default_origins()
    
    def _set_default_origins(self):
        """Set environment-appropriate default origins"""
        from os import getenv
        environment = getenv("ENVIRONMENT", "development")
        
        if environment == "production":
            # Production should explicitly set CORS_ALLOWED_ORIGINS
            # Default to empty list for security
            self.allowed_origins = []
        else:
            # Development defaults
            self.allowed_origins = [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:4200",
                "http://127.0.0.1:4200",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "http://localhost:45678",
                "http://127.0.0.1:45678",
                "http://localhost:45679",
                "http://127.0.0.1:45679"
            ]
    
    @field_validator('allowed_origins')
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            origins = [origin.strip() for origin in v.split(',') if origin.strip()]
            # Validate each origin format
            for origin in origins:
                if not origin.startswith(('http://', 'https://')):
                    raise ValueError(f"Invalid origin format: {origin}. Must start with http:// or https://")
            return origins
        return v
    
    model_config = SettingsConfigDict(env_prefix="CORS_", extra="ignore")

    @field_validator('allow_credentials')
    @classmethod
    def validate_credentials_with_origins(cls, v):
        """Validate CORS credentials configuration"""
        # Note: Cross-field validation would need model_validator in Pydantic v2
        # For now, just validate the field itself
        return v


class FileUploadSettings(BaseSettings):
    """File upload configuration"""
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = [".csv", ".txt"]
    temp_dir: str = "/tmp"

    model_config = SettingsConfigDict(env_prefix="UPLOAD_", extra="ignore")


class LoggingSettings(BaseSettings):
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_sql_logging: bool = False

    model_config = SettingsConfigDict(env_prefix="LOG_", extra="ignore")


class CacheSettings(BaseSettings):
    """Caching configuration"""
    enable_cache: bool = True
    cache_ttl: int = 300  # 5 minutes
    max_cache_size: int = 1000

    model_config = SettingsConfigDict(env_prefix="CACHE_", extra="ignore")


class RedisSettings(BaseSettings):
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    username: Optional[str] = None
    ssl: bool = False
    
    # Connection pool settings
    max_connections: int = 50
    retry_on_timeout: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    connection_pool_kwargs: dict = {}
    
    # Cache-specific settings
    key_prefix: str = "budget_family:"
    default_ttl: int = 300  # 5 minutes
    summary_ttl: int = 900  # 15 minutes for expensive calculations
    trends_ttl: int = 1800  # 30 minutes for trend data
    anomaly_ttl: int = 600  # 10 minutes for anomaly detection
    
    # Health check settings
    health_check_interval: int = 30  # seconds
    max_retry_attempts: int = 3

    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")


class APISettings(BaseSettings):
    """API configuration"""
    title: str = "Budget Famille API - Modular"
    version: str = "2.3.0"
    description: str = "API modulaire pour la gestion budgétaire familiale"
    api_version: str = "v1"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"

    model_config = SettingsConfigDict(env_prefix="API_", extra="ignore")


class Settings(BaseSettings):
    """Main settings aggregating all configurations"""
    database: DatabaseSettings = DatabaseSettings()
    security: SecuritySettings = SecuritySettings()
    cors: CORSSettings = CORSSettings()
    file_upload: FileUploadSettings = FileUploadSettings()
    logging: LoggingSettings = LoggingSettings()
    cache: CacheSettings = CacheSettings()
    redis: RedisSettings = RedisSettings()
    api: APISettings = APISettings()
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @field_validator('debug')
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() == 'true'
        return bool(v)


# Global settings instance
settings = Settings()


def configure_logging():
    """Configure application logging"""
    logging.basicConfig(
        level=getattr(logging, settings.logging.level.upper()),
        format=settings.logging.format
    )
    
    # Configure SQL logging if enabled
    if settings.logging.enable_sql_logging:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    
    logger.info("Logging configured successfully")


def get_database_url() -> str:
    """Get database URL with encryption support"""
    if settings.database.enable_encryption:
        try:
            from database_encrypted import get_encrypted_engine
            logger.info("Using encrypted database")
            return "encrypted"  # Special marker for encrypted DB
        except ImportError:
            logger.warning("Encryption requested but module unavailable, using standard DB")
    
    return settings.database.database_url


def validate_configuration():
    """Validate configuration settings"""
    errors = []
    
    # Production-specific validations
    if settings.environment == "production":
        # CORS validation for production
        dev_origins = ["localhost", "127.0.0.1"]
        production_cors_issues = []
        for origin in settings.cors.allowed_origins:
            for dev_origin in dev_origins:
                if dev_origin in origin:
                    production_cors_issues.append(origin)
        
        if production_cors_issues:
            errors.append(f"Development CORS origins not allowed in production: {production_cors_issues}")
        
        # Database encryption requirement in production
        if not settings.database.enable_encryption:
            logger.warning("Database encryption is recommended for production environments")
        
        # Debug mode check
        if settings.debug:
            errors.append("Debug mode must be disabled in production")
    
    # Validate file upload settings
    if settings.file_upload.max_file_size <= 0:
        errors.append("MAX_FILE_SIZE must be positive")
    
    # Validate database settings
    if settings.database.connection_timeout <= 0:
        errors.append("DB_CONNECTION_TIMEOUT must be positive")
    
    # Validate security token expiration
    if settings.security.access_token_expire_minutes <= 0:
        errors.append("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
    
    if settings.security.access_token_expire_minutes > 1440:  # 24 hours
        logger.warning("JWT token expiration is very long - consider shorter expiration for security")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    logger.info("Configuration validated successfully")


# Initialize configuration
configure_logging()
validate_configuration()

logger.info(f"Settings loaded for environment: {settings.environment}")