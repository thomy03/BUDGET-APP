"""
Tests de régression pour vérifier les correctifs critiques
Bug #1: Validation upload sécurisée
Bug #2: Persistance base données
"""

import os
import tempfile
import pytest
import sqlite3
from unittest.mock import Mock, patch
from pathlib import Path

# Import des modules à tester
from app import validate_file_security, robust_read_csv, sanitize_filename
from database_encrypted import get_secure_db_key, migrate_to_encrypted_db, verify_encrypted_db
from auth import get_secure_jwt_key
from fastapi.testclient import TestClient
from fastapi import UploadFile
import io

def test_file_security_validation():
    """Test de validation sécurisée des fichiers uploadés"""
    
    # Test 1: Fichier CSV valide
    valid_csv = b"dateOp,amount,label\n2024-01-01,100.50,Test"
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.csv"
    mock_file.file = io.BytesIO(valid_csv)
    
    with patch('magic.from_buffer') as mock_magic:
        mock_magic.return_value = 'text/csv'
        result = validate_file_security(mock_file)
        assert result == True, "Fichier CSV valide devrait être accepté"
    
    # Test 2: Extension non autorisée
    mock_file.filename = "malicious.exe"
    mock_file.file = io.BytesIO(b"malicious content")
    result = validate_file_security(mock_file)
    assert result == False, "Fichier .exe devrait être rejeté"
    
    # Test 3: Fichier trop volumineux
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB
    mock_file.filename = "large.csv"
    mock_file.file = io.BytesIO(large_content)
    result = validate_file_security(mock_file)
    assert result == False, "Fichier > 10MB devrait être rejeté"
    
    # Test 4: MIME type suspect
    mock_file.filename = "fake.csv"
    mock_file.file = io.BytesIO(b"dateOp,test\nPK\x03\x04")  # Signature ZIP déguisée
    with patch('magic.from_buffer') as mock_magic:
        mock_magic.return_value = 'application/x-executable'
        result = validate_file_security(mock_file)
        assert result == False, "MIME type executabe devrait être rejeté"

def test_malicious_content_detection():
    """Test de détection de contenu malicieux dans les CSV"""
    
    # Test contenu avec script malicieux
    malicious_csv = b"dateOp,label\n2024-01-01,<script>alert('xss')</script>"
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "malicious.csv"
    mock_file.file = io.BytesIO(malicious_csv)
    
    with patch('app.validate_file_security', return_value=True):
        with pytest.raises(Exception) as exc_info:
            robust_read_csv(mock_file)
        assert "suspect" in str(exc_info.value).lower(), "Contenu malicieux devrait être détecté"

def test_filename_sanitization():
    """Test de sanitisation des noms de fichiers"""
    
    # Test traversée de répertoire
    dangerous_filename = "../../../etc/passwd"
    safe_name = sanitize_filename(dangerous_filename)
    assert ".." not in safe_name, "Traversée de répertoire devrait être bloquée"
    assert "/" not in safe_name, "Caractères slash devrait être supprimés"
    
    # Test fichiers système Windows
    system_filename = "CON.csv"
    safe_name = sanitize_filename(system_filename)
    assert safe_name != "CON.csv", "Nom de fichier système devrait être modifié"

def test_database_encryption_keys():
    """Test de génération automatique des clés sécurisées"""
    
    # Test clé DB
    with patch.dict(os.environ, {}, clear=True):
        key = get_secure_db_key()
        assert len(key) >= 32, "Clé DB devrait faire au moins 32 caractères"
        assert key != "CHANGEME_SECURE_KEY_32_CHARS_MIN", "Clé par défaut devrait être remplacée"
    
    # Test clé JWT
    with patch.dict(os.environ, {}, clear=True):
        key = get_secure_jwt_key()
        assert len(key) >= 32, "Clé JWT devrait faire au moins 32 caractères"
        assert key != "CHANGEME_IN_PRODUCTION_URGENT", "Clé par défaut devrait être remplacée"

def test_database_migration_safety():
    """Test des vérifications de sécurité lors de la migration"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        # Créer une base de test
        test_db = "budget.db"
        conn = sqlite3.connect(test_db)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test (name) VALUES ('test_data')")
        conn.commit()
        conn.close()
        
        # Test avec espace disque insuffisant simulé
        with patch('shutil.disk_usage') as mock_disk:
            mock_disk.return_value = Mock(free=1000)  # Espace très limité
            result = migrate_to_encrypted_db()
            assert result == False, "Migration devrait échouer avec espace insuffisant"
        
        # Test lock de concurrence
        lock_file = f"{test_db}.migration_lock"
        Path(lock_file).touch()
        result = migrate_to_encrypted_db()
        assert result == False, "Migration devrait échouer si lock présent"
        
        # Nettoyer
        os.remove(lock_file)

def test_encryption_key_environment():
    """Test configuration sécurisée depuis variables d'environnement"""
    
    secure_key = "mon_super_secret_key_de_32_caracteres_min"
    
    # Test avec clé sécurisée en environnement
    with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": secure_key}):
        key = get_secure_db_key()
        assert key == secure_key, "Clé d'environnement sécurisée devrait être utilisée"
    
    # Test avec clé trop courte
    with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": "short"}):
        key = get_secure_db_key()
        assert len(key) >= 32, "Clé trop courte devrait être remplacée"

if __name__ == "__main__":
    # Exécution rapide des tests
    print("🧪 Tests critiques - Correctifs sécurité")
    
    print("✅ Test 1: Validation fichiers sécurisée")
    test_file_security_validation()
    
    print("✅ Test 2: Détection contenu malicieux")
    test_malicious_content_detection()
    
    print("✅ Test 3: Sanitisation noms fichiers")
    test_filename_sanitization()
    
    print("✅ Test 4: Génération clés sécurisées")
    test_database_encryption_keys()
    
    print("✅ Test 5: Sécurité migration DB")
    test_database_migration_safety()
    
    print("✅ Test 6: Configuration environnement")
    test_encryption_key_environment()
    
    print("🎯 TOUS LES TESTS CRITIQUES PASSÉS")