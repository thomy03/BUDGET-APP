"""
Centralized authentication utilities for Budget Famille v2.3
Eliminates duplicate authentication patterns across the application
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union, Tuple, List
from functools import wraps

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from .error_handlers import handle_auth_error, handle_permission_error

logger = logging.getLogger(__name__)

# Authentication configuration
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

class AuthContext:
    """Authentication context for request handling"""
    
    def __init__(self, user: Dict[str, Any], token: str, permissions: list = None):
        self.user = user
        self.token = token
        self.permissions = permissions or []
        self.username = user.get("username")
        self.user_id = user.get("id")
        self.is_admin = user.get("is_admin", False)
        
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return self.is_admin or permission in self.permissions
    
    def get_user_data(self) -> Dict[str, Any]:
        """Get sanitized user data for responses"""
        return {
            "username": self.username,
            "user_id": self.user_id,
            "is_admin": self.is_admin,
            "permissions": self.permissions
        }

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)

def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token
    
    Args:
        data: Token payload data
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Token creation error: {e}")
        raise

def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def extract_user_from_token(token: str) -> Dict[str, Any]:
    """
    Extract user information from JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    payload = verify_jwt_token(token)
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Return minimal user info from token
    # In a real implementation, you might fetch from database
    return {
        "username": username,
        "token_issued_at": payload.get("iat"),
        "token_expires_at": payload.get("exp")
    }

def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current user from token
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        Current user information
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        user = extract_user_from_token(token)
        return user
    except Exception as e:
        raise handle_auth_error(e, token=token)

def create_auth_context(
    user: Dict[str, Any],
    token: str,
    permissions: Optional[list] = None
) -> AuthContext:
    """
    Create authentication context for request
    
    Args:
        user: User information
        token: JWT token
        permissions: Optional user permissions
        
    Returns:
        AuthContext instance
    """
    return AuthContext(user, token, permissions)

def require_permission(permission: str):
    """
    Decorator to require specific permission for endpoint
    
    Args:
        permission: Required permission string
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract auth context from kwargs or dependencies
            auth_context = None
            for arg in args + tuple(kwargs.values()):
                if isinstance(arg, AuthContext):
                    auth_context = arg
                    break
            
            if not auth_context:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication context not found"
                )
            
            if not auth_context.has_permission(permission):
                raise handle_permission_error(
                    permission,
                    auth_context.permissions,
                    func.__name__
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_admin(func):
    """
    Decorator to require admin privileges
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract auth context from kwargs or dependencies
        auth_context = None
        for arg in args + tuple(kwargs.values()):
            if isinstance(arg, AuthContext):
                auth_context = arg
                break
        
        if not auth_context:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication context not found"
            )
        
        if not auth_context.is_admin:
            raise handle_permission_error(
                "admin",
                auth_context.permissions,
                func.__name__
            )
        
        return await func(*args, **kwargs)
    return wrapper

def check_user_permissions(
    user: Dict[str, Any],
    required_permissions: Union[str, list]
) -> bool:
    """
    Check if user has required permissions
    
    Args:
        user: User information
        required_permissions: Required permission(s)
        
    Returns:
        True if user has all required permissions
    """
    if isinstance(required_permissions, str):
        required_permissions = [required_permissions]
    
    user_permissions = user.get("permissions", [])
    is_admin = user.get("is_admin", False)
    
    # Admins have all permissions
    if is_admin:
        return True
    
    # Check each required permission
    for permission in required_permissions:
        if permission not in user_permissions:
            return False
    
    return True

