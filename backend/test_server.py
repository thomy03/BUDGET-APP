#!/usr/bin/env python3
"""
Simple test server for E2E validation
Bypasses complex settings configuration for basic functionality testing
"""
import datetime as dt
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.sql import func
import os
from datetime import timedelta

# Import auth functionality
from auth import (
    authenticate_user, create_access_token, get_current_user,
    fake_users_db, Token, ACCESS_TOKEN_EXPIRE_MINUTES
)

# Simple database setup
engine = create_engine("sqlite:///./budget.db", future=True, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database models
class Config(Base):
    __tablename__ = "config"
    id = Column(Integer, primary_key=True, index=True)
    salaire1 = Column(Float, default=2500.0)
    salaire2 = Column(Float, default=2200.0)
    charges_fixes = Column(Float, default=1200.0)
    created_at = Column(DateTime, server_default=func.now())

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    month = Column(String, index=True)
    date_op = Column(Date)
    amount = Column(Float)
    label = Column(String)
    category = Column(String)
    is_expense = Column(Boolean)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# FastAPI app
app = FastAPI(
    title="Budget Famille Test Server",
    version="2.3.0-test",
    description="Simple test server for E2E validation"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
@app.get("/")
def read_root():
    return {
        "message": "Budget Famille Test Server",
        "version": "2.3.0-test",
        "status": "running"
    }

@app.get("/health")
def health_check():
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        return {
            "status": "healthy",
            "version": "2.3.0-test",
            "database": "connected",
            "timestamp": dt.datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": dt.datetime.now().isoformat()
        }

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Simple token endpoint"""
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/v1/auth/validate")
def validate_token(current_user = Depends(get_current_user)):
    """Validate JWT token"""
    return {
        "valid": True,
        "user": current_user,
        "message": "Token is valid"
    }

@app.get("/config")
def get_config(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get configuration"""
    config = db.query(Config).first()
    if not config:
        # Create default config
        config = Config()
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return {
        "id": config.id,
        "salaire1": config.salaire1,
        "salaire2": config.salaire2,
        "charges_fixes": config.charges_fixes
    }

@app.post("/config")
def update_config(config_data: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update configuration"""
    config = db.query(Config).first()
    if not config:
        config = Config()
        db.add(config)
    
    for key, value in config_data.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    db.commit()
    db.refresh(config)
    return {"message": "Config updated", "config": config_data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)