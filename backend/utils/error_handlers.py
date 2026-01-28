"""
Centralized error handling utilities for Budget Famille v2.3
Eliminates duplicate error handling patterns across the application
"""

import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError

logger = logging.getLogger(__name__)

class BudgetError(Exception):
    """Base exception for Budget application"""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

class ValidationError(BudgetError):
    """Exception for validation errors"""
    pass

class AuthenticationError(BudgetError):
    """Exception for authentication errors"""
    pass

class DatabaseError(BudgetError):
    """Exception for database errors"""
    pass

def handle_http_exception(
    status_code: int, 
    detail: str, 
    headers: Optional[Dict[str, str]] = None,
    log_level: str = "error"
) -> HTTPException:
    """
    Centralized HTTP exception handler with consistent logging
    
    Args:
        status_code: HTTP status code
        detail: Error detail message
        headers: Optional HTTP headers
        log_level: Logging level (debug, info, warning, error, critical)
        
    Returns:
        HTTPException instance
    """
    # Log the error with appropriate level
    log_func = getattr(logger, log_level.lower(), logger.error)
    log_func(f"HTTP {status_code}: {detail}")
    
    # Create standardized headers
    if headers is None:
        headers = {}
    
    # Add common security headers
    if status_code == 401:
        headers.setdefault("WWW-Authenticate", "Bearer")
    
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers=headers
    )

def handle_validation_error(
    error: Union[ValidationError, ValueError, TypeError],
    field_name: Optional[str] = None,
    custom_message: Optional[str] = None
) -> HTTPException:
    """
    Handle validation errors with consistent formatting
    
    Args:
        error: The validation error
        field_name: Optional field name for context
        custom_message: Optional custom error message
        
    Returns:
        HTTPException with 422 status
    """
    if custom_message:
        message = custom_message
    elif field_name:
        message = f"Validation error for field '{field_name}': {str(error)}"
    else:
        message = f"Validation error: {str(error)}"
    
    logger.warning(f"Validation error: {message}")
    
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=message
    )

def handle_database_error(
    error: SQLAlchemyError,
    operation: str = "database operation",
    rollback_attempted: bool = False
) -> HTTPException:
    """
    Handle database errors with consistent logging and responses
    
    Args:
        error: SQLAlchemy error
        operation: Description of the operation that failed
        rollback_attempted: Whether rollback was attempted
        
    Returns:
        HTTPException with appropriate status code
    """
    error_msg = str(error)
    
    # Handle specific database error types
    if isinstance(error, IntegrityError):
        logger.warning(f"Integrity constraint violation during {operation}: {error_msg}")
        if "UNIQUE constraint failed" in error_msg:
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Resource already exists"
            )
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data integrity constraint violation"
        )
    
    # Generic database error
    logger.error(f"Database error during {operation}: {error_msg}")
    if rollback_attempted:
        logger.info("Database rollback attempted")
    
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database operation failed"
    )

def create_error_response(
    message: str,
    code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create standardized error response format
    
    Args:
        message: Error message
        code: Optional error code
        details: Optional additional details
        timestamp: Optional timestamp (defaults to now)
        
    Returns:
        Standardized error response dictionary
    """
    response = {
        "error": True,
        "message": message,
        "timestamp": timestamp or datetime.utcnow().isoformat()
    }
    
    if code:
        response["code"] = code
    if details:
        response["details"] = details
        
    return response

def create_success_response(
    data: Any = None,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create standardized success response format
    
    Args:
        data: Response data
        message: Optional success message
        meta: Optional metadata
        
    Returns:
        Standardized success response dictionary
    """
    response = {
        "success": True,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    if meta:
        response["meta"] = meta
        
    return response

def log_error_with_context(
    error: Exception,
    context: Dict[str, Any],
    level: str = "error"
) -> None:
    """
    Log error with additional context information
    
    Args:
        error: The exception to log
        context: Additional context information
        level: Log level (debug, info, warning, error, critical)
    """
    log_func = getattr(logger, level.lower(), logger.error)
    
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())
    log_func(f"{type(error).__name__}: {str(error)} | Context: {context_str}")

def handle_file_upload_error(
    error: Exception,
    filename: Optional[str] = None,
    file_size: Optional[int] = None
) -> HTTPException:
    """
    Handle file upload specific errors
    
    Args:
        error: The upload error
        filename: Optional filename
        file_size: Optional file size
        
    Returns:
        HTTPException with appropriate status
    """
    context = {}
    if filename:
        context["filename"] = filename
    if file_size:
        context["file_size"] = file_size
    
    log_error_with_context(error, context)
    
    error_msg = str(error)
    
    # Handle specific file errors
    if "too large" in error_msg.lower() or "size" in error_msg.lower():
        return HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large"
        )
    elif "format" in error_msg.lower() or "type" in error_msg.lower():
        return HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file format"
        )
    elif "corrupt" in error_msg.lower() or "invalid" in error_msg.lower():
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or corrupted file"
        )
    
    # Generic file error
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="File processing error"
    )

