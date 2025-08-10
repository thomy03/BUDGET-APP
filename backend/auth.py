"""
Module d'authentification sécurisé pour l'application Budget Famille
Implémente JWT avec FastAPI Security et hashage bcrypt
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables BEFORE using them
load_dotenv()

# Logging sécurisé
logger = logging.getLogger(__name__)

# Configuration sécurisée JWT
def get_secure_jwt_key():
    """Génère ou récupère une clé JWT sécurisée"""
    key = os.getenv("JWT_SECRET_KEY")
    
    if not key or key == "CHANGEME_IN_PRODUCTION_URGENT" or len(key) < 32:
        logger.warning("🚨 SÉCURITÉ: Génération d'une nouvelle clé JWT")
        import secrets
        new_key = secrets.token_urlsafe(32)
        logger.info(f"🔑 Nouvelle clé JWT générée. Ajoutez à .env: JWT_SECRET_KEY={new_key}")
        return new_key
    
    logger.info(f"✅ SÉCURITÉ: Utilisation clé JWT depuis .env (longueur: {len(key)})")
    return key

def validate_jwt_key_consistency():
    """Valide que la clé JWT n'a pas changé depuis l'initialisation"""
    current_env_key = os.getenv("JWT_SECRET_KEY")
    if current_env_key and current_env_key != SECRET_KEY:
        logger.error("🚨 CRITICAL: JWT_SECRET_KEY a changé depuis l'initialisation du serveur!")
        logger.error("   Cela causera des échecs d'authentification pour les tokens existants.")
        logger.error(f"   Clé initiale: {SECRET_KEY[:8]}...{SECRET_KEY[-8:]}")
        logger.error(f"   Clé actuelle: {current_env_key[:8]}...{current_env_key[-8:]}")
        return False
    return True

# Initialize JWT secret key once at module level to prevent changes during runtime
SECRET_KEY = get_secure_jwt_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Log initialization for debugging
logger.info(f"🔐 JWT SECRET_KEY initialisé: {SECRET_KEY[:8]}...{SECRET_KEY[-8:]} (longueur: {len(SECRET_KEY)})")

# Configuration bcrypt pour hashage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str

class UserInDB(User):
    hashed_password: str

# Base de données utilisateur simple (en production: base sécurisée)
# CHANGEME: Remplacer par base chiffrée
fake_users_db = {
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$4A9H9JK7bYMdk7oYEeO/a.2FqfkGRp2HPvrx4BKEjDpYdM/Zmyf0G"  # "secret" 
    }
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie le mot de passe avec bcrypt"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Erreur vérification mot de passe: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Hash le mot de passe avec bcrypt"""
    return pwd_context.hash(password)

def get_user(db: dict, username: str) -> Optional[UserInDB]:
    """Récupère un utilisateur depuis la base"""
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(db: dict, username: str, password: str) -> Optional[UserInDB]:
    """Authentifie un utilisateur"""
    user = get_user(db, username)
    if not user:
        logger.warning(f"Tentative connexion utilisateur inexistant: {username}")
        return None
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Mot de passe incorrect pour utilisateur: {username}")
        return None
    logger.info(f"Connexion réussie pour utilisateur: {username}")
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crée un token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Dépendance FastAPI pour récupérer l'utilisateur actuel depuis le token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        
        # Validate JWT key consistency before attempting decode
        if not validate_jwt_key_consistency():
            logger.error("Token JWT invalide: Clé JWT a changé depuis l'initialisation")
            raise credentials_exception
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token JWT invalide: sub claim manquant")
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.ExpiredSignatureError:
        logger.warning("Token JWT invalide: Token expiré")
        raise credentials_exception
    except jwt.InvalidSignatureError:
        logger.error(f"Token JWT invalide: Signature verification failed - SECRET_KEY length: {len(SECRET_KEY)}")
        raise credentials_exception
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token JWT invalide: Token format invalide - {e}")
        raise credentials_exception
    except JWTError as e:
        logger.error(f"Token JWT invalide: Erreur JWT inattendue - {e}")
        raise credentials_exception
    
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

# SÉCURITÉ: Fonction pour générer un nouveau secret
def generate_secret_key():
    """Génère une clé secrète sécurisée"""
    import secrets
    return secrets.token_urlsafe(32)

def debug_jwt_validation(token: str) -> dict:
    """Fonction de debugging pour analyser un token JWT"""
    try:
        # Décoder sans vérification pour inspection
        unverified_payload = jwt.get_unverified_claims(token)
        
        # Essayer de décoder avec vérification
        try:
            verified_payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return {
                "status": "valid",
                "payload": verified_payload,
                "unverified_payload": unverified_payload,
                "secret_key_length": len(SECRET_KEY),
                "algorithm": ALGORITHM
            }
        except jwt.ExpiredSignatureError:
            return {
                "status": "expired",
                "payload": None,
                "unverified_payload": unverified_payload,
                "secret_key_length": len(SECRET_KEY),
                "algorithm": ALGORITHM,
                "error": "Token expired"
            }
        except JWTError as e:
            error_msg = str(e)
            if "Signature verification failed" in error_msg:
                status = "invalid_signature"
                error = "Invalid signature - possible secret key mismatch"
            else:
                status = "jwt_error"
                error = f"JWT Error: {error_msg}"
            
            return {
                "status": status, 
                "payload": None,
                "unverified_payload": unverified_payload,
                "secret_key_length": len(SECRET_KEY),
                "algorithm": ALGORITHM,
                "error": error
            }
        except Exception as e:
            return {
                "status": "error",
                "payload": None,
                "unverified_payload": unverified_payload,
                "secret_key_length": len(SECRET_KEY),
                "algorithm": ALGORITHM,
                "error": str(e)
            }
    except Exception as e:
        return {
            "status": "malformed",
            "payload": None,
            "unverified_payload": None,
            "secret_key_length": len(SECRET_KEY),
            "algorithm": ALGORITHM,
            "error": f"Cannot decode token: {str(e)}"
        }