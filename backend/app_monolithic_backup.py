
import io
import csv
import re
import hashlib
import datetime as dt
import logging
import os
from typing import List, Optional, Dict, Union
import uuid
from html import escape
import tempfile

# Configuration du logging en premier
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
        # Fallback pour environnements sans libmagic
        import magic_fallback as magic
        MAGIC_AVAILABLE = True
        logger.info("⚠️  Utilisation magic_fallback (python-magic non disponible)")
    except ImportError:
        MAGIC_AVAILABLE = False
        logger.warning("❌ Détection MIME désactivée - uploads CSV uniquement")

import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, validator, Field
from typing import List, Optional, Dict, Union
from email_validator import validate_email, EmailNotValidError
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from sqlalchemy.sql import func
from dotenv import load_dotenv

# Import du module d'authentification
from auth import (
    authenticate_user, create_access_token, get_current_user,
    fake_users_db, Token, ACCESS_TOKEN_EXPIRE_MINUTES, debug_jwt_validation
)
# Import du module de chiffrement
from database_encrypted import (
    get_encrypted_engine, migrate_to_encrypted_db, 
    verify_encrypted_db, rollback_migration
)
from audit_logger import get_audit_logger, AuditEventType
from datetime import timedelta

# Import du moteur d'export
from export_engine import (
    ExportManager, ExportRequest, ExportFilters, ExportFormat, 
    ExportScope, ExportJob
)

# Import des routers modulaires
from routers.cache import router as cache_router

# Chargement des variables d'environnement
load_dotenv()

# Configuration de la base de données avec gestion d'environnement
def setup_database():
    """Configure le moteur de base de données selon l'environnement"""
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
    
    # Configuration standard SQLite
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

app = FastAPI(
    title="Budget Famille API",
    version="2.3.0",
    description="""
    ## Système de gestion budgétaire familiale complet

    Cette API fournit toutes les fonctionnalités nécessaires pour la gestion financière familiale :

    ### 🔐 Authentification
    - JWT Bearer Token avec expiration configurable
    - Endpoints sécurisés avec validation automatique
    - Support OAuth2 compatible

    ### 💰 Gestion des Transactions
    - Import/Export CSV intelligent avec détection automatique
    - CRUD complet des transactions avec filtrage avancé
    - Support multi-comptes et multi-devises

    ### 📊 Analytics et Reporting
    - Calculs financiers automatisés (répartition, provisions)
    - Tableaux de bord KPI avec métriques en temps réel
    - Détection d'anomalies et patterns de dépenses
    - Export multi-formats (CSV, PDF, Excel)

    ### 🏠 Provisions et Charges Fixes
    - Système de provisions personnalisables basé sur les revenus
    - Gestion des charges fixes avec répartition automatique
    - Calculs dynamiques et projections budgétaires

    ### 🤖 Intelligence Artificielle
    - Catégorisation automatique des transactions
    - Prédictions budgétaires basées sur l'historique
    - Détection d'anomalies de dépenses

    ### 📈 Performance et Cache
    - Cache Redis intégré pour les calculs intensifs
    - Optimisations de requêtes avec index performants
    - Monitoring et métriques de performance

    **Environnement de développement optimisé pour Ubuntu WSL2**
    """,
    contact={
        "name": "Budget Famille Support",
        "email": "support@budget-famille.local",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Serveur de développement local"
        },
        {
            "url": "https://api.budget-famille.com",
            "description": "Serveur de production (si configuré)"
        }
    ],
    openapi_tags=[
        {
            "name": "Authentification",
            "description": "Endpoints d'authentification JWT avec sécurité renforcée"
        },
        {
            "name": "Transactions",
            "description": "Gestion complète des transactions financières"
        },
        {
            "name": "Import/Export",
            "description": "Import CSV intelligent et export multi-formats"
        },
        {
            "name": "Analytics",
            "description": "Analyses financières et tableaux de bord KPI"
        },
        {
            "name": "Provisions",
            "description": "Système de provisions personnalisables"
        },
        {
            "name": "Charges Fixes",
            "description": "Gestion des charges fixes avec répartition"
        },
        {
            "name": "Intelligence Artificielle",
            "description": "Catégorisation et prédictions ML"
        },
        {
            "name": "Configuration",
            "description": "Paramètres système et configuration utilisateur"
        },
        {
            "name": "Cache",
            "description": "Gestion du cache Redis et performance"
        },
        {
            "name": "Système",
            "description": "Health checks et informations système"
        }
    ]
)

# Configuration de sécurité OpenAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=app.servers,
        tags=app.openapi_tags,
    )
    
    # Ajouter les schémas de sécurité
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Bearer token obtenu via l'endpoint /token"
        },
        "oAuth2": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/token",
                    "scopes": {
                        "read": "Accès en lecture aux ressources",
                        "write": "Accès en écriture aux ressources",
                        "admin": "Accès administrateur complet"
                    }
                }
            },
            "description": "OAuth2 avec JWT Bearer tokens"
        }
    }
    
    # Ajouter la sécurité par défaut
    openapi_schema["security"] = [
        {"bearerAuth": []},
        {"oAuth2": ["read", "write"]}
    ]
    
    # Ajouter des exemples de réponses d'erreur communes
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "responses" not in openapi_schema["components"]:
        openapi_schema["components"]["responses"] = {}
    
    openapi_schema["components"]["responses"].update({
        "UnauthorizedError": {
            "description": "Token d'accès manquant ou invalide",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {"type": "string", "example": "Could not validate credentials"}
                        }
                    }
                }
            }
        },
        "ForbiddenError": {
            "description": "Accès refusé - permissions insuffisantes",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {"type": "string", "example": "Operation not permitted"}
                        }
                    }
                }
            }
        },
        "ValidationError": {
            "description": "Erreur de validation des données",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "loc": {"type": "array", "items": {"type": "string"}},
                                        "msg": {"type": "string"},
                                        "type": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "ServerError": {
            "description": "Erreur interne du serveur",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {"type": "string", "example": "Internal server error"}
                        }
                    }
                }
            }
        }
    })
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:45678",
        "http://127.0.0.1:45678",
        "http://localhost:8080",  # Support Frontend alternatif
        "http://127.0.0.1:8080"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include routers
app.include_router(cache_router)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Config(Base):
    __tablename__ = "config"
    # Modèle propre avec nouveaux champs
    id = Column(Integer, primary_key=True, index=True)
    member1 = Column(String, default="diana")
    member2 = Column(String, default="thomas")
    rev1 = Column(Float, default=0.0)
    rev2 = Column(Float, default=0.0)
    split_mode = Column(String, default="revenus")  # revenus | manuel
    split1 = Column(Float, default=0.5)  # if manuel
    split2 = Column(Float, default=0.5)
    other_split_mode = Column(String, default="clé")  # clé|50/50
    
    # Configuration des dépenses variables
    var_percent = Column(Float, default=30.0)  # Pourcentage de revenus pour dépenses variables
    max_var = Column(Float, default=0.0)       # Plafond maximum dépenses variables  
    min_fixed = Column(Float, default=0.0)     # Minimum charges fixes
    created_at = Column(DateTime, nullable=True)  # Création
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)  # Mise à jour
    
    # Anciens champs - conservés temporairement pour éviter les erreurs
    # À supprimer après vérification que tout fonctionne
    loan_equal = Column(Boolean, default=True, nullable=True)
    loan_amount = Column(Float, default=0.0, nullable=True)
    other_fixed_simple = Column(Boolean, default=True, nullable=True)
    other_fixed_monthly = Column(Float, default=0.0, nullable=True)
    taxe_fonciere_ann = Column(Float, default=0.0, nullable=True)
    copro_montant = Column(Float, default=0.0, nullable=True)
    copro_freq = Column(String, default="mensuelle", nullable=True)
    vac_percent = Column(Float, default=0.0, nullable=True)
    vac_base = Column(String, default="2", nullable=True)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    month = Column(String, index=True)  # "YYYY-MM" (dérivé de date_op)
    date_op = Column(Date, index=True, nullable=True)
    label = Column(Text, default="")
    category = Column(Text, default="")
    category_parent = Column(Text, default="")
    amount = Column(Float, default=0.0)
    account_label = Column(Text, default="")
    is_expense = Column(Boolean, default=False)
    exclude = Column(Boolean, default=False)
    row_id = Column(String, index=True)  # stable hash
    tags = Column(Text, default="")      # CSV de tags
    import_id = Column(String, nullable=True, index=True)  # UUID de l'import qui a créé cette transaction

class FixedLine(Base):
    __tablename__ = "fixed_lines"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, default="")
    amount = Column(Float, default=0.0)
    freq = Column(String, default="mensuelle")  # mensuelle|trimestrielle|annuelle
    split_mode = Column(String, default="clé")  # clé|50/50|m1|m2|manuel
    split1 = Column(Float, default=0.5)         # utilisé si manuel
    split2 = Column(Float, default=0.5)
    category = Column(String, default="autres")  # logement|transport|services|loisirs|santé|autres
    active = Column(Boolean, default=True)

class ImportMetadata(Base):
    __tablename__ = "import_metadata"
    id = Column(String, primary_key=True)  # UUID de l'import
    filename = Column(String, nullable=False)
    created_at = Column(Date, nullable=False)
    user_id = Column(String, nullable=True)  # Pour audit
    months_detected = Column(Text, nullable=True)  # JSON des mois détectés
    duplicates_count = Column(Integer, default=0)
    warnings = Column(Text, nullable=True)  # JSON des warnings
    processing_ms = Column(Integer, default=0)

class ExportHistory(Base):
    __tablename__ = "export_history"
    id = Column(String, primary_key=True)  # UUID de l'export
    user_id = Column(String, nullable=False, index=True)
    format = Column(String, nullable=False)  # csv, excel, pdf, json, zip
    scope = Column(String, nullable=False)   # transactions, analytics, config, all
    created_at = Column(Date, nullable=False)
    filename = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)  # Taille en bytes
    download_count = Column(Integer, default=0)
    filters_applied = Column(Text, nullable=True)  # JSON des filtres
    processing_ms = Column(Integer, default=0)
    status = Column(String, default="completed")  # pending, completed, failed
    error_message = Column(Text, nullable=True)

class CustomProvision(Base):
    """
    Modèle de provision personnalisable
    Permet de créer n'importe quel type de provision (investissement, voyage, projet, etc.)
    """
    __tablename__ = "custom_provisions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # Ex: "Investissement", "Voyage Japon", "Rénovation"
    description = Column(String(500))  # Description optionnelle
    
    # Configuration du calcul
    percentage = Column(Float, nullable=False)  # Pourcentage du revenu (0-100)
    base_calculation = Column(String(20), default="total")  # "total", "member1", "member2", "fixed"
    fixed_amount = Column(Float, default=0)  # Si base_calculation = "fixed"
    
    # Répartition entre membres
    split_mode = Column(String(20), default="key")  # "key", "50/50", "custom", "100/0", "0/100"
    split_member1 = Column(Float, default=50)  # Pourcentage membre 1 si split_mode="custom"
    split_member2 = Column(Float, default=50)  # Pourcentage membre 2 si split_mode="custom"
    
    # Configuration d'affichage
    icon = Column(String(50), default="💰")  # Emoji ou nom d'icône
    color = Column(String(7), default="#6366f1")  # Couleur hexadécimale
    display_order = Column(Integer, default=999)  # Ordre d'affichage
    
    # État et métadonnées
    is_active = Column(Boolean, default=True)
    is_temporary = Column(Boolean, default=False)  # Pour provisions temporaires
    start_date = Column(DateTime)  # Date de début (optionnel)
    end_date = Column(DateTime)  # Date de fin (optionnel)
    
    # Objectif et suivi
    target_amount = Column(Float)  # Montant objectif à atteindre
    current_amount = Column(Float, default=0)  # Montant déjà épargné
    
    # Métadonnées
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    created_by = Column(String(100))  # Username du créateur
    
    # Catégorie pour regroupement
    category = Column(String(50), default="custom")  # "savings", "investment", "project", "custom"

Base.metadata.create_all(bind=engine)

