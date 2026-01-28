"""
Budget Famille v2.3 - Modular FastAPI Application
Refactored from monolithic architecture to support Phase 2 Intelligence roadmap
"""

import io
import csv
import re
import hashlib
import datetime as dt
import logging
import os
from typing import List, Optional, Dict, Union
from sqlalchemy.orm import Session
import uuid
from html import escape
import tempfile

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import conditionnel de magic avec gestion d'environnement optimisée pour Ubuntu WSL
MAGIC_AVAILABLE = False
try:
    import magic
    MAGIC_AVAILABLE = True
    logger.info("✅ python-magic disponible (Ubuntu/WSL)")
except ImportError:
    try:
        import magic_fallback as magic
        MAGIC_AVAILABLE = True
        logger.info("⚠️  Utilisation magic_fallback (python-magic non disponible)")
    except ImportError:
        MAGIC_AVAILABLE = False
        logger.warning("❌ Détection MIME désactivée - uploads CSV uniquement")

import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, validator, Field
from email_validator import validate_email, EmailNotValidError
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from sqlalchemy.sql import func
from dotenv import load_dotenv
from datetime import timedelta

# Import modules
from auth import (
    authenticate_user, create_access_token, get_current_user,
    fake_users_db, Token, ACCESS_TOKEN_EXPIRE_MINUTES, debug_jwt_validation
)
from database_encrypted import (
    get_encrypted_engine, migrate_to_encrypted_db, 
    verify_encrypted_db, rollback_migration
)
from audit_logger import get_audit_logger, AuditEventType
from export_engine import (
    ExportManager, ExportRequest, ExportFilters, ExportFormat, 
    ExportScope, ExportJob
)

# Chargement des variables d'environnement
load_dotenv()

# Database configuration
def setup_database():
    """Configure database engine according to environment"""
    use_encryption = os.getenv("ENABLE_DB_ENCRYPTION", "false").lower() == "true"
    
    if use_encryption:
        try:
            from database_encrypted import get_encrypted_engine, verify_encrypted_db, migrate_to_encrypted_db
            
            if not verify_encrypted_db():
                logger.info("Migration vers base chiffrée requise")
                if migrate_to_encrypted_db():
                    logger.info("✅ Migration vers base chiffrée réussie")
                else:
                    logger.warning("❌ Migration échouée - utilisation base standard")
                    return create_engine("sqlite:///./budget.db", future=True, echo=False)
            
            engine = get_encrypted_engine()
            logger.info("🔐 Utilisation base chiffrée SQLCipher")
            return engine
            
        except ImportError:
            logger.warning("⚠️  Module de chiffrement non disponible - utilisation base standard")
        except Exception as e:
            logger.error(f"Erreur chiffrement DB: {e} - utilisation base standard")
    
    # Standard SQLite configuration
    engine = create_engine(
        "sqlite:///./budget.db", 
        future=True, 
        echo=False,
        connect_args={
            "check_same_thread": False,
            "timeout": 20
        },
        pool_pre_ping=True,
        pool_recycle=3600
    )
    logger.info("📁 Utilisation base SQLite standard")
    return engine

