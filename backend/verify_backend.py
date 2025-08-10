#!/usr/bin/env python3
"""
Script de vérification finale du backend Python
Vérifie que toutes les fonctionnalités critiques fonctionnent correctement
"""

import sys
import os
import traceback
from pathlib import Path

def test_basic_imports():
    """Test des imports de base"""
    print("🔍 Test des imports de base...")
    
    imports = [
        ('fastapi', 'FastAPI'),
        ('uvicorn', 'ASGI Server'), 
        ('pandas', 'Data Processing'),
        ('numpy', 'Numerical Computing'),
        ('sqlalchemy', 'Database ORM'),
        ('jose', 'JWT Security'),
        ('passlib', 'Password Hashing'),
        ('cryptography', 'Cryptography'),
        ('dotenv', 'Environment Variables'),
        ('email_validator', 'Email Validation'),
        ('pydantic', 'Data Validation')
    ]
    
    failed = []
    for module, description in imports:
        try:
            __import__(module)
            print(f"   ✅ {module} - {description}")
        except ImportError as e:
            print(f"   ❌ {module} - {description} - ERREUR: {e}")
            failed.append(module)
    
    return failed

def test_optional_imports():
    """Test des imports optionnels"""
    print("\n🔍 Test des imports optionnels...")
    
    optional = [
        ('magic', 'File Type Detection'),
        ('pysqlcipher3', 'SQLCipher Support')
    ]
    
    missing = []
    for module, description in optional:
        try:
            __import__(module)
            print(f"   ✅ {module} - {description}")
        except ImportError:
            print(f"   ⚠️  {module} - {description} - MANQUANT (optionnel)")
            missing.append(module)
    
    return missing

def test_local_modules():
    """Test des modules locaux"""
    print("\n🔍 Test des modules locaux...")
    
    modules = [
        ('auth', 'Authentication System'),
        ('database_encrypted', 'Database Encryption'),
        ('audit_logger', 'Audit Logging')
    ]
    
    failed = []
    for module, description in modules:
        try:
            __import__(module)
            print(f"   ✅ {module} - {description}")
        except Exception as e:
            print(f"   ❌ {module} - {description} - ERREUR: {e}")
            failed.append(module)
    
    return failed

def test_app_import():
    """Test import de l'application principale"""
    print("\n🔍 Test import application principale...")
    
    try:
        import app
        print(f"   ✅ app.py importé avec succès")
        
        # Vérifier l'instance FastAPI
        if hasattr(app, 'app'):
            print(f"   ✅ Instance FastAPI trouvée")
            return True
        else:
            print(f"   ❌ Instance FastAPI non trouvée")
            return False
            
    except Exception as e:
        print(f"   ❌ Erreur import app.py: {e}")
        traceback.print_exc()
        return False

def test_database_functionality():
    """Test fonctionnalité base de données"""
    print("\n🔍 Test fonctionnalité base de données...")
    
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Test création engine
        engine = create_engine("sqlite:///:memory:")
        print(f"   ✅ Moteur SQLAlchemy créé")
        
        # Test session
        Session = sessionmaker(bind=engine)
        session = Session()
        session.close()
        print(f"   ✅ Session database fonctionnelle")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur base de données: {e}")
        return False

def test_security_functionality():
    """Test fonctionnalités sécurité"""
    print("\n🔍 Test fonctionnalités sécurité...")
    
    try:
        from passlib.context import CryptContext
        from jose import jwt
        
        # Test hashage mot de passe
        pwd_context = CryptContext(schemes=["bcrypt"])
        hashed = pwd_context.hash("test")
        verified = pwd_context.verify("test", hashed)
        
        if verified:
            print(f"   ✅ Hashage/vérification mot de passe OK")
        else:
            print(f"   ❌ Problème hashage mot de passe")
            return False
        
        # Test JWT
        token = jwt.encode({"test": "data"}, "secret", algorithm="HS256")
        decoded = jwt.decode(token, "secret", algorithms=["HS256"])
        
        if decoded.get("test") == "data":
            print(f"   ✅ Fonctionnalité JWT OK")
        else:
            print(f"   ❌ Problème JWT")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur sécurité: {e}")
        return False

def test_data_processing():
    """Test traitement des données"""
    print("\n🔍 Test traitement des données...")
    
    try:
        import pandas as pd
        import numpy as np
        
        # Test création DataFrame
        df = pd.DataFrame({"test": [1, 2, 3]})
        if len(df) == 3:
            print(f"   ✅ Pandas DataFrame OK")
        else:
            print(f"   ❌ Problème Pandas DataFrame")
            return False
        
        # Test numpy
        arr = np.array([1, 2, 3])
        if arr.sum() == 6:
            print(f"   ✅ Numpy Array OK")
        else:
            print(f"   ❌ Problème Numpy Array")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur traitement données: {e}")
        return False

def test_file_existence():
    """Vérification existence fichiers critiques"""
    print("\n🔍 Vérification fichiers critiques...")
    
    critical_files = [
        "app.py",
        "auth.py", 
        "database_encrypted.py",
        "audit_logger.py"
    ]
    
    missing = []
    for file in critical_files:
        if Path(file).exists():
            size = Path(file).stat().st_size
            print(f"   ✅ {file} ({size} bytes)")
        else:
            print(f"   ❌ {file} - MANQUANT")
            missing.append(file)
    
    return missing

def main():
    """Fonction principale de vérification"""
    print("="*60)
    print("🚀 VÉRIFICATION COMPLÈTE DU BACKEND PYTHON")
    print("="*60)
    
    all_tests_passed = True
    warnings = []
    
    # Test imports de base
    failed_imports = test_basic_imports()
    if failed_imports:
        all_tests_passed = False
        print(f"\n❌ CRITIQUE: Modules manquants: {', '.join(failed_imports)}")
    
    # Test imports optionnels
    missing_optional = test_optional_imports()
    if missing_optional:
        warnings.extend(missing_optional)
    
    # Test modules locaux
    failed_local = test_local_modules()
    if failed_local:
        all_tests_passed = False
        print(f"\n❌ CRITIQUE: Modules locaux défaillants: {', '.join(failed_local)}")
    
    # Test fichiers
    missing_files = test_file_existence()
    if missing_files:
        all_tests_passed = False
        print(f"\n❌ CRITIQUE: Fichiers manquants: {', '.join(missing_files)}")
    
    # Test import application
    if not test_app_import():
        all_tests_passed = False
    
    # Tests fonctionnels
    if not test_database_functionality():
        all_tests_passed = False
    
    if not test_security_functionality():
        all_tests_passed = False
    
    if not test_data_processing():
        all_tests_passed = False
    
    # Résumé final
    print("\n" + "="*60)
    print("📋 RÉSUMÉ DE LA VÉRIFICATION")
    print("="*60)
    
    if all_tests_passed:
        print("✅ SUCCÈS: Tous les tests critiques sont passés")
        print("🚀 Le backend est prêt à être utilisé")
        
        if warnings:
            print(f"⚠️  Modules optionnels manquants: {', '.join(warnings)}")
            print("   (Ces modules ne sont pas critiques)")
    else:
        print("❌ ÉCHEC: Des problèmes critiques ont été détectés")
        print("🔧 Consultez les messages d'erreur ci-dessus")
        print("📖 Référez-vous à GUIDE_DEPANNAGE_WINDOWS.md")
        return False
    
    # Test final - même commande que le script batch
    print("\n🔍 Test final - Commande script batch...")
    try:
        import app
        print("✅ Backend OK")
        return True
    except Exception as e:
        print(f"❌ Backend ÉCHEC: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)