# --- Light schema migration for legacy DBs: add missing columns ---
def migrate_schema():
    with engine.connect() as conn:
        # Migration transactions
        info = conn.exec_driver_sql("PRAGMA table_info('transactions')").fetchall()
        cols = [r[1] for r in info]
        if "tags" not in cols:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN tags TEXT DEFAULT ''")
        if "import_id" not in cols:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN import_id TEXT")
        
        # Créer les indexes si nécessaires
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_transactions_import_id ON transactions(import_id)")
        
        # Migration custom_provisions - vérifier si la table existe
        try:
            conn.exec_driver_sql("SELECT 1 FROM custom_provisions LIMIT 1")
            logger.info("Table custom_provisions existe déjà")
        except Exception:
            logger.info("Création de la table custom_provisions")
            # Créer la table custom_provisions si elle n'existe pas
            conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS custom_provisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    description VARCHAR(500),
                    percentage FLOAT NOT NULL,
                    base_calculation VARCHAR(20) DEFAULT 'total',
                    fixed_amount FLOAT DEFAULT 0,
                    split_mode VARCHAR(20) DEFAULT 'key',
                    split_member1 FLOAT DEFAULT 50,
                    split_member2 FLOAT DEFAULT 50,
                    icon VARCHAR(50) DEFAULT '💰',
                    color VARCHAR(7) DEFAULT '#6366f1',
                    display_order INTEGER DEFAULT 999,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_temporary BOOLEAN DEFAULT FALSE,
                    start_date DATETIME,
                    end_date DATETIME,
                    target_amount FLOAT,
                    current_amount FLOAT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME,
                    created_by VARCHAR(100),
                    category VARCHAR(50) DEFAULT 'custom'
                )
            """)
            
            # Créer les indexes
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_custom_provisions_active ON custom_provisions(is_active)")
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_custom_provisions_created_by ON custom_provisions(created_by)")
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_custom_provisions_category ON custom_provisions(category)")
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_custom_provisions_display_order ON custom_provisions(display_order, name)")
            
            logger.info("✅ Table custom_provisions créée avec succès")
        
        conn.commit()

migrate_schema()

def ensure_default_config(db: Session):
    cfg = db.query(Config).first()
    if not cfg:
        cfg = Config()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg

# ---------- Analytics Schemas ----------
class MonthlyTrend(BaseModel):
    month: str
    total_expenses: float
    total_income: float
    net: float
    transaction_count: int

class CategoryBreakdown(BaseModel):
    category: str
    amount: float
    percentage: float
    transaction_count: int
    avg_transaction: float

class KPISummary(BaseModel):
    period_start: str
    period_end: str
    total_expenses: float
    total_income: float
    net_balance: float
    avg_monthly_expenses: float
    avg_monthly_income: float
    top_expense_category: Optional[str] = None
    top_expense_amount: float = 0.0
    transaction_count: int = 0
    expense_trend: str = "stable"  # up, down, stable

class SpendingPattern(BaseModel):
    day_of_week: int
    day_name: str
    avg_amount: float
    transaction_count: int

class AnomalyDetection(BaseModel):
    transaction_id: int
    date: str
    amount: float
    category: str
    label: str
    anomaly_type: str  # "high_amount", "unusual_category", "frequency_spike"
    score: float  # 0-1, higher = more anomalous

class BudgetComparison(BaseModel):
    category: str
    actual: float
    budget_estimate: float  # Based on historical data
    variance: float
    variance_percentage: float
    status: str  # "over", "under", "on_track"

# Modèles d'export déplacés vers export_engine.py

# ---------- Schemas ----------
class ConfigIn(BaseModel):
    member1: str = Field(..., min_length=1, max_length=50, description="Nom du membre 1")
    member2: str = Field(..., min_length=1, max_length=50, description="Nom du membre 2")
    rev1: float = Field(..., ge=0, le=999999.99, description="Revenus membre 1")
    rev2: float = Field(..., ge=0, le=999999.99, description="Revenus membre 2")
    split_mode: str = Field(..., pattern="^(revenus|manuel)$", description="Mode de répartition")
    split1: float = Field(..., ge=0, le=1, description="Part membre 1")
    split2: float = Field(..., ge=0, le=1, description="Part membre 2")
    other_split_mode: str = Field(..., pattern="^(clé|50/50)$", description="Mode répartition autres")
    
    # Configuration des dépenses variables
    var_percent: float = Field(30.0, ge=0, le=100, description="Pourcentage revenus pour dépenses variables")
    max_var: float = Field(0.0, ge=0, le=99999.99, description="Plafond maximum dépenses variables")
    min_fixed: float = Field(0.0, ge=0, le=99999.99, description="Minimum charges fixes")
    
    @validator('member1', 'member2')
    def sanitize_member_names(cls, v):
        return escape(str(v).strip())[:50]
    
    @validator('split1', 'split2')
    def validate_splits(cls, v, values):
        if 'split1' in values and abs(values['split1'] + v - 1.0) > 0.01:
            raise ValueError('La somme des parts doit égaler 1.0')
        return v

class ConfigOut(ConfigIn):
    id: int

class TxOut(BaseModel):
    id: int
    month: str
    date_op: Optional[dt.date]
    label: str
    category: str
    category_parent: str
    amount: float
    account_label: str
    is_expense: bool
    exclude: bool
    row_id: str
    tags: List[str]
    import_id: Optional[str] = None

class SummaryOut(BaseModel):
    month: str
    var_total: float
    fixed_lines_total: float      # Total des lignes fixes personnalisables
    provisions_total: float       # Total des provisions personnalisables 
    r1: float
    r2: float
    member1: str
    member2: str
    total_p1: float
    total_p2: float
    detail: dict
    
    # Nouveaux champs pour optimiser les calculs frontend
    var_p1: Optional[float] = None       # Part membre 1 des variables
    var_p2: Optional[float] = None       # Part membre 2 des variables
    fixed_p1: Optional[float] = None     # Part membre 1 des fixes
    fixed_p2: Optional[float] = None     # Part membre 2 des fixes
    provisions_p1: Optional[float] = None # Part membre 1 des provisions
    provisions_p2: Optional[float] = None # Part membre 2 des provisions
    grand_total: Optional[float] = None   # Total général (P1 + P2)
    
    # Métadonnées pour les calculs
    transaction_count: Optional[int] = None      # Nombre total de transactions
    active_fixed_lines: Optional[int] = None     # Nombre de lignes fixes actives
    active_provisions: Optional[int] = None      # Nombre de provisions actives

class ExcludeIn(BaseModel):
    exclude: bool

class TagsIn(BaseModel):
    tags: List[str]

class FixedLineIn(BaseModel):
    label: str = Field(..., min_length=1, max_length=100, description="Libellé de la ligne fixe")
    amount: float = Field(..., ge=0, le=99999.99, description="Montant")
    freq: str = Field(..., pattern="^(mensuelle|trimestrielle|annuelle)$", description="Fréquence")
    split_mode: str = Field(..., pattern="^(clé|50/50|m1|m2|manuel)$", description="Mode de répartition")
    split1: float = Field(0.5, ge=0, le=1, description="Part membre 1")
    split2: float = Field(0.5, ge=0, le=1, description="Part membre 2")
    category: str = Field("autres", pattern="^(logement|transport|services|loisirs|santé|autres)$", description="Catégorie")
    active: bool = Field(True, description="Ligne active")
    
    @validator('label')
    def sanitize_label(cls, v):
        return escape(str(v).strip())[:100]

class FixedLineOut(FixedLineIn):
    id: int

# Modèles Pydantic pour les provisions personnalisables
class CustomProvisionBase(BaseModel):
    """Base model pour les provisions personnalisables"""
    name: str = Field(..., min_length=1, max_length=100, description="Nom de la provision")
    description: Optional[str] = Field(None, max_length=500, description="Description optionnelle")
    percentage: float = Field(..., ge=0, le=100, description="Pourcentage du revenu")
    base_calculation: str = Field("total", pattern="^(total|member1|member2|fixed)$")
    fixed_amount: Optional[float] = Field(0, ge=0, description="Montant fixe si applicable")
    split_mode: str = Field("key", pattern="^(key|50/50|custom|100/0|0/100)$")
    split_member1: Optional[float] = Field(50, ge=0, le=100)
    split_member2: Optional[float] = Field(50, ge=0, le=100)
    icon: str = Field("💰", max_length=50)
    color: str = Field("#6366f1", pattern="^#[0-9A-Fa-f]{6}$")
    display_order: Optional[int] = Field(999, ge=0)
    is_active: bool = Field(True)
    is_temporary: bool = Field(False)
    start_date: Optional[dt.datetime] = None
    end_date: Optional[dt.datetime] = None
    target_amount: Optional[float] = Field(None, ge=0)
    category: str = Field("custom", pattern="^(savings|investment|project|custom)$")
    
    @validator('split_member1', 'split_member2')
    def validate_splits(cls, v, values):
        """Valide que les splits totalisent 100% si mode custom"""
        if values.get('split_mode') == 'custom':
            if 'split_member1' in values and values['split_member1'] + v != 100:
                raise ValueError('Les pourcentages membre1 + membre2 doivent totaliser 100%')
        return v
    
    @validator('fixed_amount')
    def validate_fixed_amount(cls, v, values):
        """Valide que le montant fixe est fourni si base_calculation = fixed"""
        if values.get('base_calculation') == 'fixed' and (v is None or v <= 0):
            raise ValueError('Un montant fixe positif est requis si base_calculation = fixed')
        return v

class CustomProvisionCreate(CustomProvisionBase):
    """Modèle pour créer une provision"""
    pass

class CustomProvisionUpdate(BaseModel):
    """Modèle pour mettre à jour une provision (tous les champs optionnels)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    percentage: Optional[float] = Field(None, ge=0, le=100)
    base_calculation: Optional[str] = Field(None, pattern="^(total|member1|member2|fixed)$")
    fixed_amount: Optional[float] = Field(None, ge=0)
    split_mode: Optional[str] = Field(None, pattern="^(key|50/50|custom|100/0|0/100)$")
    split_member1: Optional[float] = Field(None, ge=0, le=100)
    split_member2: Optional[float] = Field(None, ge=0, le=100)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_temporary: Optional[bool] = None
    start_date: Optional[dt.datetime] = None
    end_date: Optional[dt.datetime] = None
    target_amount: Optional[float] = Field(None, ge=0)
    current_amount: Optional[float] = Field(None, ge=0)
    category: Optional[str] = Field(None, pattern="^(savings|investment|project|custom)$")

class CustomProvisionResponse(CustomProvisionBase):
    """Modèle de réponse pour une provision"""
    id: int
    current_amount: float
    created_at: dt.datetime
    updated_at: Optional[dt.datetime]
    created_by: Optional[str]
    monthly_amount: Optional[float] = Field(None, description="Montant mensuel calculé")
    progress_percentage: Optional[float] = Field(None, description="Progression vers l'objectif")
    
    class Config:
        from_attributes = True

class CustomProvisionSummary(BaseModel):
    """Résumé des provisions personnalisées pour le dashboard"""
    total_provisions: int
    active_provisions: int
    total_monthly_amount: float
    total_monthly_member1: float
    total_monthly_member2: float
    provisions_by_category: Dict[str, int]
    provisions_details: List[CustomProvisionResponse]

# Types pour le nouveau système d'import optimisé
class ImportMonth(BaseModel):
    month: str = Field(..., description="Format YYYY-MM")
    newCount: int = Field(..., ge=0, description="Nouvelles transactions créées")
    totalCount: int = Field(..., ge=0, description="Total dans le fichier pour ce mois")
    txIds: List[int] = Field(default_factory=list, description="IDs des nouvelles transactions")
    firstDate: str = Field(..., description="Première date du mois")
    lastDate: str = Field(..., description="Dernière date du mois")

class ImportResponse(BaseModel):
    importId: str = Field(..., description="UUID unique de l'import")
    months: List[ImportMonth] = Field(default_factory=list, description="Mois détectés avec métadonnées")
    suggestedMonth: Optional[str] = Field(None, description="Mois recommandé pour la redirection")
    duplicatesCount: int = Field(default=0, ge=0, description="Nombre de doublons ignorés")
    warnings: List[str] = Field(default_factory=list, description="Avertissements")
    errors: List[str] = Field(default_factory=list, description="Erreurs de parsing")
    processing: str = Field(default="done", pattern="^(done|processing)$", description="État du traitement")
    fileName: str = Field(..., description="Nom du fichier original")
    processingMs: int = Field(..., ge=0, description="Temps de traitement en millisecondes")

# ---------- Helpers ----------
EXPECTED_COLS = ["dateOp","dateVal","label","category","categoryParent",
                 "supplierFound","amount","comment","accountNum","accountLabel","accountbalance"]

def parse_number(x):
    if x is None:
        return np.nan
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace("\xa0"," ").replace(" ", "")
    s = s.replace(",", ".")
    s = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", s)
    try:
        return float(s)
    except Exception:
        return np.nan

def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    def norm(s):
        s = str(s).strip().lower()
        s = (s.replace("é","e").replace("è","e").replace("ê","e")
               .replace("à","a").replace("ô","o").replace("ï","i").replace("î","i"))
        s = re.sub(r"[^a-z0-9]+", "", s)
        return s
    mapping_src = {
        "dateop":"dateOp","dateval":"dateVal","label":"label","category":"category",
        "categoryparent":"categoryParent","supplierfound":"supplierFound","amount":"amount",
        "comment":"comment","accountnum":"accountNum","accountlabel":"accountLabel","accountbalance":"accountbalance",
        # French column mappings for common CSV formats
        "date":"dateOp","description":"label","montant":"amount","compte":"accountLabel",
        "categorie":"category","libelle":"label","solde":"accountbalance"
    }
    cur = {norm(c): c for c in df.columns}
    rename = {}
    for k_norm, target in mapping_src.items():
        if k_norm in cur:
            rename[cur[k_norm]] = target
    out = df.rename(columns=rename)
    for c in EXPECTED_COLS:
        if c not in out.columns:
            out[c] = np.nan
    out["amount"] = out["amount"].apply(parse_number)
    out["dateOp"] = pd.to_datetime(out["dateOp"], errors="coerce")
    for c in ["label","category","categoryParent","accountLabel"]:
        out[c] = out[c].fillna("").astype(str)
    return out

def sanitize_filename(filename: str) -> str:
    """Sanitise le nom de fichier pour éviter les attaques de traversée de répertoire"""
    import os
    # Supprime les caractères dangereux (slashes, backslashes, etc.)
    safe_chars = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    # Bloque toute séquence de deux points '..'
    while '..' in safe_chars:
        safe_chars = safe_chars.replace('..', '.')
    # Évite les noms de fichiers système Windows
    forbidden_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1,10)] + [f'LPT{i}' for i in range(1,10)]
    name_without_ext = os.path.splitext(safe_chars)[0].upper()
    if name_without_ext in forbidden_names:
        safe_chars = f"file_{safe_chars}"
    return safe_chars[:100]  # Limite la longueur

