"""
Module d'authentification sécurisé avancé pour l'application Budget Famille
Implémente JWT avec httpOnly cookies, rotation de tokens, et sécurité renforcée
"""

import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

import bcrypt as bcrypt_lib
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from dotenv import load_dotenv
import redis
from audit_logger import get_audit_logger, AuditEventType

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Configuration sécurisée avancée
class SecurityConfig:
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    JWT_ALGORITHM = "HS256"
    
    # Configuration Redis pour blacklist tokens
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Rate limiting
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))
    
    # Session security
    SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    MAX_CONCURRENT_SESSIONS = int(os.getenv("MAX_CONCURRENT_SESSIONS", "3"))

@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

@dataclass
class UserSession:
    username: str
    session_id: str
    created_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent_hash: str
    is_active: bool = True

class SecureTokenManager:
    def __init__(self):
        self.access_secret = self._get_secure_key("JWT_ACCESS_SECRET_KEY")
        self.refresh_secret = self._get_secure_key("JWT_REFRESH_SECRET_KEY")
        self.redis_client = self._get_redis_client()
        self.config = SecurityConfig()
        
    def _get_secure_key(self, env_key: str) -> str:
        """Génère ou récupère une clé JWT sécurisée"""
        key = os.getenv(env_key)
        
        if not key or len(key) < 32:
            logger.warning(f"🚨 SÉCURITÉ: Génération nouvelle clé {env_key}")
            new_key = secrets.token_urlsafe(32)
            logger.info(f"🔑 Ajoutez à .env: {env_key}={new_key}")
            return new_key
        
        logger.info(f"✅ Clé {env_key} chargée (longueur: {len(key)})")
        return key
    
    def _get_redis_client(self):
        """Initialise la connexion Redis avec fallback"""
        try:
            import redis
            client = redis.from_url(self.config.REDIS_URL, decode_responses=True)
            client.ping()
            logger.info("✅ Redis connecté pour gestion sessions")
            return client
        except Exception as e:
            logger.warning(f"⚠️ Redis non disponible: {e}")
            logger.warning("Utilisation fallback mémoire (non recommandé en production)")
            return None
    
    def create_token_pair(self, username: str, user_data: Dict[str, Any] = None) -> TokenPair:
        """Crée une paire access/refresh token sécurisée"""
        now = datetime.utcnow()
        session_id = secrets.token_urlsafe(16)
        
        # Access token (courte durée)
        access_payload = {
            "sub": username,
            "session_id": session_id,
            "token_type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self.config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            **(user_data or {})
        }
        
        # Refresh token (longue durée)
        refresh_payload = {
            "sub": username,
            "session_id": session_id,
            "token_type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self.config.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        }
        
        access_token = jwt.encode(access_payload, self.access_secret, algorithm=self.config.JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, self.refresh_secret, algorithm=self.config.JWT_ALGORITHM)
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Vérifie et décode un access token"""
        try:
            payload = jwt.decode(token, self.access_secret, algorithms=[self.config.JWT_ALGORITHM])
            
            if payload.get("token_type") != "access":
                raise JWTError("Invalid token type")
            
            # Vérifier blacklist
            if self._is_token_blacklisted(token):
                raise JWTError("Token blacklisted")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token expired"
            )
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid access token: {str(e)}"
            )
    
    def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """Vérifie et décode un refresh token"""
        try:
            payload = jwt.decode(token, self.refresh_secret, algorithms=[self.config.JWT_ALGORITHM])
            
            if payload.get("token_type") != "refresh":
                raise JWTError("Invalid token type")
            
            # Vérifier blacklist
            if self._is_token_blacklisted(token):
                raise JWTError("Token blacklisted")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid refresh token: {str(e)}"
            )
    
    def blacklist_token(self, token: str, expiry_seconds: int = None):
        """Ajoute un token à la blacklist"""
        if not self.redis_client:
            logger.warning("Redis non disponible - blacklist non persistante")
            return
        
        if expiry_seconds is None:
            expiry_seconds = self.config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        self.redis_client.setex(f"blacklist:{token}", expiry_seconds, "1")
    
    def _is_token_blacklisted(self, token: str) -> bool:
        """Vérifie si un token est blacklisté"""
        if not self.redis_client:
            return False
        
        return self.redis_client.exists(f"blacklist:{token}")
    
    def invalidate_user_sessions(self, username: str):
        """Invalide toutes les sessions d'un utilisateur"""
        if not self.redis_client:
            return
        
        # Récupérer toutes les sessions utilisateur
        session_keys = self.redis_client.keys(f"session:{username}:*")
        
        for key in session_keys:
            self.redis_client.delete(key)
        
        logger.info(f"Sessions invalidées pour utilisateur: {username}")

class RateLimiter:
    """Rate limiter avancé avec protection contre brute force"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.config = SecurityConfig()
    
    def check_login_attempts(self, identifier: str) -> bool:
        """Vérifie si l'identifiant peut tenter une connexion"""
        if not self.redis_client:
            return True  # Pas de rate limiting sans Redis
        
        key = f"login_attempts:{identifier}"
        attempts = self.redis_client.get(key)
        
        if attempts and int(attempts) >= self.config.MAX_LOGIN_ATTEMPTS:
            logger.warning(f"Rate limit atteint pour: {identifier}")
            return False
        
        return True
    
    def record_failed_attempt(self, identifier: str):
        """Enregistre une tentative de connexion échouée"""
        if not self.redis_client:
            return
        
        key = f"login_attempts:{identifier}"
        pipe = self.redis_client.pipeline()
        
        pipe.incr(key)
        pipe.expire(key, self.config.LOCKOUT_DURATION_MINUTES * 60)
        pipe.execute()
        
        attempts = self.redis_client.get(key)
        logger.info(f"Tentative échouée {attempts}/{self.config.MAX_LOGIN_ATTEMPTS} pour: {identifier}")
    
    def clear_failed_attempts(self, identifier: str):
        """Efface les tentatives échouées après connexion réussie"""
        if not self.redis_client:
            return
        
        self.redis_client.delete(f"login_attempts:{identifier}")

class SessionManager:
    """Gestion avancée des sessions utilisateur"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.config = SecurityConfig()
    
    def create_session(self, username: str, session_id: str, ip_address: str, user_agent: str) -> UserSession:
        """Crée une nouvelle session utilisateur"""
        session = UserSession(
            username=username,
            session_id=session_id,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            ip_address=ip_address,
            user_agent_hash=self._hash_user_agent(user_agent)
        )
        
        if self.redis_client:
            self._store_session(session)
            self._enforce_session_limit(username)
        
        return session
    
    def update_session_activity(self, session_id: str, username: str):
        """Met à jour l'activité de la session"""
        if not self.redis_client:
            return
        
        key = f"session:{username}:{session_id}"
        session_data = self.redis_client.hget(key, "data")
        
        if session_data:
            import json
            session = json.loads(session_data)
            session["last_activity"] = datetime.utcnow().isoformat()
            
            self.redis_client.hset(key, "data", json.dumps(session))
            self.redis_client.expire(key, self.config.SESSION_TIMEOUT_MINUTES * 60)
    
    def validate_session(self, session_id: str, username: str) -> bool:
        """Valide une session existante"""
        if not self.redis_client:
            return True
        
        key = f"session:{username}:{session_id}"
        return self.redis_client.exists(key)
    
    def invalidate_session(self, session_id: str, username: str):
        """Invalide une session spécifique"""
        if not self.redis_client:
            return
        
        key = f"session:{username}:{session_id}"
        self.redis_client.delete(key)
    
    def _store_session(self, session: UserSession):
        """Stocke une session en Redis"""
        import json
        key = f"session:{session.username}:{session.session_id}"
        
        session_data = {
            "username": session.username,
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "ip_address_hash": self._hash_ip(session.ip_address),
            "user_agent_hash": session.user_agent_hash,
            "is_active": session.is_active
        }
        
        self.redis_client.hset(key, "data", json.dumps(session_data))
        self.redis_client.expire(key, self.config.SESSION_TIMEOUT_MINUTES * 60)
    
    def _enforce_session_limit(self, username: str):
        """Applique la limite de sessions simultanées"""
        if not self.redis_client:
            return
        
        # Récupérer toutes les sessions actives
        session_keys = self.redis_client.keys(f"session:{username}:*")
        
        if len(session_keys) > self.config.MAX_CONCURRENT_SESSIONS:
            # Supprimer les sessions les plus anciennes
            sessions_data = []
            for key in session_keys:
                data = self.redis_client.hget(key, "data")
                if data:
                    import json
                    session_info = json.loads(data)
                    session_info["redis_key"] = key
                    sessions_data.append(session_info)
            
            # Trier par création (plus ancien en premier)
            sessions_data.sort(key=lambda x: x["created_at"])
            
            # Supprimer les sessions excédentaires
            excess_count = len(sessions_data) - self.config.MAX_CONCURRENT_SESSIONS + 1
            for i in range(excess_count):
                self.redis_client.delete(sessions_data[i]["redis_key"])
                logger.info(f"Session expirée pour limite dépassée: {username}")
    
    def _hash_ip(self, ip_address: str) -> str:
        """Hash l'adresse IP pour la confidentialité"""
        import hashlib
        salt = os.getenv("SESSION_SALT", "budget_app_session_2024")
        return hashlib.sha256(f"{salt}:{ip_address}".encode()).hexdigest()[:16]
    
    def _hash_user_agent(self, user_agent: str) -> str:
        """Hash le User-Agent pour la confidentialité"""
        import hashlib
        salt = os.getenv("SESSION_SALT", "budget_app_session_2024")
        return hashlib.sha256(f"{salt}:{user_agent}".encode()).hexdigest()[:16]

# Instances globales
token_manager = SecureTokenManager()
rate_limiter = RateLimiter(token_manager.redis_client)
session_manager = SessionManager(token_manager.redis_client)

class SecureAuthenticationService:
    """Service d'authentification sécurisé principal"""

    def __init__(self):
        self.token_manager = token_manager
        self.rate_limiter = rate_limiter
        self.session_manager = session_manager
        self.audit_logger = get_audit_logger()
        # Using bcrypt directly instead of passlib to avoid compatibility issues with bcrypt 4.x
    
    async def authenticate(self, username: str, password: str, request: Request) -> TokenPair:
        """Authentification sécurisée avec protection brute force"""
        
        # Identifier unique (IP + username)
        client_ip = self._get_client_ip(request)
        identifier = f"{client_ip}:{username}"
        
        # Vérifier rate limiting
        if not self.rate_limiter.check_login_attempts(identifier):
            self.audit_logger.log_security_violation(
                username=username,
                ip_address=client_ip,
                violation_type="rate_limit_exceeded",
                details={"endpoint": "/token"}
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives. Réessayez plus tard."
            )
        
        # Vérifier authentification
        user = self._verify_credentials(username, password)
        if not user:
            # Enregistrer tentative échouée
            self.rate_limiter.record_failed_attempt(identifier)
            self.audit_logger.log_login_failed(
                username=username,
                ip_address=client_ip,
                reason="Invalid credentials"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nom d'utilisateur ou mot de passe incorrect"
            )
        
        # Effacer tentatives échouées
        self.rate_limiter.clear_failed_attempts(identifier)
        
        # Créer tokens
        tokens = self.token_manager.create_token_pair(username)
        
        # Créer session
        user_agent = request.headers.get("user-agent", "")
        session_id = jwt.decode(tokens.access_token, options={"verify_signature": False})["session_id"]
        
        self.session_manager.create_session(
            username=username,
            session_id=session_id,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # Audit
        self.audit_logger.log_login_success(
            username=username,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        logger.info(f"Connexion sécurisée réussie: {username}")
        return tokens
    
    async def refresh_token(self, refresh_token: str, request: Request) -> TokenPair:
        """Renouvellement sécurisé des tokens"""
        
        # Vérifier refresh token
        payload = self.token_manager.verify_refresh_token(refresh_token)
        username = payload["sub"]
        session_id = payload["session_id"]
        
        # Vérifier session
        if not self.session_manager.validate_session(session_id, username):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session invalide"
            )
        
        # Blacklister ancien refresh token
        self.token_manager.blacklist_token(refresh_token, 
                                         SecurityConfig.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)
        
        # Créer nouveaux tokens
        new_tokens = self.token_manager.create_token_pair(username)
        
        # Mettre à jour session
        new_session_id = jwt.decode(new_tokens.access_token, options={"verify_signature": False})["session_id"]
        self.session_manager.invalidate_session(session_id, username)
        
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        self.session_manager.create_session(
            username=username,
            session_id=new_session_id,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        logger.info(f"Token renouvelé avec succès: {username}")
        return new_tokens
    
    async def logout(self, access_token: str, refresh_token: str = None):
        """Déconnexion sécurisée"""
        
        try:
            # Décoder token pour récupérer info session
            payload = self.token_manager.verify_access_token(access_token)
            username = payload["sub"]
            session_id = payload["session_id"]
            
            # Blacklister tokens
            self.token_manager.blacklist_token(access_token)
            if refresh_token:
                self.token_manager.blacklist_token(refresh_token, 
                                                 SecurityConfig.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)
            
            # Invalider session
            self.session_manager.invalidate_session(session_id, username)
            
            # Audit
            self.audit_logger.log_event(
                AuditEventType.LOGOUT,
                username=username,
                success=True
            )
            
            logger.info(f"Déconnexion sécurisée: {username}")
            
        except Exception as e:
            logger.warning(f"Erreur lors de la déconnexion: {e}")
            # Même en cas d'erreur, considérer la déconnexion comme réussie côté client
    
    def _verify_credentials(self, username: str, password: str) -> Optional[dict]:
        """Vérifier les identifiants utilisateur using bcrypt directly (compatible bcrypt 4.x)"""
        # TODO: Remplacer par vraie base d'utilisateurs
        fake_users = {
            "admin": {
                "username": "admin",
                "hashed_password": "$2b$12$tc88iTlfmRyjOGwvM9MshuSpmn1JLO4dvJYIZBIKQn.0g8mYl5XVG"  # test123
            }
        }

        user_data = fake_users.get(username)
        if not user_data:
            return None

        try:
            if not bcrypt_lib.checkpw(password.encode('utf-8'), user_data["hashed_password"].encode('utf-8')):
                return None
        except Exception:
            return None

        return user_data
    
    def _get_client_ip(self, request: Request) -> str:
        """Récupère l'IP client avec support proxy"""
        # Headers proxy communs
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"

# Dépendance FastAPI pour authentification
security = HTTPBearer()
auth_service = SecureAuthenticationService()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dépendance FastAPI pour récupérer l'utilisateur authentifié"""
    
    token = credentials.credentials
    
    try:
        # Vérifier access token
        payload = token_manager.verify_access_token(token)
        username = payload["sub"]
        session_id = payload["session_id"]
        
        # Vérifier session active
        if not session_manager.validate_session(session_id, username):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expirée"
            )
        
        # Mettre à jour activité session
        session_manager.update_session_activity(session_id, username)
        
        return {
            "username": username,
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur vérification token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide"
        )

# Fonction utilitaire pour définir cookie sécurisé
def set_secure_cookie(response: Response, name: str, value: str, max_age: int):
    """Définit un cookie sécurisé httpOnly"""
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=True,
        secure=True,  # HTTPS uniquement en production
        samesite="strict"
    )