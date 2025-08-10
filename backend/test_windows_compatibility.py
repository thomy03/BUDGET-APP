#!/usr/bin/env python3
"""
Script de test de compatibilité Windows
Teste tous les imports et fonctionnalités principales
"""

import sys
import traceback
import json
from pathlib import Path

def test_import(module_name, description):
    """Teste l'import d'un module"""
    try:
        __import__(module_name)
        print(f"✅ {description}: OK")
        return True
    except Exception as e:
        print(f"❌ {description}: ERREUR - {e}")
        return False

def test_magic_detection():
    """Teste la détection MIME"""
    try:
        # Test with fallback
        import magic_fallback as magic
        test_csv = b"dateOp,amount,label\n2024-01-01,100,test"
        result = magic.from_buffer(test_csv)
        expected = "text/csv"
        if expected in result or result == expected:
            print(f"✅ Détection MIME fallback: OK ({result})")
            return True
        else:
            print(f"⚠️  Détection MIME fallback: {result} (attendu: {expected})")
            return False
    except Exception as e:
        print(f"❌ Détection MIME fallback: ERREUR - {e}")
        return False

def test_database():
    """Teste la base de données"""
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine("sqlite:///./test_windows.db", future=True, echo=False)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
        Path("./test_windows.db").unlink(missing_ok=True)
        print("✅ SQLite standard: OK")
        return True
    except Exception as e:
        print(f"❌ SQLite standard: ERREUR - {e}")
        return False

def test_fastapi():
    """Teste FastAPI avec les modules optimisés"""
    try:
        from fastapi.testclient import TestClient
        import app_windows_optimized
        
        client = TestClient(app_windows_optimized.app)
        
        # Test health endpoint
        response = client.get("/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ FastAPI Windows: OK")
            print(f"   Status: {health_data['status']}")
            print(f"   Features actives: {list(health_data['features'].keys())}")
            return True
        else:
            print(f"❌ FastAPI Windows: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ FastAPI Windows: ERREUR - {e}")
        traceback.print_exc()
        return False

def test_csv_parsing():
    """Teste le parsing CSV"""
    try:
        import pandas as pd
        import io
        
        # Test données CSV simples
        csv_content = """dateOp,amount,label,category
2024-01-01,100.50,Test payment,Food
2024-01-02,-50.25,Grocery store,Food
"""
        df = pd.read_csv(io.StringIO(csv_content))
        if len(df) == 2 and 'dateOp' in df.columns:
            print("✅ Parsing CSV: OK")
            return True
        else:
            print("❌ Parsing CSV: Données incorrectes")
            return False
            
    except Exception as e:
        print(f"❌ Parsing CSV: ERREUR - {e}")
        return False

def main():
    """Tests principaux"""
    print("=== TEST DE COMPATIBILITÉ WINDOWS ===")
    print(f"Python: {sys.version}")
    print(f"Plateforme: {sys.platform}")
    print()
    
    tests = []
    
    # Tests d'imports de base
    tests.append(test_import("fastapi", "FastAPI"))
    tests.append(test_import("pandas", "Pandas"))
    tests.append(test_import("numpy", "NumPy"))
    tests.append(test_import("sqlalchemy", "SQLAlchemy"))
    tests.append(test_import("pydantic", "Pydantic"))
    tests.append(test_import("passlib", "Passlib"))
    tests.append(test_import("jose", "Python-JOSE"))
    
    print()
    
    # Tests modules custom
    tests.append(test_import("magic_fallback", "Magic fallback"))
    tests.append(test_import("app_windows_optimized", "App Windows optimisé"))
    
    print()
    
    # Tests fonctionnels
    tests.append(test_magic_detection())
    tests.append(test_database())
    tests.append(test_csv_parsing())
    tests.append(test_fastapi())
    
    print()
    
    # Tests optionnels (peuvent échouer sur Windows)
    print("=== TESTS OPTIONNELS (peuvent échouer sur Windows) ===")
    optional_tests = []
    optional_tests.append(test_import("pysqlcipher3", "PySQLCipher3 (chiffrement DB)"))
    optional_tests.append(test_import("magic", "Python-Magic (détection MIME)"))
    
    print()
    
    # Résumé
    passed = sum(tests)
    total = len(tests)
    optional_passed = sum(optional_tests)
    optional_total = len(optional_tests)
    
    print("=== RÉSUMÉ ===")
    print(f"Tests critiques: {passed}/{total} réussis")
    print(f"Tests optionnels: {optional_passed}/{optional_total} réussis")
    
    if passed == total:
        print("🎉 TOUS LES TESTS CRITIQUES RÉUSSIS - Backend compatible Windows!")
        print("💡 Utilisez app_windows_optimized.py sur Windows")
        return 0
    else:
        print("❌ Certains tests critiques ont échoué")
        return 1

if __name__ == "__main__":
    sys.exit(main())