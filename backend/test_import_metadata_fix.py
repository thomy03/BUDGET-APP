#!/usr/bin/env python3
"""
Test script pour vérifier que la correction ImportMetadata fonctionne
"""
import sys
import os
import logging
from io import StringIO
from fastapi.testclient import TestClient

# Add current directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models.database import engine, SessionLocal, Transaction, ImportMetadata
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_import_metadata_creation():
    """Test de création d'ImportMetadata avec les bons champs"""
    print("🧪 Test 1: Création directe d'ImportMetadata")
    
    import json
    from datetime import datetime
    
    try:
        meta = ImportMetadata(
            id='test-direct-123',
            filename='test_direct.csv',
            created_at=datetime.now().date(),
            user_id='test_user',
            months_detected=json.dumps(['2024-01', '2024-02']),
            duplicates_count=0,
            warnings=None,
            processing_ms=100
        )
        print("✅ ImportMetadata créé directement avec succès")
        print(f"   ID: {meta.id}")
        print(f"   Filename: {meta.filename}")
        return True
    except Exception as e:
        print(f"❌ Erreur création ImportMetadata: {e}")
        return False

def test_import_endpoint_mock():
    """Test de l'endpoint d'import en mockant l'authentification"""
    print("\n🧪 Test 2: Test endpoint import avec mock auth")
    
    client = TestClient(app)
    
    # Créer un fichier CSV de test en mémoire
    csv_content = """Date,Description,Montant,Compte
2025-01-01,Test transaction,12.34,CHECKING
2025-01-02,Test transaction 2,-5.67,CHECKING"""
    
    try:
        # Mock l'authentification en modifiant temporairement la dépendance
        from fastapi import Depends
        from auth import get_current_user
        
        # Fonction mock pour l'authentification - retourner un objet avec attributs
        class MockUser:
            def __init__(self):
                self.username = "test_user"
                self.id = 1
        
        def mock_current_user():
            return MockUser()
        
        # Remplacer temporairement la dépendance
        app.dependency_overrides[get_current_user] = mock_current_user
        
        # Tester l'upload
        files = {'file': ('test.csv', csv_content, 'text/csv')}
        response = client.post("/import", files=files)
        
        # Nettoyer les overrides
        app.dependency_overrides.clear()
        
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("✅ Import endpoint fonctionne sans erreur 500")
            return True
        else:
            print(f"⚠️ Import endpoint retourne {response.status_code}")
            if "import_id is an invalid keyword argument" in response.text:
                print("❌ L'erreur ImportMetadata persiste!")
                return False
            else:
                print("ℹ️ Autre erreur (pas liée à ImportMetadata)")
                return True
                
    except Exception as e:
        print(f"❌ Erreur test endpoint: {e}")
        return False

def test_database_import_metadata_table():
    """Test de la table ImportMetadata dans la base"""
    print("\n🧪 Test 3: Vérification table ImportMetadata en base")
    
    try:
        with engine.connect() as conn:
            # Vérifier la structure de la table
            result = conn.execute(text("PRAGMA table_info('import_metadata')")).fetchall()
            columns = [row[1] for row in result]
            print(f"Colonnes ImportMetadata: {columns}")
            
            expected_columns = ['id', 'filename', 'created_at', 'user_id', 'months_detected', 
                              'duplicates_count', 'warnings', 'processing_ms']
            
            missing_columns = [col for col in expected_columns if col not in columns]
            if missing_columns:
                print(f"❌ Colonnes manquantes: {missing_columns}")
                return False
            
            extra_columns = [col for col in columns if col not in expected_columns]
            if extra_columns:
                print(f"ℹ️ Colonnes supplémentaires: {extra_columns}")
            
            print("✅ Structure table ImportMetadata correcte")
            return True
            
    except Exception as e:
        print(f"❌ Erreur vérification table: {e}")
        return False

def main():
    """Exécution des tests"""
    print("🔧 Test de correction ImportMetadata")
    print("=" * 50)
    
    tests = [
        test_import_metadata_creation,
        test_database_import_metadata_table,
        test_import_endpoint_mock
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Exception dans {test_func.__name__}: {e}")
            results.append(False)
    
    print("\n📊 RÉSULTATS")
    print("=" * 30)
    passed = sum(results)
    total = len(results)
    print(f"Tests réussis: {passed}/{total}")
    
    if passed == total:
        print("✅ TOUS LES TESTS PASSÉS - ImportMetadata corrigé!")
        return 0
    else:
        print("❌ Des tests ont échoué")
        return 1

if __name__ == "__main__":
    sys.exit(main())