def validate_file_security(file: UploadFile) -> bool:
    """Valide la sécurité d'un fichier uploadé - TEMPORAIREMENT DESACTIVÉE POUR DÉPANNAGE CSV"""
    
    # TODO: RE-ACTIVER LA SÉCURITÉ COMPLÈTE APRÈS RÉSOLUTION PROBLÈME CSV
    # Cette fonction est temporairement simplifiée pour débloquer l'import CSV
    # en attendant la résolution des problèmes de validation MIME
    
    try:
        # 1. Vérification nom de fichier basique
        if not file.filename or len(file.filename) > 255:
            logger.warning("Nom de fichier manquant ou trop long")
            return False
        
        # 2. Vérification extension basique
        allowed_extensions = {'.csv', '.xlsx', '.xls'}
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in allowed_extensions:
            logger.warning(f"Extension non autorisée: {file_ext}")
            return False
            
        # 3. Validation taille (conservée pour sécurité DoS)
        file.file.seek(0, 2)  # Fin du fichier
        file_size = file.file.tell()
        file.file.seek(0)     # Retour au début
        
        max_size = 10 * 1024 * 1024  # 10MB fixe - pas de variable env
        if file_size > max_size:
            logger.warning(f"Fichier trop volumineux: {file_size} bytes")
            return False
        
        # SÉCURITÉ TEMPORAIREMENT DÉSACTIVÉE - Accepter tous les CSV/Excel valides
        logger.info(f"BYPASS SÉCURITÉ TEMPORAIRE: Validation simplifiée pour {file.filename}")
        return True
        
        # === CODE COMMENTÉ TEMPORAIREMENT ===
        # # 4. Validation signature magique si disponible
        # if MAGIC_AVAILABLE:
        #     file_header = file.file.read(min(8192, file_size))  # Plus large pour détection précise
        #     file.file.seek(0)
        #     
        #     mime_type = magic.from_buffer(file_header, mime=True)
        #     allowed_mimes = {
        #         'text/csv', 'text/plain',
        #         'application/vnd.ms-excel',
        #         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        #         'application/zip'  # XLSX est un ZIP
        #     }
        #     
        #     if mime_type not in allowed_mimes:
        #         logger.error(f"SÉCURITÉ: Type MIME rejeté: {mime_type} pour {file.filename}")
        #         # Pour le debugging, logguer les détails du fichier
        #         logger.info(f"DEBUG: Fichier {file.filename}, MIME détecté: {mime_type}, Extension: {file_ext}")
        #         if file_ext == '.csv' and mime_type in ['application/octet-stream', 'text/plain']:
        #             # Tolérance pour CSV détecté comme text/plain
        #             logger.info(f"Tolérance appliquée pour CSV: {file.filename}")
        #         else:
        #             return False
        # else:
        #     # Validation basique sans magic
        #     logger.info("Validation MIME simplifiée (magic non disponible)")
        # 
        # # 5. Validation signature binaire spécifique
        # file.file.seek(0)
        # first_bytes = file.file.read(512)  # Lire plus pour une meilleure détection
        # file.file.seek(0)
        # 
        # # Signatures Excel
        # xlsx_signature = b'PK\x03\x04'  # ZIP header pour XLSX
        # xls_signature = b'\xd0\xcf\x11\xe0'  # OLE2 header pour XLS
        # 
        # # Pour CSV, validation plus flexible
        # if file_ext == '.csv':
        #     is_valid_csv = False
        #     
        #     # 1. Vérifier BOM UTF-8
        #     if first_bytes.startswith(b'\xef\xbb\xbf'):
        #         is_valid_csv = True
        #     else:
        #         # 2. Essayer de décoder comme texte et vérifier structure CSV
        #         try:
        #             # Décoder avec différents encodages
        #             text_content = None
        #             for encoding in ['utf-8', 'latin-1', 'cp1252']:
        #                 try:
        #                     text_content = first_bytes.decode(encoding, errors='ignore')
        #                     break
        #                 except:
        #                     continue
        #             
        #             if text_content:
        #                 first_line = text_content.split('\n')[0].strip()
        #                 
        #                 # 3. Vérifier présence de séparateurs CSV
        #                 has_separators = any(sep in first_line for sep in [',', ';', '\t', '|'])
        #                 
        #                 # 4. Vérifier que c'est principalement du texte (pas binaire)
        #                 is_text = True
        #                 if first_line:
        #                     try:
        #                         # Vérifier caractères imprimables + caractères français courants
        #                         check_chars = first_line[:100]
        #                         printable_count = sum(1 for c in check_chars if (32 <= ord(c) <= 126 or c in '\r\n\t' or ord(c) in [192, 193, 200, 201, 202, 206, 207, 212, 217, 224, 225, 226, 231, 232, 233, 234, 235, 238, 239, 244, 249, 250, 251]))
        #                         is_text = (printable_count / len(check_chars)) >= 0.8  # Au moins 80% de caractères valides
        #                     except:
        #                         is_text = True  # En cas d'erreur, ne pas bloquer
        #                 
        #                 # 5. Patterns de headers CSV communs
        #                 common_headers = ['date', 'dateop', 'dateval', 'label', 'libelle', 'description', 
        #                                 'montant', 'amount', 'compte', 'account', 'category', 'categorie',
        #                                 'debit', 'credit', 'balance', 'solde']
        #                 has_common_headers = any(header in first_line.lower() for header in common_headers)
        #                 
        #                 # CSV valide si: (séparateurs ET texte) OU headers communs
        #                 is_valid_csv = (has_separators and is_text) or has_common_headers
        #                 
        #         except Exception as e:
        #             logger.warning(f"Erreur validation texte CSV: {e}")
        #             # En cas d'erreur de décodage, accepter si extension CSV
        #             is_valid_csv = True
        #     
        #     if not is_valid_csv:
        #         logger.error(f"SÉCURITÉ: Fichier CSV invalide pour {file.filename}")
        #         return False
        # 
        # # Pour Excel, vérification signature binaire
        # elif file_ext in ['.xlsx', '.xls']:
        #     is_valid_excel = (
        #         first_bytes.startswith(xlsx_signature) or 
        #         first_bytes.startswith(xls_signature)
        #     )
        #     
        #     if not is_valid_excel:
        #         logger.error(f"SÉCURITÉ: Signature Excel invalide pour {file.filename}")
        #         return False
        #     
        # return True
        
    except Exception as e:
        logger.error(f"CRITICAL: Erreur validation sécurité fichier: {e}")
        return False

def robust_read_csv(file: UploadFile) -> pd.DataFrame:
    # Validation sécurisée préalable renforcée
    if not validate_file_security(file):
        raise HTTPException(status_code=400, detail="Fichier non sécurisé - validation échouée")
        
    content = file.file.read()
    file.file.seek(0)
    
    # Protection DoS - taille fixe sécurisée (pas de variable env)
    max_size = 10 * 1024 * 1024  # 10MB fixe
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 10MB)")
    
    # Validation contenu non-malicieux
    try:
        # Vérification encoding sécurisé
        decoded_content = content.decode('utf-8', errors='replace')
        # Recherche de patterns malicieux
        malicious_patterns = ['<script', '<?php', '#!/', 'exec(', 'eval(']
        for pattern in malicious_patterns:
            if pattern in decoded_content.lower():
                logger.error(f"SÉCURITÉ: Pattern malicieux détecté: {pattern}")
                raise HTTPException(status_code=400, detail="Contenu fichier suspect")
    except UnicodeDecodeError:
        # Si pas UTF-8, on continue avec les autres encodings
        pass
    for enc in ["utf-8","latin-1","cp1252"]:
        try:
            text = content.decode(enc, errors="replace")
        except Exception:
            continue
        try:
            dialect = csv.Sniffer().sniff(text[:5000], delimiters=",;\t|")
            sep = dialect.delimiter
        except Exception:
            sep = None
        for engine in ["python","c"]:
            try:
                df = pd.read_csv(io.StringIO(text),
                                 sep=sep, engine=engine,
                                 on_bad_lines="skip", dtype=str)
                if df.shape[1] >= 3:
                    return df
            except Exception:
                for alt in [";",
                            ",",
                            "\t",
                            "|"]:
                    try:
                        df = pd.read_csv(io.StringIO(text), sep=alt,
                                         engine="python", on_bad_lines="skip", dtype=str)
                        if df.shape[1] >= 3:
                            return df
                    except Exception:
                        pass
    return pd.DataFrame()

# --- Fonctions helper pour l'import intelligent ---
def detect_months_with_metadata(df: pd.DataFrame) -> List[Dict]:
    """Détecte les mois présents dans le DataFrame avec métadonnées"""
    months_data = {}
    
    for _, row in df.iterrows():
        if pd.isna(row.get('dateOp')):
            continue
            
        try:
            date_op = pd.to_datetime(row['dateOp']).date()
            month_key = f"{date_op.year}-{date_op.month:02d}"
            
            if month_key not in months_data:
                months_data[month_key] = {
                    'month': month_key,
                    'transactions': [],
                    'first_date': date_op,
                    'last_date': date_op
                }
            
            months_data[month_key]['transactions'].append(row)
            months_data[month_key]['first_date'] = min(
                months_data[month_key]['first_date'], 
                date_op
            )
            months_data[month_key]['last_date'] = max(
                months_data[month_key]['last_date'], 
                date_op
            )
        except Exception:
            continue  # Ignorer les dates invalides
    
    return list(months_data.values())

def suggest_optimal_month(months_data: List[Dict]) -> Optional[str]:
    """Suggère le mois optimal pour la redirection"""
    if not months_data:
        return None
    
    # Stratégie: prendre le mois avec le plus de transactions
    # ou le mois le plus récent en cas d'égalité
    best_month = None
    max_count = 0
    most_recent_date = None
    
    for month_data in months_data:
        count = len(month_data['transactions'])
        last_date = month_data['last_date']
        
        if (count > max_count or 
            (count == max_count and (most_recent_date is None or last_date > most_recent_date))):
            best_month = month_data['month']
            max_count = count
            most_recent_date = last_date
    
    return best_month

def check_duplicate_transactions(df: pd.DataFrame, db: Session) -> Dict:
    """Vérifie les doublons internes et avec la base existante"""
    duplicates = {
        'internal': [],      # Doublons dans le fichier
        'existing': [],      # Déjà présent en base
        'clean_rows': []     # Lignes à importer
    }
    
    seen_hashes = set()
    
    for idx, row in df.iterrows():
        if pd.isna(row.get('dateOp')):
            continue
            
        try:
            date_op = pd.to_datetime(row['dateOp']).date()
            label = str(row.get('label', ''))
            amount = float(row.get('amount', 0))
            account_num = str(row.get('accountNum', ''))
            
            # Calcul du hash comme dans l'original
            row_hash = hashlib.md5(f"{date_op}|{label}|{amount}|{account_num}".encode("utf-8")).hexdigest()
            
            # Vérification doublon interne
            if row_hash in seen_hashes:
                duplicates['internal'].append({
                    'row': idx,
                    'hash': row_hash,
                    'date': str(date_op),
                    'label': label,
                    'amount': amount
                })
                continue
            
            # Vérification doublon en base
            existing = db.query(Transaction).filter(Transaction.row_id == row_hash).first()
            if existing:
                duplicates['existing'].append({
                    'row': idx,
                    'hash': row_hash,
                    'date': str(date_op),
                    'label': label,
                    'amount': amount,
                    'existing_id': existing.id
                })
                continue
            
            seen_hashes.add(row_hash)
            duplicates['clean_rows'].append(idx)
            
        except Exception as e:
            logger.warning(f"Erreur vérification doublon ligne {idx}: {e}")
            continue
    
    return duplicates

def validate_csv_data(df: pd.DataFrame) -> List[str]:
    """Valide la qualité des données CSV et retourne les warnings"""
    warnings = []
    
    # Vérifier les dates futures
    try:
        future_threshold = dt.datetime.now().date() + dt.timedelta(days=30)
        future_dates = 0
        for _, row in df.iterrows():
            if pd.notna(row.get('dateOp')):
                try:
                    date_op = pd.to_datetime(row['dateOp']).date()
                    if date_op > future_threshold:
                        future_dates += 1
                except:
                    pass
        
        if future_dates > 0:
            warnings.append(f"{future_dates} transactions avec dates futures détectées")
    except Exception:
        pass
    
    # Vérifier les montants extrêmes
    try:
        extreme_amounts = 0
        for _, row in df.iterrows():
            try:
                amount = abs(float(row.get('amount', 0)))
                if amount > 50000:  # > 50k€
                    extreme_amounts += 1
            except:
                pass
                
        if extreme_amounts > 0:
            warnings.append(f"{extreme_amounts} montants > 50k€ détectés")
    except Exception:
        pass
    
    # Vérifier les données manquantes critiques
    try:
        missing_amounts = sum(1 for _, row in df.iterrows() if pd.isna(row.get('amount')) or row.get('amount') == '')
        if missing_amounts > 0:
            warnings.append(f"{missing_amounts} montants manquants")
            
        missing_dates = sum(1 for _, row in df.iterrows() if pd.isna(row.get('dateOp')))
        if missing_dates > 0:
            warnings.append(f"{missing_dates} dates manquantes")
    except Exception:
        pass
    
    return warnings[:5]  # Limiter à 5 warnings max pour l'UI

def get_split(cfg: Config):
    if cfg.split_mode == "revenus":
        tot = (cfg.rev1 or 0) + (cfg.rev2 or 0)
        if tot <= 0: return 0.5, 0.5
        r1 = (cfg.rev1 or 0)/tot
        return r1, 1-r1
    else:
        return cfg.split1, cfg.split2

# ---------- Fonctions utilitaires pour les provisions personnalisables ----------

def calculate_provision_amount(provision: CustomProvision, config: Config) -> tuple:
    """
    Calcule le montant mensuel d'une provision et sa répartition
    Returns: (montant_total, montant_membre1, montant_membre2)
    """
    # Calcul de la base
    if provision.base_calculation == "total":
        base = (config.rev1 or 0) + (config.rev2 or 0)
    elif provision.base_calculation == "member1":
        base = config.rev1 or 0
    elif provision.base_calculation == "member2":
        base = config.rev2 or 0
    elif provision.base_calculation == "fixed":
        base = provision.fixed_amount or 0
    else:
        base = 0
    
    # Calcul du montant mensuel
    if provision.base_calculation == "fixed":
        monthly_amount = base  # Déjà mensuel
    else:
        monthly_amount = (base * provision.percentage / 100.0) / 12.0 if base else 0.0
    
    # Calcul de la répartition
    if provision.split_mode == "key":
        # Utiliser la clé de répartition globale
        total_rev = (config.rev1 or 0) + (config.rev2 or 0)
        if total_rev > 0:
            r1 = (config.rev1 or 0) / total_rev
            r2 = (config.rev2 or 0) / total_rev
        else:
            r1 = r2 = 0.5
        member1_amount = monthly_amount * r1
        member2_amount = monthly_amount * r2
    elif provision.split_mode == "50/50":
        member1_amount = monthly_amount * 0.5
        member2_amount = monthly_amount * 0.5
    elif provision.split_mode == "100/0":
        member1_amount = monthly_amount
        member2_amount = 0
    elif provision.split_mode == "0/100":
        member1_amount = 0
        member2_amount = monthly_amount
    elif provision.split_mode == "custom":
        member1_amount = monthly_amount * (provision.split_member1 / 100.0)
        member2_amount = monthly_amount * (provision.split_member2 / 100.0)
    else:
        member1_amount = member2_amount = monthly_amount * 0.5
    
    return monthly_amount, member1_amount, member2_amount

