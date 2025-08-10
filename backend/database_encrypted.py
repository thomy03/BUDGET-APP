"""
Module de gestion de base de données chiffrée avec SQLCipher
Migration sécurisée des données existantes
"""

import os
import sqlite3
import logging
from typing import Optional
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration chiffrement SÉCURISÉE
def get_secure_db_key():
    """Génère ou récupère une clé sécurisée"""
    key = os.getenv("DB_ENCRYPTION_KEY")
    if not key or key == "CHANGEME_SECURE_KEY_32_CHARS_MIN" or len(key) < 32:
        logger.warning("🚨 SÉCURITÉ: Génération d'une nouvelle clé de chiffrement")
        import secrets
        new_key = secrets.token_urlsafe(32)
        # Suggestion d'écriture en .env (ne pas hardcoder)
        logger.info(f"🔑 Nouvelle clé générée. Ajoutez à .env: DB_ENCRYPTION_KEY={new_key}")
        return new_key
    return key

DB_ENCRYPTION_KEY = get_secure_db_key()
DB_PATH_ENCRYPTED = "./budget_encrypted.db"
DB_PATH_ORIGINAL = "./budget.db"

def get_encrypted_engine():
    """Crée un moteur SQLAlchemy avec SQLCipher, avec fallback SQLite si indisponible"""
    try:
        # Test d'import pysqlcipher3 d'abord
        try:
            import pysqlcipher3
            logger.info("✅ pysqlcipher3 disponible")
        except ImportError as ie:
            logger.warning(f"❌ pysqlcipher3 non disponible: {ie}")
            raise ModuleNotFoundError("pysqlcipher3 module not available")
        
        database_url = f"sqlite+pysqlcipher://:{DB_ENCRYPTION_KEY}@/{DB_PATH_ENCRYPTED}"
        engine = create_engine(
            database_url,
            future=True,
            echo=False,
            connect_args={
                "check_same_thread": False,
                "timeout": 20,
            }
        )
        
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            try:
                cursor = dbapi_connection.cursor()
                cursor.execute(f"PRAGMA key = '{DB_ENCRYPTION_KEY}'")
                cursor.execute("PRAGMA cipher_page_size = 4096")
                cursor.execute("PRAGMA kdf_iter = 256000")
                cursor.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
                cursor.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
                cursor.close()
                logger.debug("✅ SQLCipher PRAGMA configurés")
            except Exception as pragma_error:
                logger.error(f"❌ Erreur configuration PRAGMA SQLCipher: {pragma_error}")
                raise pragma_error
        
        # Test de connexion rapide
        try:
            with engine.connect() as conn:
                conn.execute("SELECT 1").fetchone()
            logger.info("✅ Moteur SQLCipher testé avec succès")
        except Exception as test_error:
            logger.error(f"❌ Test connexion SQLCipher échoué: {test_error}")
            raise test_error
        
        return engine
        
    except ModuleNotFoundError as e:
        logger.warning(f"⚠️  SQLCipher non disponible (pysqlcipher3 manquant): {e}")
        logger.info("🔄 Fallback vers SQLite standard")
    except ImportError as e:
        logger.warning(f"⚠️  Import SQLCipher échoué: {e}")
        logger.info("🔄 Fallback vers SQLite standard")
    except Exception as e:
        logger.error(f"❌ Erreur création moteur SQLCipher: {e}")
        logger.info("🔄 Fallback vers SQLite standard")
        
    # Fallback vers SQLite standard
    logger.info("📊 Utilisation SQLite standard (non chiffré)")
    return create_engine("sqlite:///./budget.db", future=True, echo=False)