def generate_secure_password(length: int = 12) -> str:
    """
    Generate secure random password
    
    Args:
        length: Password length
        
    Returns:
        Random password string
    """
    import secrets
    import string
    
    characters = string.ascii_letters + string.digits + "!@#$%&*"
    password = ''.join(secrets.choice(characters) for _ in range(length))
    
    # Ensure password has at least one of each type
    if not any(c.islower() for c in password):
        password = password[:-1] + secrets.choice(string.ascii_lowercase)
    if not any(c.isupper() for c in password):
        password = password[:-1] + secrets.choice(string.ascii_uppercase)
    if not any(c.isdigit() for c in password):
        password = password[:-1] + secrets.choice(string.digits)
    if not any(c in "!@#$%&*" for c in password):
        password = password[:-1] + secrets.choice("!@#$%&*")
    
    return password

def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Validate password strength
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    
    if not any(c.islower() for c in password):
        issues.append("Password must contain at least one lowercase letter")
    
    if not any(c.isupper() for c in password):
        issues.append("Password must contain at least one uppercase letter")
    
    if not any(c.isdigit() for c in password):
        issues.append("Password must contain at least one digit")
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        issues.append("Password must contain at least one special character")
    
    # Check for common weak passwords
    weak_patterns = ["123456", "password", "qwerty", "abc123"]
    if any(pattern in password.lower() for pattern in weak_patterns):
        issues.append("Password contains common weak patterns")
    
    return len(issues) == 0, issues

def mask_sensitive_data(data: Dict[str, Any], fields: list = None) -> Dict[str, Any]:
    """
    Mask sensitive fields in data for logging
    
    Args:
        data: Data dictionary
        fields: Fields to mask (defaults to common sensitive fields)
        
    Returns:
        Data dictionary with masked sensitive fields
    """
    if fields is None:
        fields = ["password", "token", "secret", "key", "credentials"]
    
    masked = data.copy()
    
    for field in fields:
        if field in masked and masked[field]:
            value = str(masked[field])
            if len(value) > 8:
                masked[field] = value[:4] + "*" * (len(value) - 8) + value[-4:]
            else:
                masked[field] = "*" * len(value)
    
    return masked

def log_auth_event(
    event_type: str,
    username: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """
    Log authentication events for security monitoring
    
    Args:
        event_type: Type of auth event (login, logout, token_refresh, etc.)
        username: Username involved in the event
        success: Whether the event was successful
        details: Additional event details
        request: Optional request object for IP/user-agent
    """
    log_data = {
        "event_type": event_type,
        "success": success,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    if username:
        log_data["username"] = username
    
    if request:
        log_data["client_ip"] = getattr(request.client, "host", "unknown")
        log_data["user_agent"] = request.headers.get("user-agent", "unknown")
    
    if details:
        # Mask sensitive data before logging
        log_data["details"] = mask_sensitive_data(details)
    
    log_level = "info" if success else "warning"
    log_func = getattr(logger, log_level)
    log_func(f"Auth event: {event_type} | {log_data}")

# Rate limiting utilities
class RateLimiter:
    """Simple in-memory rate limiter for authentication attempts"""
    
    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        self.max_attempts = max_attempts
        self.window_minutes = window_minutes
        self.attempts = {}  # {identifier: [timestamp, ...]}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if identifier is within rate limits"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=self.window_minutes)
        
        # Clean old attempts
        if identifier in self.attempts:
            self.attempts[identifier] = [
                ts for ts in self.attempts[identifier] if ts > window_start
            ]
        else:
            self.attempts[identifier] = []
        
        # Check current attempts
        return len(self.attempts[identifier]) < self.max_attempts
    
    def record_attempt(self, identifier: str):
        """Record an authentication attempt"""
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        self.attempts[identifier].append(datetime.now(timezone.utc))

# Global rate limiter instance
auth_rate_limiter = RateLimiter()

def check_rate_limit(identifier: str, record: bool = True) -> bool:
    """
    Check and optionally record rate limit attempt
    
    Args:
        identifier: Unique identifier (IP, username, etc.)
        record: Whether to record this attempt
        
    Returns:
        True if within rate limits
    """
    allowed = auth_rate_limiter.is_allowed(identifier)
    
    if record:
        auth_rate_limiter.record_attempt(identifier)
    
    return allowed