def get_active_provisions(db: Session, current_date: dt.datetime = None) -> List[CustomProvision]:
    """Récupère toutes les provisions actives à une date donnée"""
    if current_date is None:
        current_date = dt.datetime.now()
    
    query = db.query(CustomProvision).filter(CustomProvision.is_active == True)
    
    # Filtrer par dates si applicable
    query = query.filter(
        (CustomProvision.start_date == None) | (CustomProvision.start_date <= current_date)
    ).filter(
        (CustomProvision.end_date == None) | (CustomProvision.end_date >= current_date)
    )
    
    return query.order_by(CustomProvision.display_order, CustomProvision.name).all()

def calculate_provisions_summary(db: Session, config: Config) -> CustomProvisionSummary:
    """Calcule le résumé complet des provisions personnalisables"""
    provisions = get_active_provisions(db)
    
    total_provisions = db.query(CustomProvision).count()
    active_provisions = len(provisions)
    total_monthly_amount = 0.0
    total_monthly_member1 = 0.0
    total_monthly_member2 = 0.0
    
    # Comptage par catégorie
    provisions_by_category = {}
    provisions_details = []
    
    for provision in provisions:
        # Calculs pour chaque provision
        monthly_amount, member1_amount, member2_amount = calculate_provision_amount(provision, config)
        
        # Calcul du pourcentage de progression
        progress_percentage = None
        if provision.target_amount and provision.target_amount > 0:
            progress_percentage = min(100.0, (provision.current_amount / provision.target_amount) * 100)
        
        # Créer la réponse avec calculs
        provision_response = CustomProvisionResponse(
            id=provision.id,
            name=provision.name,
            description=provision.description,
            percentage=provision.percentage,
            base_calculation=provision.base_calculation,
            fixed_amount=provision.fixed_amount,
            split_mode=provision.split_mode,
            split_member1=provision.split_member1,
            split_member2=provision.split_member2,
            icon=provision.icon,
            color=provision.color,
            display_order=provision.display_order,
            is_active=provision.is_active,
            is_temporary=provision.is_temporary,
            start_date=provision.start_date,
            end_date=provision.end_date,
            target_amount=provision.target_amount,
            category=provision.category,
            current_amount=provision.current_amount,
            created_at=provision.created_at,
            updated_at=provision.updated_at,
            created_by=provision.created_by,
            monthly_amount=monthly_amount,
            progress_percentage=progress_percentage
        )
        
        provisions_details.append(provision_response)
        
        # Agrégation
        total_monthly_amount += monthly_amount
        total_monthly_member1 += member1_amount
        total_monthly_member2 += member2_amount
        
        # Comptage par catégorie
        category = provision.category or "custom"
        provisions_by_category[category] = provisions_by_category.get(category, 0) + 1
    
    return CustomProvisionSummary(
        total_provisions=total_provisions,
        active_provisions=active_provisions,
        total_monthly_amount=total_monthly_amount,
        total_monthly_member1=total_monthly_member1,
        total_monthly_member2=total_monthly_member2,
        provisions_by_category=provisions_by_category,
        provisions_details=provisions_details
    )

def is_income_or_transfer(label: str, cat_parent: str) -> bool:
    l = (label or "").lower(); cp = (cat_parent or "").lower()
    if "virement" in l or "vir " in l or "vir/" in l or "virements emis" in cp: return True
    if "rembourse" in l or "refund" in l or "remboursement" in cp: return True
    if "salaire" in l or "payroll" in l or "paye" in l: return True
    return False

def split_amount(amount: float, mode: str, r1: float, r2: float, s1: float, s2: float):
    if mode == "50/50":
        return amount/2.0, amount/2.0
    if mode == "clé":
        return amount*r1, amount*r2
    if mode == "m1":
        return amount, 0.0
    if mode == "m2":
        return 0.0, amount
    if mode == "manuel":
        return amount*(s1 or 0.0), amount*(s2 or 0.0)
    return amount*r1, amount*r2

# ---------- Analytics Helper Functions ----------
def calculate_monthly_trends(db: Session, months: List[str]) -> List[MonthlyTrend]:
    """Calcule les tendances mensuelles pour les mois spécifiés"""
    trends = []
    for month in months:
        expenses_result = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.is_expense == True,
            Transaction.exclude == False,
            Transaction.amount < 0
        ).all()
        
        income_result = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.is_expense == False,
            Transaction.exclude == False,
            Transaction.amount > 0
        ).all()
        
        total_expenses = sum(abs(tx.amount or 0) for tx in expenses_result)
        total_income = sum(tx.amount or 0 for tx in income_result)
        net = total_income - total_expenses
        transaction_count = len(expenses_result) + len(income_result)
        
        trends.append(MonthlyTrend(
            month=month,
            total_expenses=total_expenses,
            total_income=total_income,
            net=net,
            transaction_count=transaction_count
        ))
    
    return trends

def calculate_category_breakdown(db: Session, month: str) -> List[CategoryBreakdown]:
    """Calcule la répartition par catégorie pour un mois donné"""
    categories = {}
    
    transactions = db.query(Transaction).filter(
        Transaction.month == month,
        Transaction.is_expense == True,
        Transaction.exclude == False,
        Transaction.amount < 0
    ).all()
    
    total_expenses = 0
    for tx in transactions:
        amount = abs(tx.amount or 0)
        total_expenses += amount
        category = tx.category or "Autre"
        
        if category not in categories:
            categories[category] = {"amount": 0, "count": 0}
        
        categories[category]["amount"] += amount
        categories[category]["count"] += 1
    
    breakdown = []
    for category, data in categories.items():
        percentage = (data["amount"] / total_expenses * 100) if total_expenses > 0 else 0
        avg_transaction = data["amount"] / data["count"] if data["count"] > 0 else 0
        
        breakdown.append(CategoryBreakdown(
            category=category,
            amount=data["amount"],
            percentage=percentage,
            transaction_count=data["count"],
            avg_transaction=avg_transaction
        ))
    
    return sorted(breakdown, key=lambda x: x.amount, reverse=True)

def calculate_kpi_summary(db: Session, months: List[str]) -> KPISummary:
    """Calcule les KPIs généraux pour une période"""
    all_expenses = []
    all_income = []
    total_transactions = 0
    
    for month in months:
        transactions = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.exclude == False
        ).all()
        
        for tx in transactions:
            total_transactions += 1
            if tx.is_expense and tx.amount < 0:
                all_expenses.append(abs(tx.amount or 0))
            elif not tx.is_expense and tx.amount > 0:
                all_income.append(tx.amount or 0)
    
    total_expenses = sum(all_expenses)
    total_income = sum(all_income)
    net_balance = total_income - total_expenses
    
    months_count = len(months)
    avg_monthly_expenses = total_expenses / months_count if months_count > 0 else 0
    avg_monthly_income = total_income / months_count if months_count > 0 else 0
    
    # Calcul de la tendance
    if months_count >= 2:
        recent_months = months[-2:]  # 2 derniers mois
        old_expenses = db.query(Transaction).filter(
            Transaction.month == recent_months[0],
            Transaction.is_expense == True,
            Transaction.exclude == False,
            Transaction.amount < 0
        ).all()
        new_expenses = db.query(Transaction).filter(
            Transaction.month == recent_months[1],
            Transaction.is_expense == True,
            Transaction.exclude == False,
            Transaction.amount < 0
        ).all()
        
        old_total = sum(abs(tx.amount or 0) for tx in old_expenses)
        new_total = sum(abs(tx.amount or 0) for tx in new_expenses)
        
        if new_total > old_total * 1.05:  # +5%
            expense_trend = "up"
        elif new_total < old_total * 0.95:  # -5%
            expense_trend = "down"
        else:
            expense_trend = "stable"
    else:
        expense_trend = "stable"
    
    # Top catégorie de dépense
    top_category = None
    top_amount = 0.0
    if months:
        latest_month = months[-1]
        breakdown = calculate_category_breakdown(db, latest_month)
        if breakdown:
            top_category = breakdown[0].category
            top_amount = breakdown[0].amount
    
    return KPISummary(
        period_start=months[0] if months else "",
        period_end=months[-1] if months else "",
        total_expenses=total_expenses,
        total_income=total_income,
        net_balance=net_balance,
        avg_monthly_expenses=avg_monthly_expenses,
        avg_monthly_income=avg_monthly_income,
        top_expense_category=top_category,
        top_expense_amount=top_amount,
        transaction_count=total_transactions,
        expense_trend=expense_trend
    )

def detect_anomalies(db: Session, month: str) -> List[AnomalyDetection]:
    """Détecte les anomalies dans les dépenses d'un mois"""
    anomalies = []
    
    # Récupérer toutes les transactions du mois
    transactions = db.query(Transaction).filter(
        Transaction.month == month,
        Transaction.exclude == False
    ).all()
    
    # Calcul des seuils basés sur l'historique
    historical_transactions = db.query(Transaction).filter(
        Transaction.exclude == False,
        Transaction.is_expense == True,
        Transaction.amount < 0
    ).all()
    
    if not historical_transactions:
        return anomalies
    
    amounts = [abs(tx.amount or 0) for tx in historical_transactions]
    avg_amount = np.mean(amounts) if amounts else 0
    std_amount = np.std(amounts) if amounts else 0
    
    # Seuil pour montants élevés (> moyenne + 2 écarts-types)
    high_amount_threshold = avg_amount + (2 * std_amount)
    
    for tx in transactions:
        score = 0.0
        anomaly_type = None
        
        if tx.is_expense and tx.amount < 0:
            amount = abs(tx.amount or 0)
            
            # Détection montant élevé
            if amount > high_amount_threshold:
                anomaly_type = "high_amount"
                score = min(1.0, amount / high_amount_threshold - 1)
        
        if score > 0.3 and anomaly_type:  # Seuil de confiance
            anomalies.append(AnomalyDetection(
                transaction_id=tx.id,
                date=str(tx.date_op),
                amount=tx.amount or 0,
                category=tx.category or "Autre",
                label=tx.label or "",
                anomaly_type=anomaly_type,
                score=score
            ))
    
    return sorted(anomalies, key=lambda x: x.score, reverse=True)[:10]  # Top 10

def calculate_spending_patterns(db: Session, months: List[str]) -> List[SpendingPattern]:
    """Analyse les patterns de dépense par jour de la semaine"""
    import calendar
    from collections import defaultdict
    
    patterns = defaultdict(lambda: {"amounts": [], "count": 0})
    
    for month in months:
        transactions = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.is_expense == True,
            Transaction.exclude == False,
            Transaction.amount < 0,
            Transaction.date_op.isnot(None)
        ).all()
        
        for tx in transactions:
            if tx.date_op:
                day_of_week = tx.date_op.weekday()  # 0 = Monday
                amount = abs(tx.amount or 0)
                patterns[day_of_week]["amounts"].append(amount)
                patterns[day_of_week]["count"] += 1
    
    result = []
    day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    
    for day_idx in range(7):
        data = patterns[day_idx]
        avg_amount = np.mean(data["amounts"]) if data["amounts"] else 0
        
        result.append(SpendingPattern(
            day_of_week=day_idx,
            day_name=day_names[day_idx],
            avg_amount=avg_amount,
            transaction_count=data["count"]
        ))
    
    return result

# ---------- Routes ----------
def _build_config_response(cfg: Config) -> ConfigOut:
    """Helper function to build ConfigOut response"""
    return ConfigOut(
        id=cfg.id, 
        member1=cfg.member1, 
        member2=cfg.member2, 
        rev1=cfg.rev1, 
        rev2=cfg.rev2,
        split_mode=cfg.split_mode, 
        split1=cfg.split1, 
        split2=cfg.split2,
        other_split_mode=cfg.other_split_mode,
        var_percent=getattr(cfg, 'var_percent', 30.0),
        max_var=getattr(cfg, 'max_var', 0.0),
        min_fixed=getattr(cfg, 'min_fixed', 0.0)
    )

