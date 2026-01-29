"""
Module d'authentification sécurisé pour l'application Budget Famille
Implémente JWT avec FastAPI Security et hashage bcrypt
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables BEFORE using them
load_dotenv()

# Logging sécurisé
logger = logging.getLogger(__name__)

# Configuration sécurisée JWT
def get_secure_jwt_key() -> str:
    """
    Récupère une clé JWT sécurisée - OBLIGATOIRE en production.

    En production, la variable JWT_SECRET_KEY DOIT être définie.
    En développement, une clé temporaire est générée (avec avertissement).
    """
    key = os.getenv("JWT_SECRET_KEY")
    environment = os.getenv("ENVIRONMENT", "development").lower()

    # Vérifier si la clé est valide
    # Liste des patterns de clés placeholder à rejeter
    placeholder_patterns = [
        "CHANGEME",
        "GENERATE",
        "REPLACE",
        "YOUR_KEY",
        "YOUR_SECRET",
        "EXAMPLE",
        "PLACEHOLDER",
        "TODO",
        "FIXME"
    ]
    is_placeholder = key and any(pattern in key.upper() for pattern in placeholder_patterns)
    is_valid_key = key and len(key) >= 32 and not is_placeholder

    if not is_valid_key:
        if environment == "production":
            # En production, la clé est OBLIGATOIRE
            error_msg = (
                "SECURITE CRITIQUE: JWT_SECRET_KEY doit etre defini en production! "
                "Generez avec: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
            logger.error(f"🚨 {error_msg}")
            raise ValueError(error_msg)

        # Uniquement en développement: générer une clé temporaire
        import secrets
        new_key = secrets.token_urlsafe(64)
        logger.warning("🚨 DEV ONLY: Generation cle JWT temporaire - NE PAS UTILISER EN PRODUCTION!")
        logger.warning(f"🔑 Ajoutez a .env: JWT_SECRET_KEY={new_key}")
        return new_key

    logger.info(f"✅ SECURITE: Utilisation cle JWT depuis .env (longueur: {len(key)})")
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
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes - security best practice

# Log initialization for debugging
logger.info(f"🔐 JWT SECRET_KEY initialisé: {SECRET_KEY[:8]}...{SECRET_KEY[-8:]} (longueur: {len(SECRET_KEY)})")

# Configuration bcrypt pour hashage des mots de passe
# Note: Using bcrypt directly instead of passlib to avoid compatibility issues with bcrypt 4.x
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

# Base de données utilisateur - chargée depuis variables d'environnement
def get_users_from_env() -> dict:
    """
    Charge les utilisateurs depuis les variables d'environnement.

    En production, ADMIN_PASSWORD_HASH est OBLIGATOIRE.
    En développement, un hash par défaut est utilisé avec avertissement.

    Variables d'environnement:
    - ADMIN_USERNAME: Nom d'utilisateur admin (défaut: "admin")
    - ADMIN_PASSWORD_HASH: Hash bcrypt du mot de passe (OBLIGATOIRE en production)

    Générer un hash avec:
    python -c "import bcrypt; print(bcrypt.hashpw(b'votre_mot_de_passe', bcrypt.gensalt()).decode())"
    """
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH")
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if not admin_password_hash:
        if environment == "production":
            error_msg = (
                "SECURITE CRITIQUE: ADMIN_PASSWORD_HASH non defini en production! "
                "Generez un hash avec: python -c \"import bcrypt; print(bcrypt.hashpw(b'votre_mot_de_passe', bcrypt.gensalt()).decode())\""
            )
            logger.error(f"🚨 {error_msg}")
            raise ValueError(error_msg)

        # En développement uniquement: utiliser un hash par défaut (INSECURE!)
        # Hash pour "secret" - A NE JAMAIS UTILISER EN PRODUCTION
        logger.warning("🚨 DEV ONLY: Utilisation hash par defaut 'secret' - NE PAS UTILISER EN PRODUCTION!")
        admin_password_hash = "$2b$12$4A9H9JK7bYMdk7oYEeO/a.2FqfkGRp2HPvrx4BKEjDpYdM/Zmyf0G"

    return {
        admin_username: {
            "username": admin_username,
            "hashed_password": admin_password_hash
        }
    }


# Initialiser la base utilisateurs au démarrage
fake_users_db = get_users_from_env()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie le mot de passe avec bcrypt directement (compatible bcrypt 4.x)"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Erreur vérification mot de passe: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Hash le mot de passe avec bcrypt directement (compatible bcrypt 4.x)"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

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
    except JWTError as e:
        logger.error(f"Token JWT invalide: {type(e).__name__} - {e}")
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