def handle_auth_error(
    error: Exception,
    token: Optional[str] = None,
    username: Optional[str] = None
) -> HTTPException:
    """
    Handle authentication specific errors
    
    Args:
        error: The authentication error
        token: Optional token (for logging - will be masked)
        username: Optional username for context
        
    Returns:
        HTTPException with 401 status
    """
    context = {}
    if username:
        context["username"] = username
    if token:
        # Log only first 8 chars of token for security
        context["token_prefix"] = token[:8] + "..." if len(token) > 8 else "short"
    
    log_error_with_context(error, context, level="warning")
    
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed",
        headers={"WWW-Authenticate": "Bearer"}
    )

def handle_permission_error(
    required_permission: str,
    user_permissions: Optional[list] = None,
    resource: Optional[str] = None
) -> HTTPException:
    """
    Handle authorization/permission errors
    
    Args:
        required_permission: The permission that was required
        user_permissions: Optional list of user permissions
        resource: Optional resource being accessed
        
    Returns:
        HTTPException with 403 status
    """
    context = {
        "required_permission": required_permission
    }
    if user_permissions:
        context["user_permissions"] = user_permissions
    if resource:
        context["resource"] = resource
    
    logger.warning(f"Permission denied | Context: {context}")
    
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions"
    )

def safe_execute(func, *args, default=None, log_errors=True, **kwargs):
    """
    Safely execute a function with error handling
    
    Args:
        func: Function to execute
        *args: Function arguments
        default: Default value to return on error
        log_errors: Whether to log errors
        **kwargs: Function keyword arguments
        
    Returns:
        Function result or default value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Safe execution failed for {func.__name__}: {str(e)}")
        return default

# Common error responses for consistency
COMMON_ERRORS = {
    "INVALID_INPUT": {
        "status_code": status.HTTP_400_BAD_REQUEST,
        "detail": "Invalid input data"
    },
    "NOT_FOUND": {
        "status_code": status.HTTP_404_NOT_FOUND,
        "detail": "Resource not found"
    },
    "UNAUTHORIZED": {
        "status_code": status.HTTP_401_UNAUTHORIZED,
        "detail": "Authentication required",
        "headers": {"WWW-Authenticate": "Bearer"}
    },
    "FORBIDDEN": {
        "status_code": status.HTTP_403_FORBIDDEN,
        "detail": "Access denied"
    },
    "CONFLICT": {
        "status_code": status.HTTP_409_CONFLICT,
        "detail": "Resource conflict"
    },
    "TOO_MANY_REQUESTS": {
        "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
        "detail": "Too many requests, please try again later"
    },
    "INTERNAL_ERROR": {
        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "detail": "Internal server error"
    }
}

def raise_common_error(error_type: str, custom_detail: Optional[str] = None):
    """
    Raise a common error type
    
    Args:
        error_type: Error type from COMMON_ERRORS
        custom_detail: Optional custom detail message
    """
    if error_type not in COMMON_ERRORS:
        raise ValueError(f"Unknown error type: {error_type}")
    
    error_config = COMMON_ERRORS[error_type].copy()
    
    if custom_detail:
        error_config["detail"] = custom_detail
    
    raise HTTPException(**error_config)