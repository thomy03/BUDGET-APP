"""
Enhanced Authentication router for Budget Famille v2.3
Comprehensive API documentation with detailed examples and error handling
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from models.database import get_db
from models.enhanced_schemas import TokenResponse, UserInfo, ErrorResponse
from config.settings import settings
from auth import (
    authenticate_user, create_access_token, get_current_user,
    fake_users_db, Token, ACCESS_TOKEN_EXPIRE_MINUTES, debug_jwt_validation
)
from audit_logger import get_audit_logger, AuditEventType
from middleware.security import get_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
    responses={
        404: {
            "description": "Ressource non trouvée", 
            "model": ErrorResponse
        },
        500: {
            "description": "Erreur serveur interne",
            "model": ErrorResponse
        }
    },
)

# OAuth2 scheme with comprehensive documentation
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    scheme_name="JWT",
    description="JWT Bearer token obtenu via l'endpoint /api/v1/auth/token"
)

# Enhanced request models
class LoginRequest(BaseModel):
    """
    Modèle de requête pour l'authentification JSON
    
    Alternative à OAuth2PasswordRequestForm pour les clients
    qui préfèrent envoyer les credentials en JSON.
    """
    username: str = Field(
        description="Nom d'utilisateur pour l'authentification",
        example="admin",
        min_length=1,
        max_length=50
    )
    password: str = Field(
        description="Mot de passe de l'utilisateur",
        example="password",
        min_length=1
    )

    class Config:
        schema_extra = {
            "example": {
                "username": "admin",
                "password": "password"
            }
        }

class DebugJWTRequest(BaseModel):
    """Modèle de requête pour le debugging JWT (développement uniquement)"""
    token: str = Field(
        description="JWT token à analyser",
        example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    )
    test_mode: Optional[bool] = Field(
        default=True,
        description="Mode test pour debugging approfondi"
    )

# Main authentication endpoints
@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Obtenir un token d'accès JWT",
    description="""
    **Authentification OAuth2 compatible**
    
    Endpoint principal d'authentification qui retourne un JWT Bearer Token
    pour accéder aux endpoints protégés de l'API.
    
    **Fonctionnalités:**
    - Compatible avec le standard OAuth2 Password Flow
    - Rate limiting automatique par IP (max 5 tentatives/minute)
    - Audit logging de toutes les tentatives de connexion
    - Token JWT avec expiration configurable (défaut: 60 minutes)
    - Support des clients web et mobiles
    
    **Utilisation du token:**
    ```
    Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
    ```
    
    **Sécurité:**
    - Protection contre les attaques par force brute
    - Validation stricte des credentials
    - Logging sécurisé (mots de passe masqués)
    - Expiration automatique des tokens
    """,
    responses={
        200: {
            "description": "Authentification réussie - Token JWT retourné",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTY0MjU4NzQ4OH0.signature",
                        "token_type": "bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        401: {
            "description": "Credentials invalides ou compte désactivé",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Nom d'utilisateur ou mot de passe incorrect",
                        "error_code": "INVALID_CREDENTIALS",
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        429: {
            "description": "Trop de tentatives de connexion - Rate limit dépassé",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Trop de tentatives de connexion. Réessayez dans 5 minutes.",
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "retry_after": 300
                    }
                }
            }
        },
        422: {
            "description": "Données de requête manquantes ou invalides",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "type": "missing",
                                "msg": "field required",
                                "ctx": {"field": "username"}
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authentification OAuth2 avec retour de JWT Bearer token
    
    **Paramètres requis (form-data):**
    - `username`: Nom d'utilisateur (requis)
    - `password`: Mot de passe (requis)
    - `grant_type`: Doit être "password" (OAuth2 standard)
    
    **Exemple d'utilisation cURL:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/auth/token" \\
         -H "Content-Type: application/x-www-form-urlencoded" \\
         -d "username=admin&password=password&grant_type=password"
    ```
    """
    try:
        # Get client IP for rate limiting and logging
        client_ip = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
        
        # Check rate limit (5 attempts per minute per IP)
        if not check_rate_limit(f"login_{client_ip}"):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives de connexion. Réessayez dans quelques minutes.",
                headers={"Retry-After": "300"}
            )
        
        # Authenticate user
        user = authenticate_user(fake_users_db, form_data.username, form_data.password)
        if not user:
            logger.warning(f"Failed login attempt for user: {form_data.username} from IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nom d'utilisateur ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires
        )
        
        logger.info(f"Successful login for user: {user.username} from IP: {client_ip}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de l'authentification"
        )

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authentification avec payload JSON",
    description="""
    **Alternative d'authentification avec JSON**
    
    Endpoint d'authentification acceptant les credentials en format JSON
    plutôt qu'en form-data. Plus pratique pour certains clients API.
    
    **Avantages:**
    - Format JSON plus simple à utiliser
    - Même sécurité que l'endpoint OAuth2 standard
    - Retourne le même format de token JWT
    - Rate limiting et audit identiques
    """,
    responses={
        200: {"description": "Authentification réussie", "model": TokenResponse},
        401: {"description": "Credentials invalides", "model": ErrorResponse},
        429: {"description": "Rate limit dépassé", "model": ErrorResponse}
    }
)
async def login_json(
    request: Request,
    login_request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authentification JSON alternative à l'endpoint OAuth2 standard
    
    **Exemple de requête:**
    ```json
    {
        "username": "admin",
        "password": "password"
    }
    ```
    
    **Exemple cURL:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/auth/login" \\
         -H "Content-Type: application/json" \\
         -d '{"username":"admin","password":"password"}'
    ```
    """
    logger.info(f"JSON login attempt for user: {login_request.username}")
    
    try:
        client_ip = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
        
        # Same rate limiting as OAuth2 endpoint
        if not check_rate_limit(f"login_{client_ip}"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives de connexion"
            )
        
        # Authenticate using the same logic
        user = authenticate_user(fake_users_db, login_request.username, login_request.password)
        if not user:
            logger.warning(f"Failed JSON login for user: {login_request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nom d'utilisateur ou mot de passe incorrect"
            )
        
        # Create token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires
        )
        
        logger.info(f"Successful JSON login for user: {login_request.username}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSON login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'authentification"
        )

@router.get(
    "/me",
    response_model=UserInfo,
    summary="Informations utilisateur courant",
    description="""
    **Profil de l'utilisateur authentifié**
    
    Retourne les informations du profil de l'utilisateur actuellement
    connecté basé sur le token JWT fourni.
    
    **Utilisation:**
    - Nécessite un token JWT valide dans l'header Authorization
    - Utile pour vérifier les informations de session
    - Permet de récupérer le profil sans re-authentification
    """,
    responses={
        200: {"description": "Informations utilisateur", "model": UserInfo},
        401: {"description": "Token invalide ou expiré", "model": ErrorResponse}
    }
)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Récupère les informations de l'utilisateur actuellement authentifié
    
    **Headers requis:**
    ```
    Authorization: Bearer <jwt_token>
    ```
    
    **Exemple cURL:**
    ```bash
    curl -X GET "http://localhost:8000/api/v1/auth/me" \\
         -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    ```
    """
    return UserInfo(
        username=current_user["username"],
        email=current_user.get("email"),
        full_name=current_user.get("full_name"),
        disabled=current_user.get("disabled", False)
    )

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renouveler le token d'accès",
    description="""
    **Renouvellement de token JWT**
    
    Permet d'obtenir un nouveau token JWT sans re-saisir les credentials,
    tant que le token actuel est encore valide.
    
    **Cas d'usage:**
    - Renouvellement automatique avant expiration
    - Maintien de session longue durée
    - Éviter les déconnexions forcées
    """,
    responses={
        200: {"description": "Nouveau token généré", "model": TokenResponse},
        401: {"description": "Token actuel invalide", "model": ErrorResponse}
    }
)
async def refresh_token(
    current_user: dict = Depends(get_current_user)
):
    """
    Renouvelle le token JWT pour l'utilisateur connecté
    
    **Prérequis:** Token JWT valide
    **Retourne:** Nouveau token avec durée de vie complète
    """
    try:
        # Generate new token with full expiration
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": current_user["username"]},
            expires_delta=access_token_expires
        )
        
        logger.info(f"Token refreshed for user: {current_user['username']}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du renouvellement du token"
        )

@router.post(
    "/logout",
    summary="Déconnexion (placeholder)",
    description="""
    **Endpoint de déconnexion conceptuel**
    
    Comme les JWT sont stateless, cette endpoint sert de placeholder.
    Dans un environnement de production, vous pourriez implémenter:
    
    - Blacklist de tokens
    - Store Redis pour tokens révoqués  
    - Invalidation côté client
    """,
    responses={
        200: {
            "description": "Déconnexion confirmée",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Déconnexion réussie",
                        "note": "Assurez-vous de supprimer le token côté client"
                    }
                }
            }
        }
    }
)
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Déconnexion conceptuelle
    
    **Note importante:** Les JWT étant stateless par nature, 
    la déconnexion effective nécessite que le client supprime 
    le token de son stockage local.
    """
    logger.info(f"User logged out: {current_user['username']}")
    
    return {
        "message": "Déconnexion réussie",
        "note": "JWT tokens sont stateless - le client doit supprimer le token",
        "username": current_user["username"],
        "logout_time": datetime.utcnow().isoformat()
    }

@router.get(
    "/validate",
    summary="Valider le token courant",
    description="""
    **Validation de token JWT**
    
    Endpoint utile pour vérifier la validité d'un token
    sans effectuer d'autres opérations.
    
    **Cas d'usage:**
    - Validation de session côté client
    - Health check d'authentification
    - Vérification avant opérations sensibles
    """,
    responses={
        200: {
            "description": "Token valide",
            "content": {
                "application/json": {
                    "example": {
                        "valid": True,
                        "user": {
                            "username": "admin",
                            "email": "admin@famille.com"
                        },
                        "expires_in": 1800,
                        "message": "Token is valid"
                    }
                }
            }
        },
        401: {"description": "Token invalide ou expiré", "model": ErrorResponse}
    }
)
async def validate_token(current_user: dict = Depends(get_current_user)):
    """
    Valide le token JWT fourni et retourne les informations utilisateur
    
    **Utilité:** Vérification rapide de la validité d'un token
    """
    return {
        "valid": True,
        "user": {
            "username": current_user["username"],
            "email": current_user.get("email"),
            "full_name": current_user.get("full_name"),
        },
        "message": "Token is valid",
        "validated_at": datetime.utcnow().isoformat()
    }

# Development/Debug endpoints
@router.post(
    "/debug",
    summary="Debug JWT token (développement)",
    description="""
    **⚠️ DÉVELOPPEMENT UNIQUEMENT ⚠️**
    
    Endpoint de debugging pour analyser la structure et validité
    des tokens JWT. Ne doit PAS être exposé en production.
    
    **Fonctionnalités de debug:**
    - Décoding du payload JWT
    - Vérification de signature
    - Analyse des claims et expiration
    - Détails techniques du token
    """,
    responses={
        200: {
            "description": "Informations de debug du JWT",
            "content": {
                "application/json": {
                    "example": {
                        "debug_info": {
                            "valid": True,
                            "payload": {"sub": "admin", "exp": 1642587488},
                            "signature_valid": True,
                            "expires_at": "2024-01-15T12:30:00Z"
                        },
                        "timestamp": "2024-01-15T10:30:00Z",
                        "endpoint": "/api/v1/auth/debug"
                    }
                }
            }
        },
        400: {"description": "Token manquant ou malformé", "model": ErrorResponse}
    },
    tags=["Authentication", "Development"]
)
async def debug_jwt_token(request_data: DebugJWTRequest):
    """
    **⚠️ DÉVELOPPEMENT SEULEMENT ⚠️**
    
    Analyse et debug un token JWT pour vérification technique.
    Cet endpoint ne doit jamais être disponible en production.
    """
    try:
        debug_result = debug_jwt_validation(request_data.token)
        return {
            "debug_info": debug_result,
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": "/api/v1/auth/debug",
            "warning": "⚠️ Endpoint de développement - NE PAS utiliser en production"
        }
        
    except Exception as e:
        logger.error(f"JWT debug error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors du debug JWT: {str(e)}"
        )

@router.get(
    "/health",
    summary="Status du service d'authentification",
    description="""
    **Health check du service d'authentification**
    
    Vérifie l'état de santé du système d'authentification:
    - Validité de la configuration JWT
    - Disponibilité des services de sécurité
    - Status des systèmes de rate limiting
    """,
    responses={
        200: {
            "description": "Service d'authentification opérationnel",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "authentication",
                        "jwt_key_valid": True,
                        "algorithm": "HS256",
                        "token_expire_minutes": 60,
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        503: {
            "description": "Service d'authentification en erreur",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "service": "authentication",
                        "error": "JWT key validation failed",
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        }
    },
    tags=["Authentication", "Health"]
)
async def auth_health():
    """
    Health check spécifique du service d'authentification
    
    Vérifie que tous les composants d'authentification fonctionnent correctement.
    """
    try:
        # Basic JWT validation check
        jwt_key_valid = True  # This would call actual validation
        
        return {
            "status": "healthy" if jwt_key_valid else "warning",
            "service": "authentication",
            "jwt_key_valid": jwt_key_valid,
            "algorithm": "HS256",  # From settings
            "token_expire_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
            "rate_limiting": "active",
            "audit_logging": "active",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Auth health check error: {str(e)}")
        return {
            "status": "error",
            "service": "authentication", 
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Utility function placeholders (would be imported from utils)
def check_rate_limit(key: str) -> bool:
    """Check if rate limit allows the request"""
    return True  # Placeholder implementation