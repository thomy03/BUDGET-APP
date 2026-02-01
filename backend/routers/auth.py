"""
Authentication router for Budget API
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models.database import get_db
from models.user import authenticate_user, create_default_admin_user, User as UserModel, hash_password
from config.settings import settings
from auth import (
    authenticate_user as auth_authenticate_user,
    create_access_token, get_current_user,
    fake_users_db, Token, ACCESS_TOKEN_EXPIRE_MINUTES, debug_jwt_validation
)
from audit_logger import get_audit_logger, AuditEventType
from middleware.security import get_rate_limiter

# Import centralized utilities
from utils.error_handlers import (
    handle_http_exception, handle_auth_error, log_error_with_context,
    create_success_response, COMMON_ERRORS, raise_common_error
)
from utils.validators import validate_string_length, validate_json_payload
from utils.auth_utils import (
    log_auth_event, check_rate_limit, mask_sensitive_data
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
    responses={404: {"description": "Not found"}},
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"/api/v1/auth/token",
    scheme_name="JWT"
)


# Pydantic Models
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class DebugJWTRequest(BaseModel):
    """Request model for JWT debugging"""
    test_mode: Optional[bool] = True


@router.post("/token", response_model=Token, summary="Login for access token")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login - Refactored with centralized error handling
    
    This endpoint matches the original /token from the monolithic app.py
    """
    try:
        # Get client IP for rate limiting
        client_ip = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
        
        # Check rate limit
        if not check_rate_limit(f"login_{client_ip}"):
            log_auth_event("login_rate_limited", form_data.username, False, 
                         {"client_ip": client_ip}, request)
            raise_common_error("TOO_MANY_REQUESTS", "Trop de tentatives de connexion")
        
        # Authenticate user
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            log_auth_event("login_failed", form_data.username, False, 
                         {"reason": "invalid_credentials", "client_ip": client_ip}, request)
            raise handle_auth_error(
                Exception("Invalid credentials"), 
                username=form_data.username
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        # Log successful login
        log_auth_event("login_success", user.username, True,
                     {"client_ip": client_ip}, request)

        # Return OAuth2-compatible token response (not wrapped in create_success_response)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(e, {
            "endpoint": "login_for_access_token",
            "username": form_data.username,
            "client_ip": client_ip
        })
        raise handle_http_exception(500, "Erreur lors de l'authentification")


