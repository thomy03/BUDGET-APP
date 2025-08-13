"""
Authentication dependencies for Budget Famille v2.3
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any

# Import from existing auth module
from auth import get_current_user as _get_current_user

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Get current authenticated user
    Wrapper around the existing auth module function
    """
    return _get_current_user(credentials)

def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get current active user (can be extended for user status checking)
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    return current_user