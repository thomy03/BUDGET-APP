"""
Script de diagnostic pour identifier les problèmes de dépendances sur Windows
Diagnostic ciblé pour l'erreur "Probleme configuration backend"
"""

import sys
import os
import platform
from pathlib import Path

print("=== DIAGNOSTIC BACKEND PYTHON ===")
print(f"OS: {platform.system()} {platform.version()}")
print(f"Python: {sys.version}")
print(f"Architecture: {platform.machine()}")
print(f"Working Directory: {os.getcwd()}")
print()

# Test des imports critiques
critical_modules = {
    'fastapi': 'FastAPI framework',
    'uvicorn': 'ASGI server',
    'pandas': 'Data processing',
    'numpy': 'Numerical computing',
    'sqlalchemy': 'Database ORM',
    'jose': 'JWT handling',
    'passlib': 'Password hashing',
    'cryptography': 'Cryptographic functions',
    'dotenv': 'Environment variables',
    'email_validator': 'Email validation',
    'pydantic': 'Data validation'
}

optional_modules = {
    'pysqlcipher3': 'SQLCipher support (optional)',
    'magic': 'File type detection (may need libmagic on Windows)',
}

print("=== MODULES CRITIQUES ===")
missing_critical = []
for module, description in critical_modules.items():
    try:
        __import__(module)
        print(f"✅ {module}: OK - {description}")
    except ImportError as e:
        print(f"❌ {module}: MANQUANT - {description}")
        print(f"   Erreur: {e}")
        missing_critical.append(module)

print("\n=== MODULES OPTIONNELS ===")
missing_optional = []
for module, description in optional_modules.items():
    try:
        __import__(module)
        print(f"✅ {module}: OK - {description}")
    except ImportError as e:
        print(f"⚠️  {module}: MANQUANT - {description}")
        print(f"   Erreur: {e}")
        missing_optional.append(module)

print("\n=== TEST IMPORT APP ===")
try:
    # Test import des modules locaux
    print("Test import modules locaux...")
    
    # Test database_encrypted
    try:
        import database_encrypted
        print("✅ database_encrypted: OK")
    except Exception as e:
        print(f"❌ database_encrypted: ERREUR - {e}")
    
    # Test auth
    try:
        import auth
        print("✅ auth: OK")
    except Exception as e:
        print(f"❌ auth: ERREUR - {e}")
    
    # Test audit_logger
    try:
        import audit_logger
        print("✅ audit_logger: OK")
    except Exception as e:
        print(f"❌ audit_logger: ERREUR - {e}")
    
    # Test app principal
    import app
    print("✅ app: IMPORT RÉUSSI")
    
    # Test création instance FastAPI
    if hasattr(app, 'app'):
        print("✅ app.app: Instance FastAPI trouvée")
    else:
        print("❌ app.app: Instance FastAPI non trouvée")
        
except Exception as e:
    print(f"❌ app: IMPORT ÉCHOUÉ")
    print(f"   Erreur détaillée: {e}")
    import traceback
    traceback.print_exc()

print("\n=== VÉRIFICATION FICHIERS ===")
required_files = [
    'app.py',
    'auth.py', 
    'database_encrypted.py',
    'audit_logger.py',
    'requirements.txt'
]

for file in required_files:
    file_path = Path(file)
    if file_path.exists():
        size = file_path.stat().st_size
        print(f"✅ {file}: OK ({size} bytes)")
    else:
        print(f"❌ {file}: MANQUANT")

print("\n=== RÉSUMÉ DIAGNOSTIC ===")
if missing_critical:
    print(f"❌ MODULES CRITIQUES MANQUANTS: {', '.join(missing_critical)}")
    print("   Ces modules DOIVENT être installés pour que l'app fonctionne.")
else:
    print("✅ TOUS LES MODULES CRITIQUES SONT PRÉSENTS")

if missing_optional:
    print(f"⚠️  MODULES OPTIONNELS MANQUANTS: {', '.join(missing_optional)}")
    print("   Ces modules sont optionnels mais recommandés pour certaines fonctionnalités.")
else:
    print("✅ TOUS LES MODULES OPTIONNELS SONT PRÉSENTS")

print("\n=== SOLUTIONS RECOMMANDÉES ===")

if 'pysqlcipher3' in missing_optional:
    print("📋 pysqlcipher3 manquant (Windows):")
    print("   - Sur Windows, pysqlcipher3 peut être difficile à installer")
    print("   - Alternative 1: pip install pysqlcipher3")
    print("   - Alternative 2: Utiliser requirements_windows.txt (sans SQLCipher)")
    print("   - Alternative 3: Utiliser requirements_minimal.txt")
    print("   - L'app fonctionnera avec SQLite standard si SQLCipher n'est pas disponible")

if 'magic' in missing_optional:
    print("📋 python-magic manquant (Windows):")
    print("   - Sur Windows, nécessite libmagic.dll")
    print("   - Solution 1: pip install python-magic-bin")
    print("   - Solution 2: Installer manuellement libmagic")

print("\n=== COMMANDES DE CORRECTION ===")
print("Pour Windows 10, exécutez dans votre venv activé:")
print()

if missing_critical:
    print("1️⃣ Installer les dépendances critiques:")
    print("   pip install --upgrade pip")
    for module in missing_critical:
        print(f"   pip install {module}")

print("\n2️⃣ Options pour les dépendances optionnelles:")
print("   Option A - Complet (avec SQLCipher):")
print("   pip install -r requirements.txt")
print()
print("   Option B - Windows friendly (sans SQLCipher):")
print("   pip install -r requirements_windows.txt")
print()
print("   Option C - Minimal:")
print("   pip install -r requirements_minimal.txt")

print("\n3️⃣ Test final:")
print('   python -c "import app; print(\'Backend OK\')"')

print("\nℹ️  Si l'erreur persiste, exécutez ce script depuis votre environnement Windows:")
print(f"   python {__file__}")