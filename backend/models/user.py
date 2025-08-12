"""
User management models and functions for Budget Famille API
Replaces hardcoded user credentials with secure database-backed system
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from passlib.context import CryptContext

from models.database import Base

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Increase rounds for better security
)


class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    full_name = Column(String(100), nullable=True)
    
    # Authentication
    hashed_password = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False)
    
    # Security
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    force_password_change = Column(Boolean, default=False)
    
    # Session management
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    created_by = Column(String(50), nullable=True)
    
    # Two-factor authentication (future extension)
    totp_secret = Column(String(32), nullable=True)
    backup_codes = Column(Text, nullable=True)  # JSON array of backup codes


class UserSession(Base):
    """User session tracking for security monitoring"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    session_token = Column(String(64), unique=True, index=True, nullable=False)
    
    # Session info
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Security flags
    is_suspicious = Column(Boolean, default=False)
    logout_reason = Column(String(50))  # expired, logout, revoked, suspicious


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def generate_secure_password(length: int = 16) -> str:
    """Generate a cryptographically secure password"""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Validate password strength
    Returns (is_valid, error_messages)
    """
    errors = []
    
    if len(password) < 12:
        errors.append("Password must be at least 12 characters long")
    
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")
    
    # Check for common weak passwords
    weak_passwords = ["password", "123456", "admin", "qwerty", "letmein"]
    if password.lower() in weak_passwords:
        errors.append("Password is too common")
    
    return len(errors) == 0, errors


def is_account_locked(user: User) -> bool:
    """Check if user account is locked due to failed attempts"""
    if user.locked_until and datetime.utcnow() < user.locked_until:
        return True
    
    # Clear expired locks
    if user.locked_until and datetime.utcnow() >= user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
    
    return False


def lock_account(user: User, duration_minutes: int = 15):
    """Lock user account for specified duration"""
    user.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
    logger.warning(f"Account locked for user: {user.username} until {user.locked_until}")


def record_login_attempt(user: User, success: bool, ip_address: str = None):
    """Record login attempt and handle account locking"""
    if success:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        user.login_count += 1
        logger.info(f"Successful login for user: {user.username}")
    else:
        user.failed_login_attempts += 1
        
        # Progressive lockout
        if user.failed_login_attempts >= 5:
            lock_account(user, 15)  # 15 minutes
        elif user.failed_login_attempts >= 10:
            lock_account(user, 60)  # 1 hour
        elif user.failed_login_attempts >= 15:
            lock_account(user, 1440)  # 24 hours
        
        logger.warning(f"Failed login attempt #{user.failed_login_attempts} for user: {user.username}")


def create_default_admin_user(db, force_new_password: bool = False) -> Tuple[User, str]:
    """
    Create default admin user with secure random password
    Returns (user, generated_password)
    """
    # Check if admin user already exists
    existing_user = db.query(User).filter(User.username == "admin").first()
    
    if existing_user and not force_new_password:
        logger.info("Admin user already exists")
        return existing_user, None
    
    # Generate secure password
    secure_password = generate_secure_password(16)
    hashed_password = hash_password(secure_password)
    
    if existing_user:
        # Update existing user's password
        existing_user.hashed_password = hashed_password
        existing_user.force_password_change = True
        existing_user.password_changed_at = datetime.utcnow()
        existing_user.failed_login_attempts = 0
        existing_user.locked_until = None
        db.commit()
        db.refresh(existing_user)
        
        logger.info("Admin user password updated")
        return existing_user, secure_password
    else:
        # Create new admin user
        admin_user = User(
            username="admin",
            email="admin@budget-famille.local",
            full_name="System Administrator",
            hashed_password=hashed_password,
            is_admin=True,
            force_password_change=True,
            password_changed_at=datetime.utcnow(),
            created_by="system"
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        logger.info("Default admin user created successfully")
        return admin_user, secure_password


def cleanup_expired_sessions(db):
    """Clean up expired user sessions"""
    try:
        expired_count = db.query(UserSession).filter(
            UserSession.expires_at < datetime.utcnow()
        ).update({"is_active": False})
        
        if expired_count > 0:
            db.commit()
            logger.info(f"Cleaned up {expired_count} expired sessions")
    
    except Exception as e:
        logger.error(f"Error cleaning up expired sessions: {e}")
        db.rollback()


def get_user_by_username(db, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(
        User.username == username,
        User.is_active == True
    ).first()


def authenticate_user(db, username: str, password: str, ip_address: str = None) -> Optional[User]:
    """Authenticate user with enhanced security"""
    user = get_user_by_username(db, username)
    
    if not user:
        logger.warning(f"Login attempt for non-existent user: {username}")
        return None
    
    # Check if account is locked
    if is_account_locked(user):
        logger.warning(f"Login attempt for locked account: {username}")
        return None
    
    # Verify password
    if not verify_password(password, user.hashed_password):
        record_login_attempt(user, False, ip_address)
        db.commit()
        return None
    
    # Successful authentication
    record_login_attempt(user, True, ip_address)
    db.commit()
    
    return user