engine = setup_database()
USE_ENCRYPTED_DB = hasattr(engine.url, 'database') and 'pysqlcipher' in str(engine.url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# FastAPI application setup with comprehensive OpenAPI configuration
app = FastAPI(
    title="Budget Famille API",
    version="2.3.0",
    description="""
    # 💰 Budget Famille v2.3 - API Documentation Complète

    Système de gestion budgétaire familiale avec architecture modulaire et IA-ready.
    Cette API RESTful complète offre toutes les fonctionnalités pour gérer efficacement 
    les finances familiales avec des outils avancés d'analyse et de prédiction.

    ## 🚀 Fonctionnalités Principales

    ### 🔐 Authentification & Sécurité
    - **JWT Bearer Token** avec expiration configurable (défaut: 60 minutes)
    - **OAuth2 Password Flow** compatible avec les standards
    - **Rate limiting** et protection contre les attaques brute-force
    - **Audit logging** complet de toutes les actions sensibles
    - **Chiffrement base de données** SQLCipher (optionnel)

    ### 💳 Gestion des Transactions
    - **Import CSV intelligent** avec détection automatique de format
    - **CRUD complet** avec filtrage avancé par date, catégorie, montant
    - **Système de tags** flexible pour organisation personnalisée  
    - **Détection de doublons** lors des imports
    - **Exclusion sélective** pour ajustements de calculs

    ### 📊 Analytics & Intelligence
    - **KPI Dashboard** temps réel avec métriques financières
    - **Analyse de tendances** multi-périodes
    - **Détection d'anomalies** automatique basée sur l'historique
    - **Patterns de dépenses** par jour de semaine
    - **Breakdown par catégories** avec visualisations

    ### 🏠 Provisions & Charges Fixes
    - **Provisions personnalisables** avec calcul automatique
    - **Charges fixes** configurables (mensuel/trimestriel/annuel)
    - **Répartition intelligente** proportionnelle ou égalitaire
    - **Projections budgétaires** basées sur l'historique
    - **Objectifs d'épargne** avec suivi de progression

    ### 📈 Export & Reporting
    - **Multi-formats**: CSV, PDF, Excel avec templates personnalisés
    - **Filtrage avancé** par période, catégorie, montant
    - **Historique des exports** avec traçabilité
    - **Données anonymisées** pour partage sécurisé

    ### 🤖 Intelligence Artificielle (Phase 2 Ready)
    - **Architecture modulaire** préparée pour ML/IA
    - **Catégorisation automatique** des transactions
    - **Prédictions budgétaires** basées sur patterns historiques  
    - **Détection fraude** et transactions suspectes
    - **Recommandations personnalisées** d'optimisation

    ### ⚡ Performance & Scalabilité
    - **Cache Redis** intelligent pour calculs complexes
    - **Indexation SQL** optimisée pour grandes volumétries
    - **Architecture modulaire** avec séparation des responsabilités
    - **Rate limiting** et gestion des pics de charge
    - **Monitoring** et métriques détaillées

    ## 📋 Guide d'utilisation

    ### Authentification
    1. Obtenez un token via `POST /api/v1/auth/token`
    2. Incluez le token dans l'header: `Authorization: Bearer <token>`
    3. Le token expire après 60 minutes (configurable)

    ### Flux typique d'utilisation
    1. **Configuration**: `POST /config` - Paramétrez revenus et répartitions
    2. **Import**: `POST /import` - Importez vos données bancaires CSV  
    3. **Analyse**: `GET /analytics/kpis` - Consultez vos KPI financiers
    4. **Optimisation**: `POST /provisions` - Configurez vos objectifs d'épargne

    ## 🔧 Endpoints par Module

    | Module | Endpoints | Description |
    |--------|-----------|-------------|
    | **Auth** | `/api/v1/auth/*` | Gestion authentification JWT |
    | **Config** | `/config` | Configuration budgétaire |
    | **Transactions** | `/transactions` | CRUD transactions |
    | **Analytics** | `/analytics/*` | KPI et analyses |
    | **Provisions** | `/provisions` | Épargne et objectifs |
    | **Fixed Lines** | `/fixed-lines` | Charges fixes |
    | **Import/Export** | `/import`, `/export` | Gestion données |

    ## 📞 Support & Documentation

    - **Documentation interactive**: [/docs](/docs) (Swagger UI)
    - **Documentation alternative**: [/redoc](/redoc) (ReDoc)
    - **Health Check**: [/health](/health)
    - **Version**: v2.3.0 - Architecture modulaire

    ## 🚨 Codes d'erreur communs

    | Code | Description | Solution |
    |------|-------------|----------|
    | 401 | Token invalide/expiré | Reconnectez-vous |
    | 403 | Accès refusé | Vérifiez permissions |
    | 422 | Données invalides | Vérifiez format |
    | 429 | Trop de requêtes | Attendez avant retry |
    | 500 | Erreur serveur | Contactez support |
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "Gestion de l'authentification JWT et des sessions utilisateur"
        },
        {
            "name": "Configuration", 
            "description": "Configuration des paramètres budgétaires (salaires, répartitions, provisions)"
        },
        {
            "name": "Transactions",
            "description": "CRUD des transactions financières avec filtrage et gestion des tags"
        },
        {
            "name": "Analytics",
            "description": "Tableaux de bord, KPI, analyses de tendances et détection d'anomalies"
        },
        {
            "name": "Provisions", 
            "description": "Gestion des provisions personnalisées et objectifs d'épargne"
        },
        {
            "name": "Fixed Expenses",
            "description": "Gestion des charges fixes récurrentes (loyer, assurances, abonnements)"
        },
        {
            "name": "Import/Export",
            "description": "Import de fichiers CSV et export de données dans différents formats"
        },
        {
            "name": "Cache",
            "description": "Gestion du cache Redis pour optimisation des performances"
        },
        {
            "name": "Account Balance",
            "description": "Gestion des soldes de comptes mensuels et calculs de virements"
        }
    ],
    contact={
        "name": "Budget Famille Support",
        "email": "support@budget-famille.com"
    },
    license_info={
        "name": "Propriétaire", 
        "url": "https://budget-famille.local/license"
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Serveur de développement local"
        }
    ]
)

# CORS configuration - Import centralized settings
from config.settings import settings
from models.schemas import SummaryOut

# Database Models (keeping essential models here for compatibility)
class Config(Base):
    __tablename__ = "config"
    id = Column(Integer, primary_key=True, index=True)
    salaire1 = Column(Float, default=2500.0)  
    salaire2 = Column(Float, default=2200.0)  
    charges_fixes = Column(Float, default=1200.0)  
    provision_vacances = Column(Float, default=200.0)  
    provision_voiture = Column(Float, default=150.0)  
    provision_travaux = Column(Float, default=100.0)
    r1 = Column(Float, default=60.0)  
    r2 = Column(Float, default=40.0)  
    s1 = Column(Float, default=1.2)  
    s2 = Column(Float, default=0.8)   
    mode = Column(String, default="proportionnel")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    month = Column(String, index=True)  
    date_op = Column(Date)  
    date_valeur = Column(Date)  
    amount = Column(Float)  
    label = Column(String)  
    category = Column(String)  
    subcategory = Column(String)  
    is_expense = Column(Boolean)  
    exclude = Column(Boolean, default=False)
    tags = Column(String)

class FixedLine(Base):
    __tablename__ = "fixed_lines"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String)
    amount = Column(Float)
    freq = Column(String)  # "mensuelle", "trimestrielle", "annuelle"
    split_mode = Column(String, default="proportionnel")  # "égalitaire", "proportionnel", "custom"
    split1 = Column(Float, default=50.0)
    split2 = Column(Float, default=50.0)
    category = Column(String, default="autres")
    active = Column(Boolean, default=True)

class ImportMetadata(Base):
    __tablename__ = "import_metadata"
    id = Column(Integer, primary_key=True, index=True)
    import_id = Column(String, unique=True, index=True)
    filename = Column(String)
    file_size = Column(Integer)
    import_date = Column(DateTime)
    user_id = Column(String)
    status = Column(String)
    months_detected = Column(Integer)
    rows_imported = Column(Integer)

class ExportHistory(Base):
    __tablename__ = "export_history"
    id = Column(Integer, primary_key=True, index=True)
    export_id = Column(String, unique=True, index=True)
    user_id = Column(String)
    export_type = Column(String)
    filters_applied = Column(Text)
    file_path = Column(String)
    created_at = Column(DateTime)

class CustomProvision(Base):
    __tablename__ = "custom_provisions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    percentage = Column(Float)
    base_calculation = Column(String, default="net_income")
    fixed_amount = Column(Float)
    split_mode = Column(String, default="proportionnel")
    split_member1 = Column(Float, default=50.0)
    split_member2 = Column(Float, default=50.0)
    icon = Column(String, default="💰")
    color = Column(String, default="#3B82F6")
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_temporary = Column(Boolean, default=False)
    start_date = Column(Date)
    end_date = Column(Date)
    target_amount = Column(Float)
    current_amount = Column(Float, default=0.0)
    category = Column(String, default="épargne")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String)

# Create tables
Base.metadata.create_all(bind=engine)

# Import routers
from routers.auth import router as auth_router
# from routers.cache import router as cache_router
from routers.config import router as config_router
from routers.fixed_expenses import router as fixed_expenses_router
from routers.provisions import router as provisions_router
from routers.transactions import router as transactions_router
from routers.import_export import router as import_export_router
from routers.analytics import router as analytics_router
from routers.tag_automation import router as tag_automation_router
from routers.tags import router as tags_router
from routers.classification import router as classification_router
from routers.intelligent_tags import router as intelligent_tags_router  # New intelligent tag system
from routers.auto_tagging import router as auto_tagging_router  # Batch auto-tagging system
# from routers.intelligence import router as intelligence_router  # Temporarily disabled due to syntax error
from routers.research import router as research_router
from routers.ml_tagging import router as ml_tagging_router  # ML-based tagging with confidence scoring
from routers.ml_feedback import router as ml_feedback_router  # ML feedback learning system
from routers.ml_enhanced_classification import router as ml_enhanced_classification_router  # Enhanced ML classification
from routers.balance import router as balance_router  # Account balance management
from routers.tag_categories import router as tag_categories_router  # Tag-category mappings persistence
from routers.custom_categories import router as custom_categories_router  # User-defined custom categories
from routers.budgets import router as budgets_router  # Category budget management for variance analysis
from routers.ai import router as ai_router  # AI-powered budget analysis with OpenRouter
from routers.predictions import router as predictions_router  # ML predictions and anomaly detection
from routers.smart_import import router as smart_import_router  # Smart multi-format file import (CSV, XLSX, PDF)

# Include routers with their prefixes
app.include_router(auth_router, tags=["authentication"])
# app.include_router(cache_router, tags=["cache"])
app.include_router(config_router, tags=["configuration"])
app.include_router(fixed_expenses_router, tags=["fixed-expenses"])
app.include_router(provisions_router, tags=["provisions"])
app.include_router(transactions_router, tags=["transactions"])
app.include_router(import_export_router, tags=["import-export"])
app.include_router(analytics_router, tags=["analytics"])
app.include_router(tag_automation_router, tags=["tag-automation"])
app.include_router(tags_router, tags=["tags"])
app.include_router(classification_router, prefix="/expense-classification", tags=["intelligent-classification"])
app.include_router(intelligent_tags_router, tags=["intelligent-tags"])  # New intelligent tag system
app.include_router(auto_tagging_router, tags=["auto-tagging"])  # Batch auto-tagging system
# app.include_router(intelligence_router, tags=["intelligence"])  # Temporarily disabled
app.include_router(research_router, tags=["web-research"])
app.include_router(ml_tagging_router, tags=["ml-tagging"])  # ML-based tagging with confidence scoring
app.include_router(ml_feedback_router, tags=["ml-feedback"])  # ML feedback learning system
app.include_router(ml_enhanced_classification_router, tags=["ml-enhanced-classification"])  # Enhanced ML classification
app.include_router(balance_router, tags=["account-balance"])  # Account balance management
app.include_router(tag_categories_router, tags=["tag-categories"])  # Tag-category mappings persistence
app.include_router(custom_categories_router, tags=["custom-categories"])  # User-defined custom categories
app.include_router(budgets_router, tags=["category-budgets"])  # Category budget management for variance analysis
app.include_router(ai_router, tags=["ai-analysis"])  # AI-powered budget analysis with OpenRouter
app.include_router(predictions_router, tags=["ml-predictions"])  # ML budget predictions and anomaly detection
app.include_router(smart_import_router, tags=["smart-import"])  # Smart multi-format file import

# Configure CORS middleware after all routes are defined
# This ensures CORS preflight requests are handled correctly for all endpoints
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allowed_origins,
    allow_credentials=settings.cors.allow_credentials,
    allow_methods=settings.cors.allow_methods,
    allow_headers=settings.cors.allow_headers,
    max_age=settings.cors.max_age,
    expose_headers=["Content-Type", "Authorization", "X-Total-Count", "X-Pagination", "*"],  # Expose all headers for debugging
)

# Add compatibility routes for existing endpoints that don't have prefixes
@app.post("/token", response_model=Token)
async def legacy_token_endpoint(form_data: OAuth2PasswordRequestForm = Depends()):
    """Legacy token endpoint for backward compatibility"""
    # Direct authentication logic matching the original
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

@app.get("/keep-alive")
async def keep_alive(current_user = Depends(get_current_user)):
    """Endpoint pour maintenir la session active et vérifier la validité du token"""
    return {
        "status": "ok", 
        "user": current_user.username, 
        "timestamp": dt.datetime.utcnow().isoformat(),
        "message": "Session active"
    }

@app.post("/debug/jwt")
def legacy_debug_jwt(request_data: dict):
    """Legacy debug JWT endpoint for backward compatibility"""
    try:
        token = request_data.get("token")
        if not token:
            raise HTTPException(status_code=400, detail="Token requis")
        
        debug_result = debug_jwt_validation(token)
        return {
            "debug_info": debug_result,
            "timestamp": dt.datetime.now().isoformat(),
            "endpoint": "/debug/jwt"
        }
    except Exception as e:
        logger.error(f"JWT debug error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug JWT failed: {str(e)}"
        )

# Compatibility routes for custom-provisions (frontend expects this endpoint)

@app.get("/custom-provisions")
async def legacy_list_custom_provisions(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Legacy custom-provisions endpoint for frontend compatibility"""
    # Delegate to the provisions router implementation
    from routers.provisions import list_provisions
    return list_provisions(current_user=current_user, db=db)

@app.post("/custom-provisions")
async def legacy_create_custom_provision(payload: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Legacy custom-provisions POST endpoint for frontend compatibility"""
    # Delegate to the provisions router implementation
    from routers.provisions import create_provision
    from models.schemas import CustomProvisionCreate
    
    # Convert dict payload to Pydantic model for validation
    try:
        provision_data = CustomProvisionCreate(**payload)
        return create_provision(payload=provision_data, current_user=current_user, db=db)
    except Exception as e:
        logger.error(f"Error creating custom provision: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provision data: {str(e)}"
        )

@app.put("/custom-provisions/{provision_id}")
async def legacy_update_custom_provision(provision_id: int, payload: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Legacy custom-provisions PUT endpoint for frontend compatibility"""
    # Delegate to the provisions router implementation
    from routers.provisions import update_provision
    from models.schemas import CustomProvisionUpdate
    
    # Convert dict payload to Pydantic model for validation
    try:
        provision_data = CustomProvisionUpdate(**payload)
        return update_provision(provision_id=provision_id, payload=provision_data, current_user=current_user, db=db)
    except Exception as e:
        logger.error(f"Error updating custom provision {provision_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provision data: {str(e)}"
        )

@app.delete("/custom-provisions/{provision_id}", status_code=status.HTTP_204_NO_CONTENT)
async def legacy_delete_custom_provision(provision_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Legacy custom-provisions DELETE endpoint for frontend compatibility"""
    # Delegate to the provisions router implementation  
    from routers.provisions import delete_provision
    
    try:
        return delete_provision(provision_id=provision_id, current_user=current_user, db=db)
    except Exception as e:
        logger.error(f"Error deleting custom provision {provision_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete provision: {str(e)}"
        )

# Compatibility route for tags-summary (frontend expects this endpoint)
@app.get("/tags-summary")
def legacy_tags_summary(month: str, db: Session = Depends(get_db)):
    """Legacy tags-summary endpoint for frontend compatibility"""
    # Delegate to the transactions router implementation
    try:
        from routers.transactions import tags_summary
        return tags_summary(month=month, db=db)
    except Exception as e:
        logger.error(f"Error in legacy_tags_summary: {str(e)}")
        # Return a safe fallback response
        return {
            "month": month,
            "tags": {},
            "total_tagged_transactions": 0
        }

# Compatibility routes for unified classification endpoints (frontend expects /unified/* paths)
@app.post("/unified/classify")
async def legacy_unified_classify(payload: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Legacy unified classify endpoint for frontend compatibility"""
    try:
        from routers.classification import unified_classify
        from models.schemas import UnifiedClassificationRequest
        
        # Convert dict payload to Pydantic model
        request_data = UnifiedClassificationRequest(**payload)
        return await unified_classify(request=request_data, current_user=current_user, db=db)
    except Exception as e:
        logger.error(f"Error in legacy_unified_classify: {str(e)}")
        # Return fallback classification
        return {
            "classification_results": {
                "category": "autres",
                "expense_type": "VARIABLE",
                "confidence": 0.0,
                "suggested_tags": []
            },
            "request": payload,
            "timestamp": dt.datetime.now().isoformat(),
            "fallback": True
        }

@app.post("/unified/batch-classify") 
async def legacy_unified_batch_classify(payload: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Legacy unified batch classify endpoint for frontend compatibility"""
    try:
        from routers.classification import unified_batch_classify
        from models.schemas import BatchUnifiedClassificationRequest
        
        # Convert dict payload to Pydantic model
        request_data = BatchUnifiedClassificationRequest(**payload)
        return await unified_batch_classify(request=request_data, current_user=current_user, db=db)
    except Exception as e:
        logger.error(f"Error in legacy_unified_batch_classify: {str(e)}")
        # Return fallback batch classification
        return {
            "results": [],
            "stats": {
                "total_transactions": 0,
                "successfully_classified": 0,
                "classification_rate": 0.0
            },
            "timestamp": dt.datetime.now().isoformat(),
            "fallback": True
        }

@app.get("/unified/stats")
async def legacy_unified_stats(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Legacy unified stats endpoint for frontend compatibility"""
    try:
        from routers.classification import get_unified_classification_stats
        return await get_unified_classification_stats(current_user=current_user, db=db)
    except Exception as e:
        logger.error(f"Error in legacy_unified_stats: {str(e)}")
        # Return fallback stats
        return {
            "total_classifications": 0,
            "success_rate": 0.0,
            "average_confidence": 0.0,
            "category_distribution": {},
            "expense_type_distribution": {"VARIABLE": 100, "FIXED": 0},
            "timestamp": dt.datetime.now().isoformat(),
            "fallback": True
        }

# Compatibility routes for tag suggestion endpoints
@app.get("/tags/suggest/{tag_name}")
async def legacy_tag_suggest_simple(tag_name: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Legacy tag suggest endpoint for frontend compatibility"""
    try:
        from routers.classification import suggest_classification_simple
        return suggest_classification_simple(tag_name=tag_name, current_user=current_user, db=db)
    except Exception as e:
        logger.error(f"Error in legacy_tag_suggest_simple: {str(e)}")
        # Return fallback suggestion
        return {
            "tag_name": tag_name,
            "suggested_type": "VARIABLE",
            "confidence": 0.0,
            "explanation": "Fallback suggestion - system unavailable",
            "timestamp": dt.datetime.now().isoformat(),
            "fallback": True
        }

@app.post("/tags/suggest")
async def legacy_tag_suggest(payload: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Legacy tag suggest POST endpoint for frontend compatibility"""
    try:
        from routers.classification import suggest_classification
        from models.schemas import ClassificationRequest
        
        # Convert dict payload to Pydantic model
        request_data = ClassificationRequest(**payload)
        return suggest_classification(request=request_data, current_user=current_user, db=db)
    except Exception as e:
        logger.error(f"Error in legacy_tag_suggest: {str(e)}")
        # Return fallback suggestion
        return {
            "tag_name": payload.get("tag_name", "unknown"),
            "suggested_type": "VARIABLE",
            "confidence": 0.0,
            "explanation": "Fallback suggestion - system unavailable",
            "timestamp": dt.datetime.now().isoformat(),
            "fallback": True
        }

@app.options("/tags/suggest/{tag_name}")
@app.options("/tags/suggest")
@app.options("/unified/classify")
@app.options("/unified/batch-classify")
@app.options("/unified/stats")
async def cors_preflight():
    """Handle CORS preflight requests for all endpoints that need OPTIONS support"""
    from fastapi.responses import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
            "Access-Control-Max-Age": "600"
        }
    )

# The /summary endpoint is implemented later in the file for compatibility

# Health check endpoint
@app.get("/health")
def health_check():
    """
    Health check endpoint
    
    Returns the overall system status including database connectivity.
    """
    try:
        # Test database connectivity
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        
        return {
            "status": "healthy",
            "version": "2.3.0",
            "database": "connected",
            "encryption": "enabled" if USE_ENCRYPTED_DB else "disabled",
            "timestamp": dt.datetime.now().isoformat(),
            "architecture": "modular"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "version": "2.3.0", 
            "database": "disconnected",
            "error": str(e),
            "timestamp": dt.datetime.now().isoformat()
        }

# Summary endpoint - Frontend Dashboard compatible
@app.get("/summary", response_model=SummaryOut)  
def get_summary(month: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Legacy summary endpoint - returns Summary data for frontend dashboard compatibility
    
    This endpoint returns the structure expected by the frontend Dashboard component.
    """
    from models.database import Config, Transaction, FixedLine, CustomProvision, ensure_default_config
    from services.calculations import get_split, split_amount, calculate_provision_amount
    from models.schemas import SummaryOut
    
    try:
        logger.info(f"📊 Summary requested for month {month} by user {current_user.username}")
        
        # Get configuration
        cfg = ensure_default_config(db)
        r1, r2 = get_split(cfg)

        # Lignes fixes personnalisées
        lines = db.query(FixedLine).filter(FixedLine.active == True).all()
        lines_total = 0.0
        lines_detail = []
        for ln in lines:
            if ln.freq == "mensuelle":
                mval = ln.amount
            elif ln.freq == "trimestrielle":
                mval = (ln.amount or 0.0) / 3.0
            else:
                mval = (ln.amount or 0.0) / 12.0
            p1, p2 = split_amount(mval, ln.split_mode, r1, r2, ln.split1, ln.split2)
            lines_total += mval
            lines_detail.append((ln.label or "Fixe", p1, p2))

        # Provisions personnalisables
        custom_provisions = db.query(CustomProvision).filter(
            CustomProvision.created_by == current_user.username,
            CustomProvision.is_active == True
        ).order_by(CustomProvision.display_order, CustomProvision.name).all()
        
        custom_provisions_total = 0.0
        custom_provisions_detail = []
        custom_provisions_p1_total = 0.0
        custom_provisions_p2_total = 0.0
        
        for provision in custom_provisions:
            monthly_amount, member1_amount, member2_amount = calculate_provision_amount(provision, cfg)
            custom_provisions_total += monthly_amount
            custom_provisions_p1_total += member1_amount
            custom_provisions_p2_total += member2_amount
            custom_provisions_detail.append((provision.name, member1_amount, member2_amount, provision.icon))

        # Variables (transactions du mois)
        # Filtrer: montant négatif (dépenses) ET non exclu (prêt auto, immobilier, etc.)
        txs = db.query(Transaction).filter(Transaction.month == month).all()
        var_total = -sum(t.amount for t in txs if (t.amount is not None and t.amount < 0 and not t.exclude))
        var_p1 = var_total * r1
        var_p2 = var_total * r2

        # Totaux
        total_p1 = var_p1 + sum(p1 for _,p1,_ in lines_detail) + custom_provisions_p1_total
        total_p2 = var_p2 + sum(p2 for _,_,p2 in lines_detail) + custom_provisions_p2_total

        # Détail pour l'interface
        detail = {}
        for label, p1, p2 in lines_detail:
            detail[f"Fixe — {label}"] = {cfg.member1: p1, cfg.member2: p2}
        
        if custom_provisions_detail:
            for prov_name, prov_p1, prov_p2, prov_icon in custom_provisions_detail:
                detail[f"Provision — {prov_icon} {prov_name}"] = {cfg.member1: prov_p1, cfg.member2: prov_p2}
        
        detail["Dépenses variables"] = {cfg.member1: var_p1, cfg.member2: var_p2}

        # Parts par type
        fixed_p1 = sum(p1 for _, p1, _ in lines_detail)
        fixed_p2 = sum(p2 for _, _, p2 in lines_detail)
        
        # Comptages
        transaction_count = len(txs)
        active_fixed_lines = len([l for l in lines if l.active])
        active_provisions_count = len(custom_provisions)
        
        logger.info(f"✅ Summary calculated: var_total={var_total}, provisions_total={custom_provisions_total}, fixed_total={lines_total}")
        
        return SummaryOut(
            month=month, 
            var_total=round(var_total, 2),
            fixed_lines_total=round(lines_total, 2),
            provisions_total=round(custom_provisions_total, 2),
            r1=round(r1, 4), 
            r2=round(r2, 4),
            member1=cfg.member1, 
            member2=cfg.member2,
            total_p1=round(total_p1, 2), 
            total_p2=round(total_p2, 2), 
            detail=detail,
            
            # Champs optimisation frontend
            var_p1=round(var_p1, 2),
            var_p2=round(var_p2, 2),
            fixed_p1=round(fixed_p1, 2),
            fixed_p2=round(fixed_p2, 2),
            provisions_p1=round(custom_provisions_p1_total, 2),
            provisions_p2=round(custom_provisions_p2_total, 2),
            grand_total=round(total_p1 + total_p2, 2),
            
            # Métadonnées
            transaction_count=transaction_count,
            active_fixed_lines=active_fixed_lines,
            active_provisions=active_provisions_count,
            
            # Totals object for unified structure
            totals={
                "total_expenses": round(-var_total, 2),
                "total_fixed": round(lines_total, 2),
                "total_variable": round(-var_total, 2)
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error in summary endpoint: {str(e)}")
        # Return fallback with safe default values
        cfg = ensure_default_config(db)
        return SummaryOut(
            month=month, 
            var_total=0.0,
            fixed_lines_total=0.0,
            provisions_total=0.0,
            r1=0.5, 
            r2=0.5,
            member1=cfg.member1 if cfg else "Membre1", 
            member2=cfg.member2 if cfg else "Membre2",
            total_p1=0.0, 
            total_p2=0.0, 
            detail={},
            var_p1=0.0,
            var_p2=0.0,
            fixed_p1=0.0,
            fixed_p2=0.0,
            provisions_p1=0.0,
            provisions_p2=0.0,
            grand_total=0.0,
            transaction_count=0,
            active_fixed_lines=0,
            active_provisions=0,
            totals={
                "total_expenses": 0.0,
                "total_fixed": 0.0,
                "total_variable": 0.0
            }
        )

@app.get("/summary/enhanced")
def get_enhanced_summary(month: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Enhanced summary with detailed variables breakdown by tags
    
    This endpoint provides:
    - Provisions (savings) separated from expenses
    - Variables detailed by tags with individual amounts
    - Untagged transactions total
    - Clear separation between savings and expenses
    """
    from models.database import Config, Transaction, FixedLine, CustomProvision, ensure_default_config
    from services.calculations import get_split, split_amount, calculate_provision_amount
    from collections import defaultdict
    
    try:
        logger.info(f"📊 Enhanced Summary requested for month {month} by user {current_user.username}")
        
        # Get configuration
        cfg = ensure_default_config(db)
        r1, r2 = get_split(cfg)
        
        # === PROVISIONS (ÉPARGNE) ===
        custom_provisions = db.query(CustomProvision).filter(
            CustomProvision.created_by == current_user.username,
            CustomProvision.is_active == True
        ).order_by(CustomProvision.display_order, CustomProvision.name).all()
        
        provisions_total = 0.0
        provisions_detail = []
        provisions_p1_total = 0.0
        provisions_p2_total = 0.0
        
        for provision in custom_provisions:
            monthly_amount, member1_amount, member2_amount = calculate_provision_amount(provision, cfg)
            provisions_total += monthly_amount
            provisions_p1_total += member1_amount
            provisions_p2_total += member2_amount
            provisions_detail.append({
                "name": provision.name,
                "icon": provision.icon,
                "color": provision.color,
                "monthly_amount": round(monthly_amount, 2),
                "member1_amount": round(member1_amount, 2),
                "member2_amount": round(member2_amount, 2),
                "type": "provision"
            })
        
        # === CHARGES FIXES ===
        # Inclut DEUX sources :
        # 1. Charges manuelles (fixed_lines)
        # 2. Transactions automatiquement classées FIXED par l'IA
        
        fixed_total = 0.0
        fixed_detail = []
        fixed_p1_total = 0.0
        fixed_p2_total = 0.0
        
        # 1. Charges fixes manuelles
        lines = db.query(FixedLine).filter(FixedLine.active == True).all()
        for ln in lines:
            if ln.freq == "mensuelle":
                mval = ln.amount
            elif ln.freq == "trimestrielle":
                mval = (ln.amount or 0.0) / 3.0
            else:
                mval = (ln.amount or 0.0) / 12.0
            
            p1, p2 = split_amount(mval, ln.split_mode, r1, r2, ln.split1, ln.split2)
            fixed_total += mval
            fixed_p1_total += p1
            fixed_p2_total += p2
            fixed_detail.append({
                "name": ln.label or "Fixe",
                "monthly_amount": round(mval, 2),
                "member1_amount": round(p1, 2),
                "member2_amount": round(p2, 2),
                "category": ln.category,
                "type": "fixed",
                "source": "manual",
                "icon": "⚙️"  # Icône pour charges manuelles
            })
        
        # 2. Transactions automatiquement classées FIXED par l'IA
        # Utilise amount < 0 au lieu de is_expense pour plus de robustesse
        fixed_txs = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.amount < 0,  # Dépenses = montants négatifs
            Transaction.exclude == False,
            Transaction.expense_type == 'FIXED'
        ).all()
        
        # Grouper par tags pour les transactions FIXED
        fixed_tag_amounts = defaultdict(float)
        fixed_untagged_amount = 0.0
        
        for tx in fixed_txs:
            amount = abs(tx.amount or 0)
            
            if tx.tags and tx.tags.strip():
                tags = [t.strip() for t in tx.tags.split(',') if t.strip()]
                if tags:
                    amount_per_tag = amount / len(tags)
                    for tag in tags:
                        fixed_tag_amounts[tag] += amount_per_tag
                else:
                    fixed_untagged_amount += amount
            else:
                fixed_untagged_amount += amount
        
        # Ajouter les charges fixes untagged
        if fixed_untagged_amount > 0:
            untagged_p1 = fixed_untagged_amount * r1
            untagged_p2 = fixed_untagged_amount * r2
            fixed_total += fixed_untagged_amount
            fixed_p1_total += untagged_p1
            fixed_p2_total += untagged_p2
            fixed_detail.append({
                "name": "Charges fixes non-taggées",
                "monthly_amount": round(fixed_untagged_amount, 2),
                "member1_amount": round(untagged_p1, 2),
                "member2_amount": round(untagged_p2, 2),
                "category": "auto",
                "type": "fixed",
                "source": "ai_classified",
                "icon": "🤖"  # Icône pour IA
            })
        
        # Ajouter les charges fixes par tags (triées par montant décroissant)
        for tag, amount in sorted(fixed_tag_amounts.items(), key=lambda x: x[1], reverse=True):
            tag_p1 = amount * r1
            tag_p2 = amount * r2
            fixed_total += amount
            fixed_p1_total += tag_p1
            fixed_p2_total += tag_p2
            
            fixed_detail.append({
                "name": f"{tag}",
                "monthly_amount": round(amount, 2),
                "member1_amount": round(tag_p1, 2),
                "member2_amount": round(tag_p2, 2),
                "category": "auto",
                "type": "fixed",
                "source": "ai_classified",
                "icon": "🤖",  # Icône pour IA
                "tag": tag
            })
        
        # === VARIABLES (DÉPENSES) - FILTRAGE STRICT PAR TYPE ===
        # NOTE: Séparation stricte implémentée pour éviter le double comptage
        # - Les charges fixes viennent de fixed_lines ET des transactions FIXED
        # - Les variables viennent UNIQUEMENT des transactions avec expense_type='VARIABLE'  
        # - Plus de double affichage possible entre Fixed et Variable
        
        # Utilise amount < 0 au lieu de is_expense pour plus de robustesse
        txs = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.amount < 0,  # Dépenses = montants négatifs
            Transaction.exclude == False,
            Transaction.expense_type == 'VARIABLE'  # Filtrage strict pour éviter duplication
        ).all()
        
        # Group by tags
        tag_amounts = defaultdict(float)
        untagged_amount = 0.0
        tagged_transactions = 0
        untagged_transactions = 0
        
        for tx in txs:
            amount = abs(tx.amount or 0)
            
            if tx.tags and tx.tags.strip():
                # Transaction avec tags
                tags = [t.strip() for t in tx.tags.split(',') if t.strip()]
                if tags:
                    # Répartir le montant entre tous les tags
                    amount_per_tag = amount / len(tags)
                    for tag in tags:
                        tag_amounts[tag] += amount_per_tag
                    tagged_transactions += 1
                else:
                    untagged_amount += amount
                    untagged_transactions += 1
            else:
                # Transaction sans tags
                untagged_amount += amount
                untagged_transactions += 1
        
        # Préparer le détail des variables par tags
        variables_detail = []
        variables_p1_total = 0.0
        variables_p2_total = 0.0
        
        # Transactions non-taggées
        if untagged_amount > 0:
            untagged_p1 = untagged_amount * r1
            untagged_p2 = untagged_amount * r2
            variables_p1_total += untagged_p1
            variables_p2_total += untagged_p2
            variables_detail.append({
                "name": "Dépenses non-taggées",
                "tag": None,
                "amount": round(untagged_amount, 2),
                "member1_amount": round(untagged_p1, 2),
                "member2_amount": round(untagged_p2, 2),
                "transaction_count": untagged_transactions,
                "type": "untagged_variable"
            })
        
        # Transactions par tags (triées par montant décroissant)
        for tag, amount in sorted(tag_amounts.items(), key=lambda x: x[1], reverse=True):
            tag_p1 = amount * r1
            tag_p2 = amount * r2
            variables_p1_total += tag_p1
            variables_p2_total += tag_p2
            
            # Compter les transactions pour ce tag
            tag_tx_count = sum(1 for tx in txs 
                              if tx.tags and tag in [t.strip() for t in tx.tags.split(',') if t.strip()])
            
            variables_detail.append({
                "name": f"Tag: {tag}",
                "tag": tag,
                "amount": round(amount, 2),
                "member1_amount": round(tag_p1, 2),
                "member2_amount": round(tag_p2, 2),
                "transaction_count": tag_tx_count,
                "type": "tagged_variable"
            })
        
        variables_total = variables_p1_total + variables_p2_total
        
        # === REVENUS (INCOME) ===
        # Récupérer toutes les transactions de revenus (montants positifs)
        # Utilise amount > 0 comme critère principal au lieu de is_expense
        revenue_txs = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.amount > 0,  # Revenus = montants positifs
            Transaction.exclude == False
        ).all()
        
        revenue_member1_total = 0.0
        revenue_member2_total = 0.0
        
        for tx in revenue_txs:
            amount = abs(tx.amount or 0)
            member1_amount, member2_amount = split_amount(amount, "ratio", r1, r2, 0, 0)
            revenue_member1_total += member1_amount
            revenue_member2_total += member2_amount
        
        revenue_total = revenue_member1_total + revenue_member2_total
        
        # Calculer le montant recommandé à provisionner (charges fixes + épargne)
        provision_needed = fixed_total + provisions_total
        
        # === TOTAUX GÉNÉRAUX ===
        grand_total_p1 = provisions_p1_total + fixed_p1_total + variables_p1_total
        grand_total_p2 = provisions_p2_total + fixed_p2_total + variables_p2_total
        grand_total = grand_total_p1 + grand_total_p2
        
        # === RÉPONSE STRUCTURÉE ===
        response = {
            "month": month,
            "member1": cfg.member1,
            "member2": cfg.member2,
            "split_ratio": {"member1": round(r1, 4), "member2": round(r2, 4)},
            
            # REVENUS (INCOME)
            "revenues": {
                "member1_revenue": round(revenue_member1_total, 2),
                "member2_revenue": round(revenue_member2_total, 2),
                "total_revenue": round(revenue_total, 2),
                "provision_needed": round(provision_needed, 2)
            },
            
            # ÉPARGNE (PROVISIONS)
            "savings": {
                "total": round(provisions_total, 2),
                "member1_total": round(provisions_p1_total, 2),
                "member2_total": round(provisions_p2_total, 2),
                "count": len(provisions_detail),
                "detail": provisions_detail
            },
            
            # CHARGES FIXES
            "fixed_expenses": {
                "total": round(fixed_total, 2),
                "member1_total": round(fixed_p1_total, 2),
                "member2_total": round(fixed_p2_total, 2),
                "count": len(fixed_detail),
                "detail": fixed_detail
            },
            
            # DÉPENSES VARIABLES (DÉTAILLÉES PAR TAGS)
            "variables": {
                "total": round(variables_total, 2),
                "member1_total": round(variables_p1_total, 2),
                "member2_total": round(variables_p2_total, 2),
                "tagged_count": len([d for d in variables_detail if d["type"] == "tagged_variable"]),
                "untagged_count": untagged_transactions,
                "total_transactions": tagged_transactions + untagged_transactions,
                "detail": variables_detail
            },
            
            # TOTAUX GÉNÉRAUX
            "totals": {
                "total_expenses": round(fixed_total + variables_total, 2),  # Fixed: Fixed + Variables (not just variables)
                "total_fixed": round(fixed_total, 2),
                "total_variable": round(variables_total, 2),
                "grand_total": round(grand_total, 2),
                "member1_total": round(grand_total_p1, 2),
                "member2_total": round(grand_total_p2, 2)
            },
            
            # MÉTADONNÉES
            "metadata": {
                "active_provisions": len(custom_provisions),
                "active_fixed_expenses": len(lines),
                "unique_tags": len(tag_amounts),
                "calculation_timestamp": dt.datetime.now().isoformat()
            }
        }
        
        logger.info(f"✅ Enhanced Summary calculated: provisions={provisions_total:.2f}, fixed={fixed_total:.2f}, variables={variables_total:.2f}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error in enhanced summary endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enhanced summary calculation failed: {str(e)}"
        )

# Root endpoint
@app.get("/")
def read_root():
    """
    Welcome endpoint
    
    Returns basic API information and available endpoints.
    """
    return {
        "message": "Budget Famille API v2.3.0 - Modular Architecture",
        "description": "Financial management API with AI-ready modular architecture",
        "version": "2.3.0",
        "architecture": "modular",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "modules": [
            "authentication",
            "configuration", 
            "transactions",
            "fixed-expenses",
            "provisions",
            "analytics",
            "import-export",
            "cache"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)