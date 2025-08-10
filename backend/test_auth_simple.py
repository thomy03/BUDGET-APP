#!/usr/bin/env python3
"""
Script simple pour tester l'authentification FastAPI
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
import hashlib

# Configuration
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Base de données simple en mémoire
fake_users_db = {
    "admin": {
        "username": "admin",
        "hashed_password": hashlib.sha256("secret".encode()).hexdigest(),  # Simple hash pour test
    }
}

# Models Pydantic
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str

# FastAPI app
app = FastAPI(title="Budget API Test", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:45678",
        "http://127.0.0.1:45678"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier le mot de passe"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def authenticate_user(username: str, password: str):
    """Authentifier un utilisateur"""
    user = fake_users_db.get(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Créer un token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Obtenir l'utilisateur courant depuis le token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = fake_users_db.get(username)
    if user is None:
        raise credentials_exception
    return user

@app.get("/")
async def root():
    """Endpoint racine"""
    return {"message": "Budget API Test - OK"}

@app.get("/health")
async def health():
    """Endpoint de santé"""
    return {"status": "OK", "timestamp": datetime.utcnow()}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint d'authentification"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=User)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """Obtenir les informations de l'utilisateur courant"""
    return {"username": current_user["username"]}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Démarrage du serveur test d'authentification...")
    print("📍 URL: http://127.0.0.1:8002")
    print("🔑 Identifiants: admin / secret")
    print("📄 Documentation: http://127.0.0.1:8002/docs")
    uvicorn.run(app, host="127.0.0.1", port=8002)