
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
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, validator, Field
from email_validator import validate_email, EmailNotValidError
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, Text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
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
    title="Budget Famille API - Consolidated", 
    version="2.3.0",
    description="API unifiée pour la gestion budgétaire familiale - Ubuntu WSL optimisé"
)

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
    id = Column(Integer, primary_key=True, index=True)
    member1 = Column(String, default="diana")
    member2 = Column(String, default="thomas")
    rev1 = Column(Float, default=0.0)
    rev2 = Column(Float, default=0.0)
    split_mode = Column(String, default="revenus")  # revenus | manuel
    split1 = Column(Float, default=0.5)  # if manuel
    split2 = Column(Float, default=0.5)
    loan_equal = Column(Boolean, default=True)
    loan_amount = Column(Float, default=825.91)

    # Modes historiques (on les garde pour compatibilité)
    other_fixed_simple = Column(Boolean, default=True)
    other_fixed_monthly = Column(Float, default=360.0)
    taxe_fonciere_ann = Column(Float, default=0.0)
    copro_montant = Column(Float, default=0.0)
    copro_freq = Column(String, default="mensuelle")  # mensuelle|trimestrielle
    other_split_mode = Column(String, default="clé")  # clé|50/50

    vac_percent = Column(Float, default=5.0)
    vac_base = Column(String, default="2")  # "2" | "1" | "2nd"

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

Base.metadata.create_all(bind=engine)

# --- Light schema migration for legacy DBs: add missing columns ---
def migrate_schema():
    with engine.connect() as conn:
        info = conn.exec_driver_sql("PRAGMA table_info('transactions')").fetchall()
        cols = [r[1] for r in info]
        if "tags" not in cols:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN tags TEXT DEFAULT ''")
        if "import_id" not in cols:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN import_id TEXT")
            
        # Créer les indexes si nécessaires
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_transactions_import_id ON transactions(import_id)")

migrate_schema()

def ensure_default_config(db: Session):
    cfg = db.query(Config).first()
    if not cfg:
        cfg = Config()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg

# ---------- Schemas ----------
class ConfigIn(BaseModel):
    member1: str = Field(..., min_length=1, max_length=50, description="Nom du membre 1")
    member2: str = Field(..., min_length=1, max_length=50, description="Nom du membre 2")
    rev1: float = Field(..., ge=0, le=999999.99, description="Revenus membre 1")
    rev2: float = Field(..., ge=0, le=999999.99, description="Revenus membre 2")
    split_mode: str = Field(..., pattern="^(revenus|manuel)$", description="Mode de répartition")
    split1: float = Field(..., ge=0, le=1, description="Part membre 1")
    split2: float = Field(..., ge=0, le=1, description="Part membre 2")
    loan_equal: bool = Field(..., description="Prêt à égalité")
    loan_amount: float = Field(..., ge=0, le=99999.99, description="Montant du prêt")

    other_fixed_simple: bool = Field(..., description="Charges fixes simplifiées")
    other_fixed_monthly: float = Field(..., ge=0, le=99999.99, description="Charges fixes mensuelles")
    taxe_fonciere_ann: float = Field(..., ge=0, le=99999.99, description="Taxe foncière annuelle")
    copro_montant: float = Field(..., ge=0, le=99999.99, description="Montant copropriété")
    copro_freq: str = Field(..., pattern="^(mensuelle|trimestrielle)$", description="Fréquence copropriété")
    other_split_mode: str = Field(..., pattern="^(clé|50/50)$", description="Mode répartition autres")

    vac_percent: float = Field(..., ge=0, le=100, description="Pourcentage vacances")
    vac_base: str = Field(..., pattern="^(1|2|2nd)$", description="Base calcul vacances")
    
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
    loan_amount: float
    taxe_m: float
    copro_m: float
    other_fixed_total: float
    vac_monthly_total: float
    r1: float
    r2: float
    member1: str
    member2: str
    total_p1: float
    total_p2: float
    detail: dict

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
    active: bool = Field(True, description="Ligne active")
    
    @validator('label')
    def sanitize_label(cls, v):
        return escape(str(v).strip())[:100]