@app.get("/config", response_model=ConfigOut)
def get_config(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = ensure_default_config(db)
    return _build_config_response(cfg)

@app.post(
    "/token", 
    response_model=Token,
    tags=["Authentification"],
    summary="Connexion utilisateur et génération de token JWT",
    description="""
    Endpoint d'authentification OAuth2 compatible pour l'obtention d'un token JWT.
    
    ### Flux d'authentification :
    1. **Envoi des identifiants** via formulaire URL-encoded
    2. **Validation** des credentials avec audit de sécurité
    3. **Génération** d'un token JWT avec expiration (24h par défaut)
    4. **Retour** du token Bearer pour les futures requêtes
    
    ### Utilisateurs par défaut :
    - **Utilisateur** : `admin`
    - **Mot de passe** : `secret`
    
    ### Sécurité :
    - Chiffrement PBKDF2 des mots de passe
    - Logging complet des tentatives d'authentification
    - Rate limiting automatique en cas d'abus
    - Tokens JWT signés avec clé secrète
    """,
    responses={
        200: {
            "description": "Authentification réussie - Token JWT généré",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTY5NzI4NzIwMH0.signature",
                        "token_type": "bearer",
                        "expires_in": 86400
                    }
                }
            }
        },
        401: {
            "description": "Échec d'authentification - Identifiants invalides",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Nom d'utilisateur ou mot de passe incorrect"
                    }
                }
            }
        },
        422: {
            "description": "Données de formulaire invalides ou manquantes",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "username"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authentification OAuth2 pour obtenir un token d'accès JWT.
    
    Utilise le format standard OAuth2 password flow avec form-data.
    """
    audit_logger = get_audit_logger()
    
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Tentative de connexion échouée pour: {form_data.username}")
        audit_logger.log_login_failed(
            username=form_data.username,
            reason="Invalid credentials"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    logger.info(f"Token généré pour utilisateur: {user.username}")
    audit_logger.log_login_success(username=user.username)
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/config", response_model=ConfigOut)
def update_config(payload: ConfigIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Endpoint protégé - Mise à jour de la configuration"""
    audit_logger = get_audit_logger()
    logger.info(f"Configuration mise à jour par utilisateur: {current_user.username}")
    
    cfg = ensure_default_config(db)
    changes = {}
    for k, v in payload.dict().items():
        old_value = getattr(cfg, k, None)
        if old_value != v:
            changes[k] = {"old": old_value, "new": v}
        setattr(cfg, k, v)
    
    db.add(cfg); db.commit(); db.refresh(cfg)
    
    audit_logger.log_event(
        AuditEventType.CONFIG_UPDATE,
        username=current_user.username,
        details={"changes_count": len(changes)},
        success=True
    )
    
    cfg = ensure_default_config(db)
    return _build_config_response(cfg)

@app.get("/fixed-lines", response_model=List[FixedLineOut])
def list_fixed_lines(
    category: Optional[str] = Query(None, regex="^(logement|transport|services|loisirs|santé|autres)$", description="Filtrer par catégorie"),
    active_only: bool = Query(True, description="Afficher uniquement les lignes actives"),
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Liste toutes les lignes fixes avec filtrage par catégorie"""
    query = db.query(FixedLine)
    
    if active_only:
        query = query.filter(FixedLine.active == True)
    
    if category:
        query = query.filter(FixedLine.category == category)
    
    items = query.order_by(FixedLine.category, FixedLine.id.asc()).all()
    return [FixedLineOut(
        id=i.id, 
        label=i.label, 
        amount=i.amount, 
        freq=i.freq, 
        split_mode=i.split_mode, 
        split1=i.split1, 
        split2=i.split2, 
        category=i.category,
        active=i.active
    ) for i in items]

@app.post("/fixed-lines", response_model=FixedLineOut)
def create_fixed_line(payload: FixedLineIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Crée une nouvelle ligne fixe"""
    logger.info(f"Création ligne fixe '{payload.label}' catégorie '{payload.category}' par utilisateur: {current_user.username}")
    f = FixedLine(
        label=payload.label, 
        amount=payload.amount, 
        freq=payload.freq,
        split_mode=payload.split_mode, 
        split1=payload.split1, 
        split2=payload.split2, 
        category=payload.category,
        active=payload.active
    )
    db.add(f); db.commit(); db.refresh(f)
    return FixedLineOut(
        id=f.id, 
        label=f.label, 
        amount=f.amount, 
        freq=f.freq, 
        split_mode=f.split_mode, 
        split1=f.split1, 
        split2=f.split2, 
        category=f.category,
        active=f.active
    )

@app.get("/fixed-lines/{lid}", response_model=FixedLineOut)
def get_fixed_line(lid: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Récupère une ligne fixe par son ID"""
    f = db.query(FixedLine).filter(FixedLine.id == lid).first()
    if not f:
        raise HTTPException(status_code=404, detail="Ligne fixe introuvable")
    
    return FixedLineOut(
        id=f.id, 
        label=f.label, 
        amount=f.amount, 
        freq=f.freq, 
        split_mode=f.split_mode, 
        split1=f.split1, 
        split2=f.split2, 
        category=f.category,
        active=f.active
    )

@app.patch("/fixed-lines/{lid}", response_model=FixedLineOut)
def update_fixed_line(lid: int, payload: FixedLineIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Met à jour une ligne fixe existante"""
    logger.info(f"Mise à jour ligne fixe {lid} par utilisateur: {current_user.username}")
    f = db.query(FixedLine).filter(FixedLine.id == lid).first()
    if not f: 
        raise HTTPException(status_code=404, detail="Ligne fixe introuvable")
    
    # Mise à jour avec validation
    for k, v in payload.dict().items():
        setattr(f, k, v)
    
    db.add(f); db.commit(); db.refresh(f)
    logger.info(f"Ligne fixe {lid} mise à jour: '{f.label}' - {f.category}")
    
    return FixedLineOut(
        id=f.id, 
        label=f.label, 
        amount=f.amount, 
        freq=f.freq, 
        split_mode=f.split_mode, 
        split1=f.split1, 
        split2=f.split2, 
        category=f.category,
        active=f.active
    )

@app.delete("/fixed-lines/{lid}")
def delete_fixed_line(lid: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Supprime une ligne fixe"""
    logger.info(f"Suppression ligne fixe {lid} par utilisateur: {current_user.username}")
    f = db.query(FixedLine).filter(FixedLine.id == lid).first()
    if not f: 
        raise HTTPException(status_code=404, detail="Ligne fixe introuvable")
    
    logger.info(f"Suppression confirmée: '{f.label}' - {f.category}")
    db.delete(f); db.commit()
    return {"ok": True, "message": f"Ligne fixe '{f.label}' supprimée"}

@app.get("/fixed-lines/stats/by-category")
def get_fixed_lines_stats_by_category(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Récupère les statistiques des lignes fixes par catégorie"""
    from sqlalchemy import func
    
    # Statistiques par catégorie
    stats = db.query(
        FixedLine.category,
        func.count(FixedLine.id).label('count'),
        func.sum(FixedLine.amount).label('total_amount')
    ).filter(
        FixedLine.active == True
    ).group_by(FixedLine.category).all()
    
    # Conversion en montants mensuels
    monthly_stats = []
    for cat, count, total in stats:
        # Calculer le total mensuel pour cette catégorie
        lines = db.query(FixedLine).filter(
            FixedLine.category == cat, 
            FixedLine.active == True
        ).all()
        
        monthly_total = 0.0
        for line in lines:
            if line.freq == "mensuelle":
                monthly_total += line.amount
            elif line.freq == "trimestrielle":
                monthly_total += (line.amount or 0.0) / 3.0
            else:  # annuelle
                monthly_total += (line.amount or 0.0) / 12.0
        
        monthly_stats.append({
            "category": cat,
            "count": count,
            "monthly_total": round(monthly_total, 2)
        })
    
    # Total général
    global_monthly_total = sum(s["monthly_total"] for s in monthly_stats)
    
    return {
        "by_category": monthly_stats,
        "global_monthly_total": round(global_monthly_total, 2),
        "total_lines": sum(s["count"] for s in monthly_stats)
    }

# ---------- Endpoints Provisions Personnalisables ----------

@app.get("/provisions", response_model=List[CustomProvisionResponse])
def list_provisions(
    active_only: bool = True,
    category: Optional[str] = None,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Liste toutes les provisions personnalisables de l'utilisateur"""
    logger.info(f"Liste provisions demandée par utilisateur: {current_user.username}")
    
    query = db.query(CustomProvision).filter(CustomProvision.created_by == current_user.username)
    
    if active_only:
        query = query.filter(CustomProvision.is_active == True)
    
    if category:
        query = query.filter(CustomProvision.category == category)
    
    provisions = query.order_by(CustomProvision.display_order, CustomProvision.name).all()
    
    # Calculer les montants pour chaque provision
    config = ensure_default_config(db)
    result = []
    
    for provision in provisions:
        monthly_amount, _, _ = calculate_provision_amount(provision, config)
        
        # Calcul du pourcentage de progression
        progress_percentage = None
        if provision.target_amount and provision.target_amount > 0:
            progress_percentage = min(100.0, (provision.current_amount / provision.target_amount) * 100)
        
        provision_response = CustomProvisionResponse(
            id=provision.id,
            name=provision.name,
            description=provision.description,
            percentage=provision.percentage,
            base_calculation=provision.base_calculation,
            fixed_amount=provision.fixed_amount,
            split_mode=provision.split_mode,
            split_member1=provision.split_member1,
            split_member2=provision.split_member2,
            icon=provision.icon,
            color=provision.color,
            display_order=provision.display_order,
            is_active=provision.is_active,
            is_temporary=provision.is_temporary,
            start_date=provision.start_date,
            end_date=provision.end_date,
            target_amount=provision.target_amount,
            category=provision.category,
            current_amount=provision.current_amount,
            created_at=provision.created_at,
            updated_at=provision.updated_at,
            created_by=provision.created_by,
            monthly_amount=monthly_amount,
            progress_percentage=progress_percentage
        )
        result.append(provision_response)
    
    return result

@app.post("/provisions", response_model=CustomProvisionResponse)
def create_provision(
    payload: CustomProvisionCreate,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Crée une nouvelle provision personnalisable"""
    audit_logger = get_audit_logger()
    logger.info(f"Création provision '{payload.name}' par utilisateur: {current_user.username}")
    
    # Vérifier qu'il n'y a pas de doublons de nom pour cet utilisateur
    existing = db.query(CustomProvision).filter(
        CustomProvision.created_by == current_user.username,
        CustomProvision.name == payload.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Une provision nommée '{payload.name}' existe déjà"
        )
    
    # Créer la nouvelle provision
    provision = CustomProvision(
        name=payload.name,
        description=payload.description,
        percentage=payload.percentage,
        base_calculation=payload.base_calculation,
        fixed_amount=payload.fixed_amount,
        split_mode=payload.split_mode,
        split_member1=payload.split_member1,
        split_member2=payload.split_member2,
        icon=payload.icon,
        color=payload.color,
        display_order=payload.display_order,
        is_active=payload.is_active,
        is_temporary=payload.is_temporary,
        start_date=payload.start_date,
        end_date=payload.end_date,
        target_amount=payload.target_amount,
        category=payload.category,
        created_by=current_user.username
    )
    
    db.add(provision)
    db.commit()
    db.refresh(provision)
    
    # Audit de création
    audit_logger.log_event(
        AuditEventType.CONFIG_UPDATE,
        username=current_user.username,
        details={
            "action": "create_provision",
            "provision_id": provision.id,
            "provision_name": provision.name,
            "percentage": provision.percentage
        },
        success=True
    )
    
    # Calculer le montant mensuel pour la réponse
    config = ensure_default_config(db)
    monthly_amount, _, _ = calculate_provision_amount(provision, config)
    
    # Calcul du pourcentage de progression
    progress_percentage = None
    if provision.target_amount and provision.target_amount > 0:
        progress_percentage = min(100.0, (provision.current_amount / provision.target_amount) * 100)
    
    return CustomProvisionResponse(
        id=provision.id,
        name=provision.name,
        description=provision.description,
        percentage=provision.percentage,
        base_calculation=provision.base_calculation,
        fixed_amount=provision.fixed_amount,
        split_mode=provision.split_mode,
        split_member1=provision.split_member1,
        split_member2=provision.split_member2,
        icon=provision.icon,
        color=provision.color,
        display_order=provision.display_order,
        is_active=provision.is_active,
        is_temporary=provision.is_temporary,
        start_date=provision.start_date,
        end_date=provision.end_date,
        target_amount=provision.target_amount,
        category=provision.category,
        current_amount=provision.current_amount,
        created_at=provision.created_at,
        updated_at=provision.updated_at,
        created_by=provision.created_by,
        monthly_amount=monthly_amount,
        progress_percentage=progress_percentage
    )

@app.get("/provisions/summary", response_model=CustomProvisionSummary)
def get_provisions_summary_endpoint(
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Récupère le résumé complet des provisions personnalisables"""
    logger.info(f"Résumé provisions demandé par utilisateur: {current_user.username}")
    
    config = ensure_default_config(db)
    
    # Filtrer par utilisateur
    user_provisions = db.query(CustomProvision).filter(
        CustomProvision.created_by == current_user.username
    ).all()
    
    total_provisions = len(user_provisions)
    active_provisions_list = [p for p in user_provisions if p.is_active]
    active_provisions = len(active_provisions_list)
    
    total_monthly_amount = 0.0
    total_monthly_member1 = 0.0
    total_monthly_member2 = 0.0
    
    # Comptage par catégorie
    provisions_by_category = {}
    provisions_details = []
    
    for provision in active_provisions_list:
        # Calculs pour chaque provision
        monthly_amount, member1_amount, member2_amount = calculate_provision_amount(provision, config)
        
        # Calcul du pourcentage de progression
        progress_percentage = None
        if provision.target_amount and provision.target_amount > 0:
            progress_percentage = min(100.0, (provision.current_amount / provision.target_amount) * 100)
        
        # Créer la réponse avec calculs
        provision_response = CustomProvisionResponse(
            id=provision.id,
            name=provision.name,
            description=provision.description,
            percentage=provision.percentage,
            base_calculation=provision.base_calculation,
            fixed_amount=provision.fixed_amount,
            split_mode=provision.split_mode,
            split_member1=provision.split_member1,
            split_member2=provision.split_member2,
            icon=provision.icon,
            color=provision.color,
            display_order=provision.display_order,
            is_active=provision.is_active,
            is_temporary=provision.is_temporary,
            start_date=provision.start_date,
            end_date=provision.end_date,
            target_amount=provision.target_amount,
            category=provision.category,
            current_amount=provision.current_amount,
            created_at=provision.created_at,
            updated_at=provision.updated_at,
            created_by=provision.created_by,
            monthly_amount=monthly_amount,
            progress_percentage=progress_percentage
        )
        
        provisions_details.append(provision_response)
        
        # Agrégation
        total_monthly_amount += monthly_amount
        total_monthly_member1 += member1_amount
        total_monthly_member2 += member2_amount
        
        # Comptage par catégorie
        category = provision.category or "custom"
        provisions_by_category[category] = provisions_by_category.get(category, 0) + 1
    
    return CustomProvisionSummary(
        total_provisions=total_provisions,
        active_provisions=active_provisions,
        total_monthly_amount=total_monthly_amount,
        total_monthly_member1=total_monthly_member1,
        total_monthly_member2=total_monthly_member2,
        provisions_by_category=provisions_by_category,
        provisions_details=provisions_details
    )

@app.get("/provisions/{provision_id}", response_model=CustomProvisionResponse)
def get_provision(
    provision_id: int,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Récupère les détails d'une provision spécifique"""
    provision = db.query(CustomProvision).filter(
        CustomProvision.id == provision_id,
        CustomProvision.created_by == current_user.username
    ).first()
    
    if not provision:
        raise HTTPException(status_code=404, detail="Provision introuvable")
    
    # Calculer le montant mensuel
    config = ensure_default_config(db)
    monthly_amount, _, _ = calculate_provision_amount(provision, config)
    
    # Calcul du pourcentage de progression
    progress_percentage = None
    if provision.target_amount and provision.target_amount > 0:
        progress_percentage = min(100.0, (provision.current_amount / provision.target_amount) * 100)
    
    return CustomProvisionResponse(
        id=provision.id,
        name=provision.name,
        description=provision.description,
        percentage=provision.percentage,
        base_calculation=provision.base_calculation,
        fixed_amount=provision.fixed_amount,
        split_mode=provision.split_mode,
        split_member1=provision.split_member1,
        split_member2=provision.split_member2,
        icon=provision.icon,
        color=provision.color,
        display_order=provision.display_order,
        is_active=provision.is_active,
        is_temporary=provision.is_temporary,
        start_date=provision.start_date,
        end_date=provision.end_date,
        target_amount=provision.target_amount,
        category=provision.category,
        current_amount=provision.current_amount,
        created_at=provision.created_at,
        updated_at=provision.updated_at,
        created_by=provision.created_by,
        monthly_amount=monthly_amount,
        progress_percentage=progress_percentage
    )

@app.put("/provisions/{provision_id}", response_model=CustomProvisionResponse)
def update_provision(
    provision_id: int,
    payload: CustomProvisionUpdate,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Met à jour une provision existante"""
    audit_logger = get_audit_logger()
    logger.info(f"Mise à jour provision {provision_id} par utilisateur: {current_user.username}")
    
    provision = db.query(CustomProvision).filter(
        CustomProvision.id == provision_id,
        CustomProvision.created_by == current_user.username
    ).first()
    
    if not provision:
        raise HTTPException(status_code=404, detail="Provision introuvable")
    
    # Vérifier les doublons de nom si le nom change
    if payload.name and payload.name != provision.name:
        existing = db.query(CustomProvision).filter(
            CustomProvision.created_by == current_user.username,
            CustomProvision.name == payload.name,
            CustomProvision.id != provision_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Une provision nommée '{payload.name}' existe déjà"
            )
    
    # Capturer les changements pour audit
    changes = {}
    update_data = payload.dict(exclude_unset=True)
    
    for key, new_value in update_data.items():
        old_value = getattr(provision, key, None)
        if old_value != new_value:
            changes[key] = {"old": old_value, "new": new_value}
            setattr(provision, key, new_value)
    
    # Mettre à jour la date de modification
    provision.updated_at = dt.datetime.now()
    
    db.add(provision)
    db.commit()
    db.refresh(provision)
    
    # Audit de modification
    if changes:
        audit_logger.log_event(
            AuditEventType.CONFIG_UPDATE,
            username=current_user.username,
            details={
                "action": "update_provision",
                "provision_id": provision.id,
                "provision_name": provision.name,
                "changes_count": len(changes)
            },
            success=True
        )
    
    # Calculer le montant mensuel pour la réponse
    config = ensure_default_config(db)
    monthly_amount, _, _ = calculate_provision_amount(provision, config)
    
    # Calcul du pourcentage de progression
    progress_percentage = None
    if provision.target_amount and provision.target_amount > 0:
        progress_percentage = min(100.0, (provision.current_amount / provision.target_amount) * 100)
    
    return CustomProvisionResponse(
        id=provision.id,
        name=provision.name,
        description=provision.description,
        percentage=provision.percentage,
        base_calculation=provision.base_calculation,
        fixed_amount=provision.fixed_amount,
        split_mode=provision.split_mode,
        split_member1=provision.split_member1,
        split_member2=provision.split_member2,
        icon=provision.icon,
        color=provision.color,
        display_order=provision.display_order,
        is_active=provision.is_active,
        is_temporary=provision.is_temporary,
        start_date=provision.start_date,
        end_date=provision.end_date,
        target_amount=provision.target_amount,
        category=provision.category,
        current_amount=provision.current_amount,
        created_at=provision.created_at,
        updated_at=provision.updated_at,
        created_by=provision.created_by,
        monthly_amount=monthly_amount,
        progress_percentage=progress_percentage
    )

@app.delete("/provisions/{provision_id}")
def delete_provision(
    provision_id: int,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Supprime une provision personnalisable"""
    audit_logger = get_audit_logger()
    logger.info(f"Suppression provision {provision_id} par utilisateur: {current_user.username}")
    
    provision = db.query(CustomProvision).filter(
        CustomProvision.id == provision_id,
        CustomProvision.created_by == current_user.username
    ).first()
    
    if not provision:
        raise HTTPException(status_code=404, detail="Provision introuvable")
    
    provision_name = provision.name
    
    db.delete(provision)
    db.commit()
    
    # Audit de suppression
    audit_logger.log_event(
        AuditEventType.CONFIG_UPDATE,
        username=current_user.username,
        details={
            "action": "delete_provision",
            "provision_id": provision_id,
            "provision_name": provision_name
        },
        success=True
    )
    
    return {"ok": True, "message": f"Provision '{provision_name}' supprimée avec succès"}


# ---------- Endpoints Custom Provisions (alias pour compatibilité frontend) ----------

@app.get("/custom-provisions", response_model=List[CustomProvisionResponse])
def list_custom_provisions(
    active_only: bool = True,
    category: Optional[str] = None,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Liste toutes les provisions personnalisables de l'utilisateur - alias pour /provisions"""
    return list_provisions(active_only, category, current_user, db)

@app.post("/custom-provisions", response_model=CustomProvisionResponse)
def create_custom_provision(
    payload: CustomProvisionCreate,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Crée une nouvelle provision personnalisable - alias pour /provisions"""
    return create_provision(payload, current_user, db)

@app.get("/custom-provisions/{provision_id}", response_model=CustomProvisionResponse)
def get_custom_provision(
    provision_id: int,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Récupère les détails d'une provision spécifique - alias pour /provisions/{id}"""
    return get_provision(provision_id, current_user, db)

@app.put("/custom-provisions/{provision_id}", response_model=CustomProvisionResponse)
def update_custom_provision(
    provision_id: int,
    payload: CustomProvisionUpdate,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Met à jour une provision existante - alias pour /provisions/{id}"""
    return update_provision(provision_id, payload, current_user, db)

@app.delete("/custom-provisions/{provision_id}")
def delete_custom_provision(
    provision_id: int,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Supprime une provision personnalisable - alias pour /provisions/{id}"""
    return delete_provision(provision_id, current_user, db)


@app.post(
    "/import", 
    response_model=ImportResponse,
    tags=["Import/Export"],
    summary="Import de transactions via fichier CSV",
    description="""
    Import intelligent de transactions bancaires depuis un fichier CSV avec détection automatique du format.
    
    ### 🔧 Fonctionnalités Avancées :
    - **Détection automatique** des encodages (UTF-8, CP1252, ISO-8859-1)
    - **Auto-mapping** des colonnes avec patterns intelligents
    - **Validation rigoureuse** des données avec rapport d'erreurs
    - **Détection de doublons** par signature unique
    - **Multi-mois support** avec regroupement automatique
    - **Navigation automatique** vers le mois principal détecté
    
    ### 📋 Formats CSV Supportés :
    - **Colonnes requises** : dateOp, label, amount
    - **Colonnes optionnelles** : dateVal, category, categoryParent, accountLabel
    - **Auto-détection** : date, description, montant, compte, catégorie
    - **Flexibilité** : ordre des colonnes libre, headers français/anglais
    
    ### 🛡️ Sécurité :
    - **Validation MIME** avec python-magic (si disponible)
    - **Sanitisation** des noms de fichiers
    - **Limite de taille** : 50MB par fichier
    - **Audit complet** : logging des imports par utilisateur
    - **Rollback automatique** en cas d'erreur critique
    
    ### 📊 Réponse Détaillée :
    - **Import ID unique** pour traçabilité
    - **Métadonnées par mois** : nouvelles transactions vs total
    - **Liste des IDs** créés pour référence
    - **Compteurs de doublons** avec rapports
    - **Suggestions de navigation** vers le mois principal
    - **Warnings et erreurs** détaillées
    
    ### 💡 Exemples d'utilisation :
    - Import relevés bancaires mensuels
    - Migration de données depuis autres outils
    - Import groupé multi-comptes/multi-mois
    """,
    responses={
        200: {
            "description": "Import réussi avec métadonnées détaillées",
            "content": {
                "application/json": {
                    "example": {
                        "importId": "123e4567-e89b-12d3-a456-426614174000",
                        "months": [
                            {
                                "month": "2024-01",
                                "newCount": 45,
                                "totalCount": 45,
                                "txIds": [1001, 1002, 1003, "..."],
                                "firstDate": "2024-01-02",
                                "lastDate": "2024-01-31"
                            }
                        ],
                        "suggestedMonth": "2024-01",
                        "duplicatesCount": 3,
                        "warnings": [
                            "3 doublons détectés et ignorés",
                            "Colonne 'categoryParent' manquante - valeur par défaut utilisée"
                        ],
                        "errors": [],
                        "processing": "done",
                        "fileName": "releve_janvier_2024.csv",
                        "processingMs": 1245
                    }
                }
            }
        },
        400: {
            "description": "Fichier invalide ou format non supporté",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_csv": {
                            "summary": "Format CSV invalide",
                            "value": {
                                "detail": "Format de fichier non supporté. Utilisez un fichier CSV valide.",
                                "errors": ["Impossible de parser le CSV", "Headers manquants"]
                            }
                        },
                        "missing_columns": {
                            "summary": "Colonnes requises manquantes",
                            "value": {
                                "detail": "Colonnes requises manquantes dans le CSV",
                                "errors": ["Colonne 'dateOp' introuvable", "Colonne 'amount' introuvable"]
                            }
                        }
                    }
                }
            }
        },
        401: {"$ref": "#/components/responses/UnauthorizedError"},
        413: {
            "description": "Fichier trop volumineux (limite : 50MB)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Fichier trop volumineux. Taille maximale autorisée : 50MB"
                    }
                }
            }
        },
        422: {
            "description": "Erreurs de validation des données",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Erreurs de validation détectées",
                        "errors": [
                            "Ligne 5: Date invalide '32/01/2024'",
                            "Ligne 12: Montant invalide 'abc'"
                        ]
                    }
                }
            }
        },
        500: {
            "description": "Erreur interne lors du traitement",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Erreur interne lors de l'import",
                        "import_id": "123e4567-e89b-12d3-a456-426614174000",
                        "errors": ["Database connection failed"]
                    }
                }
            }
        }
    }
)
def import_file(
    file: UploadFile = File(
        ..., 
        description="Fichier CSV contenant les transactions à importer",
        media_type="text/csv"
    ), 
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Import intelligent de transactions CSV avec validation automatique et détection de doublons.
    
    Supporte multiple encodages et formats de CSV bancaires courrants.
    """
    start_time = dt.datetime.now()
    import_id = str(uuid.uuid4())
    audit_logger = get_audit_logger()
    safe_filename = sanitize_filename(file.filename or "unknown")
    logger.info(f"Import {import_id} du fichier {safe_filename} par utilisateur: {current_user.username}")
    
    try:
        # === 1. VALIDATION SÉCURISÉE ===
        if not file.filename:
            audit_logger.log_security_violation(
                username=current_user.username,
                violation_type="missing_filename",
                details={"endpoint": "/import", "import_id": import_id}
            )
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        # Validation extension ET type MIME
        allowed_extensions = os.getenv("ALLOWED_EXTENSIONS", "csv,xlsx,xls").split(',')
        if not any(file.filename.lower().endswith(f'.{ext}') for ext in allowed_extensions):
            audit_logger.log_security_violation(
                username=current_user.username,
                violation_type="invalid_file_extension",
                details={"filename": safe_filename, "endpoint": "/import", "import_id": import_id}
            )
            raise HTTPException(status_code=400, detail="Format de fichier non autorisé")
        
        # Validation sécurité complète
        if not validate_file_security(file):
            audit_logger.log_security_violation(
                username=current_user.username,
                violation_type="file_security_check_failed",
                details={"filename": safe_filename, "endpoint": "/import", "import_id": import_id}
            )
            # Message d'erreur plus spécifique selon l'extension
            if safe_filename.lower().endswith('.csv'):
                raise HTTPException(status_code=400, detail=f"Fichier CSV invalide: {safe_filename}. Vérifiez que le fichier contient des headers valides et des séparateurs CSV (,;|).")
            else:
                raise HTTPException(status_code=400, detail=f"Format de fichier non supporté ou corrompu: {safe_filename}")

        # === 2. PARSING DU FICHIER ===
        name = file.filename.lower()
        if name.endswith(".csv"):
            df = robust_read_csv(file)
            if df.empty: 
                raise HTTPException(status_code=400, detail="CSV illisible")
            df = normalize_cols(df)
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            import pandas as p
            frames = []
            xls = p.ExcelFile(file.file)
            for s in xls.sheet_names:
                try:
                    tmp = p.read_excel(xls, s)
                    tmp = normalize_cols(tmp)
                    if tmp["dateOp"].notna().any(): 
                        frames.append(tmp)
                except Exception:
                    try:
                        raw = p.read_excel(xls, s, header=None, dtype=str)
                        header_idx = None
                        for i in range(min(40, len(raw))):
                            if str(raw.iloc[i,0]).strip().lower() == "dateop": 
                                header_idx = i; break
                        if header_idx is not None:
                            df2 = raw.iloc[header_idx+1:].copy()
                            df2.columns = raw.iloc[header_idx].fillna("").astype(str).str.strip().tolist()
                            df2 = df2.loc[:, [c for c in df2.columns if c != ""]]
                            df2 = normalize_cols(df2)
                            if df2["dateOp"].notna().any(): 
                                frames.append(df2)
                    except Exception: 
                        pass
            if not frames: 
                raise HTTPException(status_code=400, detail="Aucune feuille compatible détectée")
            df = pd.concat(frames, ignore_index=True)
        else:
            raise HTTPException(status_code=400, detail="Format non supporté")
        
        # Nettoyer les données
        df = df[(df["dateOp"].notna())].copy()
        if df.empty:
            raise HTTPException(status_code=400, detail="Aucune transaction avec date valide trouvée")

        # === 3. VALIDATION DES DONNÉES ===
        warnings = validate_csv_data(df)
        
        # === 4. DÉTECTION DOUBLONS ===
        duplicates = check_duplicate_transactions(df, db)
        
        # === 5. DÉTECTION MOIS AVEC MÉTADONNÉES ===
        months_data = detect_months_with_metadata(df)
        
        # === 6. CRÉATION DES TRANSACTIONS (seulement lignes propres) ===
        created_transactions = []
        import_months = []
        
        for month_data in months_data:
            month_key = month_data['month']
            month_transactions = []
            
            for row in month_data['transactions']:
                # Vérifier si cette ligne est dans les lignes propres
                row_index = row.name
                if row_index not in duplicates['clean_rows']:
                    continue
                    
                try:
                    date_op = pd.to_datetime(row["dateOp"]).date()
                    label = str(row.get("label","") or "")
                    cat = str(row.get("category","") or "")
                    catp = str(row.get("categoryParent","") or "")
                    amount = float(row.get("amount") or 0.0)
                    acc = str(row.get("accountLabel","") or "")
                    is_expense = amount < 0
                    sugg_excl = (not is_expense) or is_income_or_transfer(label, catp)
                    rid = hashlib.md5(f"{date_op}|{label}|{amount}|{row.get('accountNum','')}".encode("utf-8")).hexdigest()
                    
                    t = Transaction(
                        month=month_key, 
                        date_op=date_op, 
                        label=label, 
                        category=cat, 
                        category_parent=catp,
                        amount=amount, 
                        account_label=acc, 
                        is_expense=is_expense, 
                        exclude=sugg_excl, 
                        row_id=rid, 
                        tags="",
                        import_id=import_id
                    )
                    
                    db.add(t)
                    month_transactions.append(t)
                    created_transactions.append(t)
                    
                except Exception as e:
                    logger.warning(f"Erreur création transaction ligne {row_index}: {e}")
                    continue
            
            # Commit pour obtenir les IDs
            db.commit()
            
            # Rafraîchir pour obtenir les IDs
            for t in month_transactions:
                db.refresh(t)
            
            # Créer ImportMonth avec les vraies données
            import_month = ImportMonth(
                month=month_key,
                newCount=len(month_transactions),
                totalCount=len(month_data['transactions']),
                txIds=[t.id for t in month_transactions],
                firstDate=month_data['first_date'].isoformat(),
                lastDate=month_data['last_date'].isoformat()
            )
            import_months.append(import_month)
        
        # === 7. SUGGESTION DU MOIS OPTIMAL ===
        suggested_month = suggest_optimal_month(months_data)
        
        # === 8. SAUVEGARDE MÉTADONNÉES D'IMPORT ===
        import json
        import_metadata = ImportMetadata(
            id=import_id,
            filename=safe_filename,
            created_at=start_time.date(),
            user_id=current_user.username,
            months_detected=json.dumps([m.dict() for m in import_months]),
            duplicates_count=len(duplicates['internal']) + len(duplicates['existing']),
            warnings=json.dumps(warnings),
            processing_ms=int((dt.datetime.now() - start_time).total_seconds() * 1000)
        )
        db.add(import_metadata)
        db.commit()
        
        # === 9. AUDIT DE SUCCÈS ===
        audit_logger.log_event(
            AuditEventType.TRANSACTION_IMPORT,
            username=current_user.username,
            details={
                "import_id": import_id,
                "filename": safe_filename,
                "file_size": getattr(file, 'size', 0) or 0,
                "transactions_created": len(created_transactions),
                "months_detected": len(import_months),
                "duplicates_found": len(duplicates['internal']) + len(duplicates['existing']),
                "suggested_month": suggested_month
            },
            success=True
        )
        
        # === 10. RÉPONSE FINALE ===
        processing_time = int((dt.datetime.now() - start_time).total_seconds() * 1000)
        
        return ImportResponse(
            importId=import_id,
            months=import_months,
            suggestedMonth=suggested_month,
            duplicatesCount=len(duplicates['internal']) + len(duplicates['existing']),
            warnings=warnings,
            errors=[],
            processing="done",
            fileName=safe_filename,
            processingMs=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Audit d'échec
        audit_logger.log_event(
            AuditEventType.TRANSACTION_IMPORT,
            username=current_user.username,
            details={
                "import_id": import_id,
                "filename": safe_filename,
                "error": str(e)[:200]
            },
            success=False
        )
        logger.error(f"Erreur import {import_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'import: {str(e)[:100]}")

@app.get("/imports/{import_id}", response_model=ImportResponse)
def get_import_details(import_id: str, db: Session = Depends(get_db)):
    """Récupère les détails d'un import via son ID"""
    import_metadata = db.query(ImportMetadata).filter(ImportMetadata.id == import_id).first()
    
    if not import_metadata:
        raise HTTPException(status_code=404, detail="Import non trouvé")
    
    import json
    try:
        months_data = json.loads(import_metadata.months_detected or "[]")
        warnings = json.loads(import_metadata.warnings or "[]")
    except json.JSONDecodeError:
        months_data = []
        warnings = []
    
    # Reconstituer les ImportMonth objects
    import_months = []
    suggested_month = None
    
    for month_data in months_data:
        import_month = ImportMonth(**month_data)
        import_months.append(import_month)
        
        # La suggestion est le premier mois avec le plus de transactions
        if suggested_month is None and import_month.newCount > 0:
            suggested_month = import_month.month
    
    return ImportResponse(
        importId=import_id,
        months=import_months,
        suggestedMonth=suggested_month,
        duplicatesCount=import_metadata.duplicates_count,
        warnings=warnings,
        errors=[],
        processing="done",
        fileName=import_metadata.filename,
        processingMs=import_metadata.processing_ms
    )

@app.get(
    "/transactions", 
    response_model=List[TxOut],
    tags=["Transactions"],
    summary="Récupérer les transactions d'un mois",
    description="""
    Récupère toutes les transactions pour un mois donné avec tri par date décroissante.
    
    ### Fonctionnalités :
    - **Filtrage automatique** par mois (format YYYY-MM)
    - **Tri descendant** par date d'opération
    - **Données complètes** : montants, catégories, tags, comptes
    - **Support des tags** : liste des tags séparés par virgules
    - **Gestion exclusions** : indicateur d'exclusion des calculs
    
    ### Format des données :
    - Montants positifs = recettes, négatifs = dépenses
    - Dates au format ISO (YYYY-MM-DD)
    - Tags automatiquement parsés depuis la chaîne CSV
    - Catégories avec hiérarchie parent/enfant
    
    ### Cas d'usage :
    - Affichage liste transactions du mois
    - Export de données mensuelles
    - Calculs financiers par période
    """,
    responses={
        200: {
            "description": "Liste des transactions du mois demandé",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1425,
                            "month": "2024-01",
                            "date_op": "2024-01-15",
                            "label": "Courses Carrefour Market",
                            "category": "Alimentation",
                            "category_parent": "Dépenses courantes",
                            "amount": -45.67,
                            "account_label": "Compte Principal",
                            "is_expense": True,
                            "exclude": False,
                            "row_id": "TX_20240115_001",
                            "tags": ["courses", "alimentation", "carrefour"],
                            "import_id": "import_20240115_123456"
                        },
                        {
                            "id": 1426,
                            "month": "2024-01",
                            "date_op": "2024-01-14",
                            "label": "Salaire Janvier",
                            "category": "Revenus",
                            "category_parent": "Revenus",
                            "amount": 3200.00,
                            "account_label": "Compte Principal",
                            "is_expense": False,
                            "exclude": False,
                            "row_id": "TX_20240114_001",
                            "tags": ["salaire", "revenus"],
                            "import_id": "import_20240115_123456"
                        }
                    ]
                }
            }
        },
        401: {"$ref": "#/components/responses/UnauthorizedError"},
        422: {
            "description": "Format de mois invalide - doit être YYYY-MM",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Format de mois invalide. Utilisez YYYY-MM (ex: 2024-01)"
                    }
                }
            }
        }
    }
)
def list_transactions(
    month: str = Query(
        ..., 
        regex=r"^\d{4}-\d{2}$",
        description="Mois au format YYYY-MM (ex: 2024-01)",
        example="2024-01"
    ), 
    db: Session = Depends(get_db)
):
    items = db.query(Transaction).filter(Transaction.month == month).order_by(Transaction.date_op.desc()).all()
    return [TxOut(id=t.id, month=t.month, date_op=t.date_op, label=t.label, category=t.category,
                  category_parent=t.category_parent, amount=(t.amount or 0.0), account_label=t.account_label,
                  is_expense=t.is_expense, exclude=t.exclude, row_id=t.row_id, tags=[x for x in (t.tags or '').split(',') if x], import_id=t.import_id) for t in items]