@router.post("/login", response_model=Token, summary="Alternative login endpoint")
async def login(
    request: Request,
    login_request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Alternative login endpoint accepting JSON payload
    
    - **username**: The username for authentication
    - **password**: The password for authentication
    """
    logger.info(f"JSON login attempt for user: {login_request.username}")
    
    try:
        # Get client IP for rate limiting
        client_ip = "unknown"
        if hasattr(request, 'client') and request.client:
            client_ip = request.client.host
        
        # Authenticate user
        user = authenticate_user(db, login_request.username, login_request.password)
        if not user:
            logger.warning(f"Failed JSON login attempt for user: {login_request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.security.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )
        
        logger.info(f"✅ Successful JSON login for user: {login_request.username}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.security.access_token_expire_minutes * 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSON login error for user {login_request.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication error"
        )


@router.get("/me", response_model=User, summary="Get current user")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Get information about the currently authenticated user
    
    Requires valid JWT token in Authorization header.
    """
    return User(
        username=current_user["username"],
        email=current_user.get("email"),
        full_name=current_user.get("full_name"),
        disabled=current_user.get("disabled", False)
    )


@router.post("/refresh", response_model=Token, summary="Refresh access token")
async def refresh_token(
    current_user: dict = Depends(get_current_user)
):
    """
    Refresh the access token for the current user
    
    This endpoint allows users to get a new access token without re-authenticating,
    as long as their current token is still valid.
    """
    try:
        # Create new access token
        access_token_expires = timedelta(minutes=settings.security.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": current_user["username"]}, 
            expires_delta=access_token_expires
        )
        
        logger.info(f"Token refreshed for user: {current_user['username']}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.security.access_token_expire_minutes * 60
        }
        
    except Exception as e:
        logger.error(f"Token refresh error for user {current_user['username']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout", summary="Logout (placeholder)")
async def logout(
    current_user: dict = Depends(get_current_user)
):
    """
    Logout endpoint (placeholder)
    
    Since JWT tokens are stateless, this endpoint serves as a placeholder.
    In a production environment, you might want to implement token blacklisting
    or use a token store for proper logout functionality.
    """
    logger.info(f"User logged out: {current_user['username']}")
    
    return {
        "message": "Successfully logged out",
        "note": "JWT tokens are stateless - ensure client discards the token"
    }


@router.get("/validate", summary="Validate current token")
async def validate_token(
    current_user: dict = Depends(get_current_user)
):
    """
    Validate the current JWT token
    
    Returns user information if token is valid, otherwise returns 401.
    """
    return {
        "valid": True,
        "user": {
            "username": current_user["username"],
            "email": current_user.get("email"),
            "full_name": current_user.get("full_name"),
        },
        "message": "Token is valid"
    }


@router.post("/debug", summary="Debug JWT token (development only)")
async def debug_jwt_token(request_data: dict):
    """
    Debug JWT token information - Compatible with original monolithic endpoint
    
    This endpoint matches the original /debug/jwt from the monolithic app.py
    for development purposes only.
    """
    try:
        from auth import debug_jwt_validation
        import datetime as dt
        
        token = request_data.get("token")
        if not token:
            raise HTTPException(status_code=400, detail="Token requis")
        
        debug_result = debug_jwt_validation(token)
        return {
            "debug_info": debug_result,
            "timestamp": dt.datetime.now().isoformat(),
            "endpoint": "/debug/jwt"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JWT debug error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug JWT failed: {str(e)}"
        )


@router.get("/health", summary="Authentication service health check")
async def auth_health():
    """
    Health check endpoint for authentication service
    
    Returns the status of the authentication system.
    """
    try:
        # Validate JWT key consistency
        from auth import validate_jwt_key_consistency
        
        jwt_key_valid = validate_jwt_key_consistency()
        
        return {
            "status": "healthy" if jwt_key_valid else "warning",
            "service": "authentication",
            "jwt_key_valid": jwt_key_valid,
            "algorithm": settings.security.algorithm,
            "token_expire_minutes": settings.security.access_token_expire_minutes,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Auth health check error: {str(e)}")
        return {
            "status": "error",
            "service": "authentication",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Registration Models
class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None


@router.post("/register", summary="Register a new user")
async def register_user(
    request: Request,
    register_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account
    """
    try:
        # Validate username
        if len(register_data.username) < 3:
            raise HTTPException(status_code=400, detail="Username trop court (min 3 caractères)")
        if len(register_data.username) > 50:
            raise HTTPException(status_code=400, detail="Username trop long (max 50 caractères)")
        
        # Validate password
        if len(register_data.password) < 6:
            raise HTTPException(status_code=400, detail="Mot de passe trop court (min 6 caractères)")
        
        # Check if username already exists
        existing_user = db.query(UserModel).filter(
            UserModel.username == register_data.username.lower()
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce nom d'utilisateur existe déjà"
            )
        
        # Check if email already exists (if provided)
        if register_data.email:
            existing_email = db.query(UserModel).filter(
                UserModel.email == register_data.email.lower()
            ).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cette adresse email est déjà utilisée"
                )
        
        # Create new user
        new_user = UserModel(
            username=register_data.username.lower(),
            email=register_data.email.lower() if register_data.email else None,
            full_name=register_data.full_name,
            hashed_password=hash_password(register_data.password),
            is_active=True,
            is_admin=False
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New user registered: {new_user.username}")
        
        # Auto-login: create token for the new user
        access_token_expires = timedelta(minutes=settings.security.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": new_user.username}, 
            expires_delta=access_token_expires
        )
        
        return {
            "message": "Inscription réussie!",
            "user": {
                "username": new_user.username,
                "email": new_user.email,
                "full_name": new_user.full_name
            },
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.security.access_token_expire_minutes * 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'inscription"
        )