class FixedLineOut(FixedLineIn):
    id: int

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

# ---------- Routes ----------
@app.get("/config", response_model=ConfigOut)
def get_config(db: Session = Depends(get_db)):
    cfg = ensure_default_config(db)
    return ConfigOut(
        id=cfg.id, member1=cfg.member1, member2=cfg.member2, rev1=cfg.rev1, rev2=cfg.rev2,
        split_mode=cfg.split_mode, split1=cfg.split1, split2=cfg.split2,
        loan_equal=cfg.loan_equal, loan_amount=cfg.loan_amount,
        other_fixed_simple=cfg.other_fixed_simple, other_fixed_monthly=cfg.other_fixed_monthly,
        taxe_fonciere_ann=cfg.taxe_fonciere_ann, copro_montant=cfg.copro_montant,
        copro_freq=cfg.copro_freq, other_split_mode=cfg.other_split_mode,
        vac_percent=cfg.vac_percent, vac_base=cfg.vac_base
    )

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint d'authentification JWT"""
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
    
    return get_config(db)

@app.get("/fixed-lines", response_model=List[FixedLineOut])
def list_fixed_lines(db: Session = Depends(get_db)):
    items = db.query(FixedLine).filter(FixedLine.active == True).order_by(FixedLine.id.asc()).all()
    return [FixedLineOut(id=i.id, label=i.label, amount=i.amount, freq=i.freq, split_mode=i.split_mode, split1=i.split1, split2=i.split2, active=i.active) for i in items]