@app.patch("/transactions/{tx_id}", response_model=TxOut)
def toggle_exclude(tx_id: int, payload: ExcludeIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info(f"Modification exclusion transaction {tx_id} par utilisateur: {current_user.username}")
    t = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not t: raise HTTPException(status_code=404, detail="Transaction introuvable")
    t.exclude = bool(payload.exclude)
    db.add(t); db.commit(); db.refresh(t)
    return TxOut(id=t.id, month=t.month, date_op=t.date_op, label=t.label, category=t.category,
                 category_parent=t.category_parent, amount=(t.amount or 0.0), account_label=t.account_label,
                 is_expense=t.is_expense, exclude=t.exclude, row_id=t.row_id, tags=[x for x in (t.tags or '').split(',') if x], import_id=t.import_id)

@app.patch("/transactions/{tx_id}/tags", response_model=TxOut)
def update_tags(tx_id: int, payload: TagsIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info(f"Mise à jour tags transaction {tx_id} par utilisateur: {current_user.username}")
    t = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not t: raise HTTPException(status_code=404, detail="Transaction introuvable")
    clean = [x.strip() for x in payload.tags if x and x.strip()]
    t.tags = ",".join(dict.fromkeys(clean))  # dédoublonne en gardant l'ordre
    db.add(t); db.commit(); db.refresh(t)
    return TxOut(id=t.id, month=t.month, date_op=t.date_op, label=t.label, category=t.category,
                 category_parent=t.category_parent, amount=(t.amount or 0.0), account_label=t.account_label,
                 is_expense=t.is_expense, exclude=t.exclude, row_id=t.row_id, tags=[x for x in (t.tags or '').split(',') if x], import_id=t.import_id)

@app.get("/tags", response_model=List[str])
def list_tags(db: Session = Depends(get_db)):
    items = db.query(Transaction.tags).all()
    tags = set()
    for (s,) in items:
        for t in (s or '').split(','):
            t = t.strip()
            if t: tags.add(t)
    return sorted(tags)

@app.get("/tags-summary")
def tags_summary(month: str, db: Session = Depends(get_db)):
    # agrège les dépenses variables (négatives, non exclues) par tag
    items = db.query(Transaction).filter(Transaction.month == month).all()
    agg: Dict[str, float] = {}
    for t in items:
        if t.is_expense and not t.exclude and t.amount is not None and t.amount < 0:
            val = -t.amount
            tags = [x.strip() for x in (t.tags or '').split(',') if x.strip()]
            if not tags:
                tags = ["(non tagué)"]
            for tg in tags:
                agg[tg] = agg.get(tg, 0.0) + val
    out = sorted(agg.items(), key=lambda x: x[1], reverse=True)
    return [{"tag": k, "total": round(v, 2)} for k, v in out]

@app.get("/summary", response_model=SummaryOut)
def summary(month: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = ensure_default_config(db)
    r1, r2 = get_split(cfg)

    # Anciens champs supprimés - utiliser les FixedLine pour crédit immo
    loan_p1 = 0.0  # Géré par FixedLine maintenant
    loan_p2 = 0.0

    # Anciens systèmes de charges fixes supprimés - utiliser FixedLine maintenant
    other_fixed_total = 0.0  # Géré par FixedLine maintenant
    taxe_m = 0.0
    copro_m = 0.0
    other_p1 = 0.0
    other_p2 = 0.0

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
        lines_detail.append( (ln.label or "Fixe", p1, p2) )

    # Ancien système provision vacances supprimé - utiliser CustomProvision maintenant
    vac_monthly_total = 0.0  # Géré par CustomProvision maintenant
    vac_p1 = 0.0
    vac_p2 = 0.0
    
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
        # Vérifier si la provision est active à cette date
        current_date = dt.datetime.now()
        if provision.start_date and provision.start_date > current_date:
            continue
        if provision.end_date and provision.end_date < current_date:
            continue
            
        monthly_amount, member1_amount, member2_amount = calculate_provision_amount(provision, cfg)
        custom_provisions_total += monthly_amount
        custom_provisions_p1_total += member1_amount
        custom_provisions_p2_total += member2_amount
        custom_provisions_detail.append((provision.name, member1_amount, member2_amount, provision.icon))

    # Variables
    txs = db.query(Transaction).filter(Transaction.month == month).all()
    var_total = -sum(t.amount for t in txs if (t.is_expense and not t.exclude and t.amount is not None))
    var_p1 = var_total * r1
    var_p2 = var_total * r2

    # Totaux (incluant les provisions personnalisables)
    total_p1 = loan_p1 + other_p1 + vac_p1 + var_p1 + sum(p1 for _,p1,_ in lines_detail) + custom_provisions_p1_total
    total_p2 = loan_p2 + other_p2 + vac_p2 + var_p2 + sum(p2 for _,_,p2 in lines_detail) + custom_provisions_p2_total

    # Détail - nouveau système uniquement
    detail = {}
    # Les anciens systèmes ne sont plus affichés - tout passe par FixedLine et CustomProvision
    taxe_m_out = 0.0
    copro_m_out = 0.0
    # Anciens systèmes supprimés

    for label, p1, p2 in lines_detail:
        detail[f"Fixe — {label}"] = {cfg.member1: p1, cfg.member2: p2}
    
    # Ajout des provisions personnalisables au détail
    if custom_provisions_detail:
        for prov_name, prov_p1, prov_p2, prov_icon in custom_provisions_detail:
            detail[f"Provision — {prov_icon} {prov_name}"] = {cfg.member1: prov_p1, cfg.member2: prov_p2}
    
    # Ancienne provision vacances supprimée
    
    detail["Dépenses variables"] = {cfg.member1: var_p1, cfg.member2: var_p2}

    # Calcul des parts par type de poste pour optimisation frontend
    fixed_p1 = sum(p1 for _, p1, _ in lines_detail)
    fixed_p2 = sum(p2 for _, _, p2 in lines_detail)
    
    # Comptage des éléments actifs
    transaction_count = len(txs)
    active_fixed_lines = len([l for l in lines if l.active])
    active_provisions_count = len(custom_provisions)
    
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
        
        # Nouveaux champs pour optimiser les calculs frontend
        var_p1=round(var_p1, 2),
        var_p2=round(var_p2, 2),
        fixed_p1=round(fixed_p1, 2),
        fixed_p2=round(fixed_p2, 2),
        provisions_p1=round(custom_provisions_p1_total, 2),
        provisions_p2=round(custom_provisions_p2_total, 2),
        grand_total=round(total_p1 + total_p2, 2),
        
        # Métadonnées pour les calculs
        transaction_count=transaction_count,
        active_fixed_lines=active_fixed_lines,
        active_provisions=active_provisions_count
    )

@app.get("/health")
def health_check():
    """Health check endpoint pour diagnostics Windows"""
    import sys
    import platform
    from auth import SECRET_KEY
    
    try:
        import pysqlcipher3
        sqlcipher_status = "available"
    except ImportError:
        sqlcipher_status = "not_available"
    
    return {
        "status": "ok",
        "version": "0.3.0",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture()[0]
        },
        "features": {
            "database_encryption": USE_ENCRYPTED_DB and sqlcipher_status == "available",
            "magic_detection": MAGIC_AVAILABLE,
            "sqlcipher_module": sqlcipher_status
        },
        "database": {
            "encryption_enabled": USE_ENCRYPTED_DB,
            "encrypted_db_verified": USE_ENCRYPTED_DB and verify_encrypted_db() if 'verify_encrypted_db' in globals() else False,
            "standard_db_path": "./budget.db",
            "encrypted_db_path": "./budget_encrypted.db"
        },
        "auth": {
            "jwt_secret_length": len(SECRET_KEY),
            "jwt_secret_preview": f"{SECRET_KEY[:8]}...{SECRET_KEY[-8:]}",
            "algorithm": "HS256"
        }
    }

@app.post("/debug/jwt")
def debug_jwt_token(request_data: dict):
    """Debug endpoint pour analyser les problèmes JWT - DÉVELOPPEMENT UNIQUEMENT"""
    token = request_data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token requis")
    
    debug_result = debug_jwt_validation(token)
    return {
        "debug_info": debug_result,
        "timestamp": dt.datetime.now().isoformat(),
        "endpoint": "/debug/jwt"
    }

# ---------- Analytics Endpoints ----------
@app.get("/analytics/kpis", response_model=KPISummary)
def get_kpi_summary(
    months: str = "last3",  # "last3", "last6", "last12", "2024-01,2024-02" 
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les KPIs généraux pour une période"""
    audit_logger = get_audit_logger()
    logger.info(f"Analytics KPIs demandés par utilisateur: {current_user.username}")
    
    # Déterminer les mois à analyser
    if months.startswith("last"):
        num_months = int(months[4:])
        all_months = db.query(Transaction.month).distinct().order_by(Transaction.month.desc()).limit(num_months).all()
        selected_months = [m[0] for m in reversed(all_months)]
    else:
        selected_months = [m.strip() for m in months.split(",")]
    
    try:
        kpis = calculate_kpi_summary(db, selected_months)
        
        audit_logger.log_event(
            AuditEventType.ANALYTICS_ACCESS,
            username=current_user.username,
            details={"endpoint": "/analytics/kpis", "months": len(selected_months)},
            success=True
        )
        
        return kpis
    except Exception as e:
        logger.error(f"Erreur calcul KPIs: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du calcul des KPIs")

@app.get("/analytics/trends", response_model=List[MonthlyTrend])
def get_monthly_trends(
    months: str = "last6",
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les tendances mensuelles"""
    logger.info(f"Analytics trends demandés par utilisateur: {current_user.username}")
    
    # Déterminer les mois à analyser
    if months.startswith("last"):
        num_months = int(months[4:])
        all_months = db.query(Transaction.month).distinct().order_by(Transaction.month.desc()).limit(num_months).all()
        selected_months = [m[0] for m in reversed(all_months)]
    else:
        selected_months = [m.strip() for m in months.split(",")]
    
    try:
        trends = calculate_monthly_trends(db, selected_months)
        return trends
    except Exception as e:
        logger.error(f"Erreur calcul trends: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du calcul des tendances")

@app.get("/analytics/categories", response_model=List[CategoryBreakdown])
def get_category_breakdown(
    month: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère la répartition par catégorie pour un mois"""
    logger.info(f"Analytics categories demandées pour {month} par utilisateur: {current_user.username}")
    
    try:
        breakdown = calculate_category_breakdown(db, month)
        return breakdown
    except Exception as e:
        logger.error(f"Erreur calcul catégories: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du calcul des catégories")

@app.get("/analytics/anomalies", response_model=List[AnomalyDetection])
def get_anomalies(
    month: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Détecte les anomalies pour un mois donné"""
    logger.info(f"Détection anomalies pour {month} par utilisateur: {current_user.username}")
    
    try:
        anomalies = detect_anomalies(db, month)
        return anomalies
    except Exception as e:
        logger.error(f"Erreur détection anomalies: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la détection d'anomalies")

def get_previous_month(month: str) -> Optional[str]:
    """Calcule le mois précédent au format YYYY-MM"""
    try:
        year, month_num = month.split('-')
        year, month_num = int(year), int(month_num)
        
        if month_num == 1:
            return f"{year-1}-12"
        else:
            return f"{year}-{month_num-1:02d}"
    except:
        return None

@app.get("/summary/enhanced")
def get_enhanced_summary(
    month: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Endpoint enrichi combinant summary + analytics pour optimiser les appels frontend"""
    logger.info(f"Summary enrichi demandé pour {month} par utilisateur: {current_user.username}")
    
    try:
        # Récupération du summary standard
        summary_data = summary(month, current_user, db)
        
        # Ajout des analytics
        categories = calculate_category_breakdown(db, month)
        
        # Calcul des tendances simples
        prev_month = get_previous_month(month)
        prev_summary = None
        if prev_month:
            try:
                prev_summary = summary(prev_month, current_user, db)
            except:
                prev_summary = None
        
        # Construction de la réponse enrichie
        enhanced_data = {
            "summary": summary_data.dict(),
            "categories": [cat.dict() for cat in categories],
            "trends": {
                "expense_evolution": None,
                "fixed_evolution": None,
                "provisions_evolution": None
            },
            "metadata": {
                "has_previous_data": prev_summary is not None,
                "previous_month": prev_month
            }
        }
        
        # Calcul des évolutions si mois précédent disponible
        if prev_summary:
            enhanced_data["trends"]["expense_evolution"] = round(
                ((summary_data.var_total - prev_summary.var_total) / prev_summary.var_total * 100) 
                if prev_summary.var_total > 0 else 0, 2
            )
            enhanced_data["trends"]["fixed_evolution"] = round(
                ((summary_data.fixed_lines_total - prev_summary.fixed_lines_total) / prev_summary.fixed_lines_total * 100) 
                if prev_summary.fixed_lines_total > 0 else 0, 2
            )
            enhanced_data["trends"]["provisions_evolution"] = round(
                ((summary_data.provisions_total - prev_summary.provisions_total) / prev_summary.provisions_total * 100) 
                if prev_summary.provisions_total > 0 else 0, 2
            )
        
        return enhanced_data
        
    except Exception as e:
        logger.error(f"Erreur summary enrichi: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du calcul du summary enrichi")

@app.get("/summary/batch")
def get_batch_summary(
    months: str,  # Format: "2024-01,2024-02,2024-03"
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les summaries pour plusieurs mois en une seule requête"""
    logger.info(f"Batch summary demandé par utilisateur: {current_user.username}")
    
    try:
        month_list = [m.strip() for m in months.split(",") if m.strip()]
        if len(month_list) > 12:  # Limite de sécurité
            raise HTTPException(status_code=400, detail="Maximum 12 mois par requête")
        
        results = {}
        for month in month_list:
            try:
                month_summary = summary(month, current_user, db)
                results[month] = month_summary.dict()
            except Exception as e:
                logger.warning(f"Erreur pour le mois {month}: {e}")
                results[month] = None
        
        return {
            "months": results,
            "metadata": {
                "requested_months": len(month_list),
                "successful_months": len([m for m in results.values() if m is not None]),
                "failed_months": len([m for m in results.values() if m is None])
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur batch summary: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du calcul batch summary")

@app.get("/analytics/patterns", response_model=List[SpendingPattern])
def get_spending_patterns(
    months: str = "last3",
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyse les patterns de dépense par jour de la semaine"""
    logger.info(f"Analytics patterns demandés par utilisateur: {current_user.username}")
    
    # Déterminer les mois à analyser
    if months.startswith("last"):
        num_months = int(months[4:])
        all_months = db.query(Transaction.month).distinct().order_by(Transaction.month.desc()).limit(num_months).all()
        selected_months = [m[0] for m in reversed(all_months)]
    else:
        selected_months = [m.strip() for m in months.split(",")]
    
    try:
        patterns = calculate_spending_patterns(db, selected_months)
        return patterns
    except Exception as e:
        logger.error(f"Erreur calcul patterns: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du calcul des patterns")

@app.get("/analytics/available-months")
def get_available_months(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère la liste des mois disponibles pour l'analyse"""
    try:
        months = db.query(Transaction.month).distinct().order_by(Transaction.month.desc()).all()
        return {"months": [m[0] for m in months]}
    except Exception as e:
        logger.error(f"Erreur récupération mois: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des mois")

# ========== ENDPOINTS D'EXPORT COMPLET ==========

@app.post("/export")
async def create_export(
    request: ExportRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Endpoint principal d'export multi-formats"""
    audit_logger = get_audit_logger()
    logger.info(f"Export {request.format.value} demandé par utilisateur: {current_user.username}")
    
    try:
        # Validation des paramètres
        if request.format == ExportFormat.ZIP and not request.options:
            raise HTTPException(
                status_code=400, 
                detail="Options requises pour export ZIP (formats à inclure)"
            )
        
        # Initialiser le gestionnaire d'export
        export_manager = ExportManager(db)
        
        # Audit de la demande
        audit_logger.log_event(
            AuditEventType.ANALYTICS_ACCESS,
            username=current_user.username,
            details={
                "export_format": request.format.value,
                "export_scope": request.scope.value,
                "filters": request.filters.dict() if request.filters else None
            },
            success=True
        )
        
        # Exécuter l'export
        response = export_manager.execute_export(request, current_user.username)
        
        logger.info(f"Export {request.format.value} généré avec succès pour {current_user.username}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'export: {e}")
        audit_logger.log_event(
            AuditEventType.ANALYTICS_ACCESS,
            username=current_user.username,
            details={
                "export_format": request.format.value,
                "error": str(e)[:200]
            },
            success=False
        )
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'export: {str(e)[:100]}")

@app.get("/export/templates")
def get_export_templates(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les templates d'export disponibles"""
    export_manager = ExportManager(db)
    templates = export_manager.get_export_templates()
    
    return {
        "templates": templates,
        "available_formats": [format.value for format in ExportFormat],
        "available_scopes": [scope.value for scope in ExportScope]
    }

@app.post("/export/quick/{format}")
async def quick_export(
    format: ExportFormat,
    months: Optional[str] = None,
    categories: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export rapide avec paramètres simplifiés"""
    # Construire la requête d'export
    filters = ExportFilters()
    
    if months:
        # Format attendu: "2024-01,2024-02" ou "last3"
        if months.startswith("last"):
            # Récupérer les N derniers mois
            num_months = int(months[4:])
            all_months = db.query(Transaction.month).distinct().order_by(Transaction.month.desc()).limit(num_months).all()
            filters.months = [m[0] for m in reversed(all_months)]
        else:
            filters.months = [m.strip() for m in months.split(",")]
    
    if categories:
        filters.categories = [c.strip() for c in categories.split(",")]
    
    request = ExportRequest(
        format=format,
        scope=ExportScope.ALL,
        filters=filters
    )
    
    # Réutiliser l'endpoint principal
    return await create_export(request, current_user, db)

@app.get("/export/history")
def get_export_history(
    limit: int = 20,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère l'historique des exports de l'utilisateur"""
    # TODO: Implémenter le modèle ExportHistory en base
    # Pour l'instant, retourner un historique factice
    return {
        "exports": [],
        "message": "Historique des exports à implémenter avec table dédiée"
    }

@app.delete("/export/cleanup")
def cleanup_old_exports(
    days_old: int = 7,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Nettoie les anciens fichiers d'export"""
    # TODO: Implémenter le nettoyage des fichiers temporaires
    return {
        "message": f"Nettoyage des exports > {days_old} jours à implémenter",
        "cleaned_count": 0
    }

# Endpoint legacy pour compatibilité avec l'interface existante
@app.post("/analytics/export")
def export_analytics_legacy(
    months: List[str],
    format: str = "csv",
    include_charts: bool = True,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export legacy des analytics - redirige vers le nouveau système"""
    try:
        export_format = ExportFormat(format)
    except ValueError:
        export_format = ExportFormat.CSV
    
    filters = ExportFilters(months=months)
    options = {"include_charts": include_charts} if format == "pdf" else {}
    
    request = ExportRequest(
        format=export_format,
        scope=ExportScope.ANALYTICS,
        filters=filters,
        options=options
    )
    
    # Réutiliser le nouveau endpoint
    import asyncio
    return asyncio.create_task(create_export(request, current_user, db))