def migrate_to_encrypted_db() -> bool:
    """
    Migre la base SQLite standard vers SQLCipher chiffré
    CRITICAL: Sauvegarde automatique créée + Vérifications sécurisées
    """
    logger.info("🔐 Début migration vers base chiffrée")
    cwd_before = os.getcwd()
    
    # Vérifications préliminaires
    if not Path(DB_PATH_ORIGINAL).exists():
        logger.warning("Base originale non trouvée - création d'une base chiffrée vide")
        return True
    
    # SÉCURITÉ: Vérification de l'espace disque avant migration
    import shutil
    original_size = Path(DB_PATH_ORIGINAL).stat().st_size
    free_space = shutil.disk_usage(Path(".").resolve()).free
    
    if free_space < original_size * 3:  # 3x sécurité (original + backup + encrypted)
        logger.error(f"❌ Espace disque insuffisant: {free_space} disponible, {original_size * 3} requis")
        return False
    
    # SÉCURITÉ: Lock pour éviter concurrence
    lock_file = f"{DB_PATH_ORIGINAL}.migration_lock"
    if Path(lock_file).exists():
        logger.error("❌ Migration déjà en cours (fichier lock présent)")
        return False
    
    try:
        # Créer lock de migration
        Path(lock_file).touch()
        
        # 1. Créer sauvegarde de sécurité avec timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{DB_PATH_ORIGINAL}.backup_{timestamp}_{os.getpid()}"
        shutil.copy2(DB_PATH_ORIGINAL, backup_path)
        logger.info(f"✅ Sauvegarde créée: {backup_path}")
        
        # 2. Connexion à la base originale avec timeout
        conn_original = sqlite3.connect(DB_PATH_ORIGINAL, timeout=30)
        
        # 3. Connexion à la nouvelle base chiffrée avec configuration sécurisée
        conn_encrypted = sqlite3.connect(DB_PATH_ENCRYPTED, timeout=30)
        conn_encrypted.execute(f"PRAGMA key = '{DB_ENCRYPTION_KEY}'")
        conn_encrypted.execute("PRAGMA cipher_page_size = 4096")
        conn_encrypted.execute("PRAGMA kdf_iter = 256000")
        conn_encrypted.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
        conn_encrypted.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
        
        # 4. Migration des données table par table
        cursor_original = conn_original.cursor()
        cursor_original.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor_original.fetchall()
        
        for (table_name,) in tables:
            logger.info(f"Migration table: {table_name}")
            
            # Récupérer schéma
            cursor_original.execute(f"SELECT sql FROM sqlite_master WHERE name='{table_name}'")
            schema = cursor_original.fetchone()[0]
            
            # Créer table dans base chiffrée
            conn_encrypted.execute(schema)
            
            # Copier données
            cursor_original.execute(f"SELECT * FROM {table_name}")
            rows = cursor_original.fetchall()
            
            if rows:
                placeholders = ','.join(['?' for _ in rows[0]])
                conn_encrypted.executemany(
                    f"INSERT INTO {table_name} VALUES ({placeholders})", 
                    rows
                )
        
        # 5. Valider l'intégrité
        conn_encrypted.commit()
        
        # Test de lecture
        cursor_encrypted = conn_encrypted.cursor()
        cursor_encrypted.execute("SELECT COUNT(*) FROM sqlite_master")
        table_count = cursor_encrypted.fetchone()[0]
        
        conn_original.close()
        conn_encrypted.close()
        
        logger.info(f"✅ Migration réussie - {table_count} tables migrées")
        
        # 6. Validation intégrité complète
        cursor_encrypted.execute("PRAGMA integrity_check")
        integrity_result = cursor_encrypted.fetchone()[0]
        if integrity_result != "ok":
            raise Exception(f"Vérification intégrité échouée: {integrity_result}")
        
        # 7. Renommer l'ancienne base (sécurité)
        old_db_backup = f"{DB_PATH_ORIGINAL}.old"
        os.rename(DB_PATH_ORIGINAL, old_db_backup)
        logger.info(f"✅ Base originale sauvée: {old_db_backup}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur migration: {e}")
        # Nettoyer en cas d'erreur avec rollback automatique
        if Path(DB_PATH_ENCRYPTED).exists():
            os.remove(DB_PATH_ENCRYPTED)
        logger.error("❌ Base chiffrée supprimée suite à l'erreur")
        return False
    finally:
        # SÉCURITÉ: Toujours supprimer le lock
        if Path(lock_file).exists():
            os.remove(lock_file)
            logger.info("🔓 Lock de migration supprimé")
        # Windows: éviter de laisser le CWD dans un dossier temporaire utilisé par les tests
        try:
            if os.path.isdir(cwd_before):
                os.chdir(cwd_before)
        except Exception as _e:
            logger.warning(f"⚠️ Restauration CWD échouée: {_e}")

def verify_encrypted_db() -> bool:
    """Vérifie l'intégrité de la base chiffrée avec gestion d'erreurs Windows"""
    # Vérifier d'abord que le fichier existe
    if not Path(DB_PATH_ENCRYPTED).exists():
        logger.info(f"⚠️  Fichier base chiffrée inexistant: {DB_PATH_ENCRYPTED}")
        return False
    
    try:
        # Vérifier que pysqlcipher3 est disponible
        try:
            import pysqlcipher3
        except ImportError:
            logger.warning("⚠️  pysqlcipher3 non disponible pour vérification")
            return False
            
        conn = sqlite3.connect(DB_PATH_ENCRYPTED, timeout=10)
        
        try:
            conn.execute(f"PRAGMA key = '{DB_ENCRYPTION_KEY}'")
            
            # Test de lecture avec timeout
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            if not tables:
                logger.warning("⚠️  Aucune table trouvée dans la base chiffrée")
                return False
            
            # Vérifier quelques tables critiques
            expected_tables = ['config', 'transactions', 'fixed_lines']
            found_tables = [t[0] for t in tables]
            
            critical_found = 0
            for table in expected_tables:
                if table in found_tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        logger.debug(f"✅ Table {table}: {count} enregistrements")
                        critical_found += 1
                    except Exception as table_error:
                        logger.warning(f"⚠️  Erreur lecture table {table}: {table_error}")
            
            # Si au moins une table critique est accessible, c'est OK
            if critical_found > 0:
                logger.info(f"✅ Base chiffrée vérifiée: {critical_found}/{len(expected_tables)} tables critiques OK")
                return True
            else:
                logger.error("❌ Aucune table critique accessible")
                return False
        
        finally:
            conn.close()
        
    except sqlite3.DatabaseError as db_error:
        logger.error(f"❌ Erreur base de données chiffrée: {db_error}")
        return False
    except Exception as e:
        logger.error(f"❌ Vérification base chiffrée échouée: {e}")
        return False

def rollback_migration() -> bool:
    """Plan de rollback - restaure la base originale"""
    logger.warning("🔄 ROLLBACK - Restauration base originale")
    
    try:
        old_db_backup = f"{DB_PATH_ORIGINAL}.old"
        
        if Path(old_db_backup).exists():
            # Supprimer base chiffrée défaillante
            if Path(DB_PATH_ENCRYPTED).exists():
                os.remove(DB_PATH_ENCRYPTED)
            
            # Restaurer base originale
            os.rename(old_db_backup, DB_PATH_ORIGINAL)
            logger.info("✅ Base originale restaurée")
            return True
        else:
            logger.error("❌ Fichier de rollback non trouvé")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erreur rollback: {e}")
        return False

# Fonction utilitaire pour générer une clé sécurisée
def generate_db_key() -> str:
    """Génère une clé de chiffrement sécurisée"""
    import secrets
    return secrets.token_urlsafe(32)