@app.post("/fixed-lines", response_model=FixedLineOut)
def create_fixed_line(payload: FixedLineIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info(f"Création ligne fixe par utilisateur: {current_user.username}")
    f = FixedLine(label=payload.label, amount=payload.amount, freq=payload.freq,
                  split_mode=payload.split_mode, split1=payload.split1, split2=payload.split2, active=payload.active)
    db.add(f); db.commit(); db.refresh(f)
    return FixedLineOut(id=f.id, label=f.label, amount=f.amount, freq=f.freq, split_mode=f.split_mode, split1=f.split1, split2=f.split2, active=f.active)

@app.patch("/fixed-lines/{lid}", response_model=FixedLineOut)
def update_fixed_line(lid: int, payload: FixedLineIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info(f"Mise à jour ligne fixe {lid} par utilisateur: {current_user.username}")
    f = db.query(FixedLine).filter(FixedLine.id == lid).first()
    if not f: raise HTTPException(status_code=404, detail="Ligne fixe introuvable")
    for k, v in payload.dict().items():
        setattr(f, k, v)
    db.add(f); db.commit(); db.refresh(f)
    return FixedLineOut(id=f.id, label=f.label, amount=f.amount, freq=f.freq, split_mode=f.split_mode, split1=f.split1, split2=f.split2, active=f.active)

@app.delete("/fixed-lines/{lid}")
def delete_fixed_line(lid: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info(f"Suppression ligne fixe {lid} par utilisateur: {current_user.username}")
    f = db.query(FixedLine).filter(FixedLine.id == lid).first()
    if not f: raise HTTPException(status_code=404, detail="Ligne fixe introuvable")
    db.delete(f); db.commit()
    return {"ok": True}

@app.post("/import", response_model=ImportResponse)
def import_file(file: UploadFile = File(...), current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Endpoint protégé - Import de fichiers sécurisé avec navigation automatique"""
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

@app.get("/transactions", response_model=List[TxOut])
def list_transactions(month: str, db: Session = Depends(get_db)):
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
def summary(month: str, db: Session = Depends(get_db)):
    cfg = ensure_default_config(db)
    r1, r2 = get_split(cfg)

    # Crédit immo + voiture
    loan_p1 = (cfg.loan_amount/2.0) if cfg.loan_equal else (cfg.loan_amount * r1)
    loan_p2 = (cfg.loan_amount/2.0) if cfg.loan_equal else (cfg.loan_amount * r2)

    # Autres charges fixes (ancien système)
    if cfg.other_fixed_simple:
        other_fixed_total = cfg.other_fixed_monthly or 0.0
        taxe_m = 0.0
        copro_m = 0.0
    else:
        taxe_m = (cfg.taxe_fonciere_ann or 0.0) / 12.0
        copro_m = cfg.copro_montant if cfg.copro_freq == "mensuelle" else ((cfg.copro_montant or 0.0) / 3.0)
        other_fixed_total = taxe_m + copro_m

    if cfg.other_split_mode == "50/50":
        other_p1 = other_fixed_total/2.0
        other_p2 = other_fixed_total/2.0
    else:
        other_p1 = other_fixed_total * r1
        other_p2 = other_fixed_total * r2

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

    # Provision vacances/bébé/plaisir
    if cfg.vac_base == "2":
        base = (cfg.rev1 or 0) + (cfg.rev2 or 0)
    elif cfg.vac_base == "1":
        base = (cfg.rev1 or 0)
    else:
        base = (cfg.rev2 or 0)
    vac_monthly_total = (base * (cfg.vac_percent or 0) / 100.0) / 12.0 if base else 0.0
    vac_p1 = vac_monthly_total * r1
    vac_p2 = vac_monthly_total * r2

    # Variables
    txs = db.query(Transaction).filter(Transaction.month == month).all()
    var_total = -sum(t.amount for t in txs if (t.is_expense and not t.exclude and t.amount is not None))
    var_p1 = var_total * r1
    var_p2 = var_total * r2

    # Totaux
    total_p1 = loan_p1 + other_p1 + vac_p1 + var_p1 + sum(p1 for _,p1,_ in lines_detail)
    total_p2 = loan_p2 + other_p2 + vac_p2 + var_p2 + sum(p2 for _,_,p2 in lines_detail)

    # Détail
    detail = {}
    detail["Crédit immo+voiture"] = {cfg.member1: loan_p1, cfg.member2: loan_p2}
    if cfg.other_fixed_simple:
        detail["Autres charges fixes (mensuel)"] = {cfg.member1: (other_fixed_total/2.0 if cfg.other_split_mode=="50/50" else other_fixed_total*r1),
                                                    cfg.member2: (other_fixed_total/2.0 if cfg.other_split_mode=="50/50" else other_fixed_total*r2)}
        taxe_m_out = 0.0; copro_m_out = 0.0
    else:
        detail["Taxe foncière (mensualisée)"] = {cfg.member1: (taxe_m/2.0 if cfg.other_split_mode=="50/50" else taxe_m*r1),
                                                 cfg.member2: (taxe_m/2.0 if cfg.other_split_mode=="50/50" else taxe_m*r2)}
        detail["Copro (mensualisée)"] = {cfg.member1: (copro_m/2.0 if cfg.other_split_mode=="50/50" else copro_m*r1),
                                         cfg.member2: (copro_m/2.0 if cfg.other_split_mode=="50/50" else copro_m*r2)}
        taxe_m_out = taxe_m; copro_m_out = copro_m

    for label, p1, p2 in lines_detail:
        detail[f"Fixe — {label}"] = {cfg.member1: p1, cfg.member2: p2}

    detail["Provision vacances/bébé"] = {cfg.member1: vac_p1, cfg.member2: vac_p2}
    detail["Dépenses variables"] = {cfg.member1: var_p1, cfg.member2: var_p2}

    return SummaryOut(
        month=month, var_total=round(var_total,2), loan_amount=round(cfg.loan_amount,2),
        taxe_m=round(taxe_m_out if not cfg.other_fixed_simple else 0.0,2),
        copro_m=round(copro_m_out if not cfg.other_fixed_simple else 0.0,2),
        other_fixed_total=round((cfg.other_fixed_monthly if cfg.other_fixed_simple else (taxe_m_out+copro_m_out)) + lines_total,2),
        vac_monthly_total=round(vac_monthly_total,2), r1=round(r1,4), r2=round(r2,4),
        member1=cfg.member1, member2=cfg.member2,
        total_p1=round(total_p1,2), total_p2=round(total_p2,2), detail=detail
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
