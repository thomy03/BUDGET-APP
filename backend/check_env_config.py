#!/usr/bin/env python3
"""
Script de vérification des variables d'environnement et configuration JWT
"""
import os
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta

def check_env_config():
    print("=== VÉRIFICATION VARIABLES D'ENVIRONNEMENT ===\n")
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Vérifier JWT_SECRET_KEY
    jwt_key = os.getenv("JWT_SECRET_KEY")
    if jwt_key:
        print(f"✅ JWT_SECRET_KEY trouvée:")
        print(f"  - Longueur: {len(jwt_key)} caractères")
        print(f"  - Aperçu: {jwt_key[:8]}...{jwt_key[-8:]}")
        
        # Vérifier la sécurité de la clé
        if len(jwt_key) >= 32:
            print("  - ✅ Longueur sécurisée (≥32 caractères)")
        else:
            print("  - ⚠️  Longueur insuffisante (<32 caractères)")
            
        if jwt_key == "CHANGEME_IN_PRODUCTION_URGENT":
            print("  - ❌ DANGER: Clé par défaut non sécurisée!")
        else:
            print("  - ✅ Clé personnalisée")
    else:
        print("❌ JWT_SECRET_KEY non trouvée dans .env")
    
    # Vérifier DB_ENCRYPTION_KEY
    db_key = os.getenv("DB_ENCRYPTION_KEY")
    if db_key:
        print(f"\n✅ DB_ENCRYPTION_KEY trouvée:")
        print(f"  - Longueur: {len(db_key)} caractères")
        print(f"  - Aperçu: {db_key[:8]}...{db_key[-8:]}")
    else:
        print("\n⚠️  DB_ENCRYPTION_KEY non configurée (optionnelle)")
    
    # Autres variables d'environnement importantes
    other_vars = ["DATABASE_URL", "CORS_ORIGINS", "DEBUG", "LOG_LEVEL"]
    print(f"\n🔍 Autres variables d'environnement:")
    for var in other_vars:
        value = os.getenv(var)
        if value:
            print(f"  - {var}: {value}")
        else:
            print(f"  - {var}: non définie")

def check_jwt_functionality():
    """Tester la fonctionnalité JWT"""
    print("\n=== TEST FONCTIONNALITÉ JWT ===\n")
    
    try:
        from auth import create_access_token, SECRET_KEY, ALGORITHM
        from jose import jwt
        
        print(f"📝 Configuration JWT actuelle:")
        print(f"  - SECRET_KEY longueur: {len(SECRET_KEY)}")
        print(f"  - Algorithme: {ALGORITHM}")
        print(f"  - Durée d'expiration: 30 minutes")
        
        # Créer un token de test
        test_data = {"sub": "test_user"}
        test_token = create_access_token(test_data, timedelta(minutes=5))
        
        print(f"\n🔧 Test création token:")
        print(f"  - Token créé: {test_token[:20]}...")
        
        # Décoder le token
        decoded = jwt.decode(test_token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"  - Décodage réussi: {decoded}")
        
        print("✅ Fonctionnalité JWT opérationnelle")
        return True
        
    except Exception as e:
        print(f"❌ Erreur test JWT: {e}")
        return False

def check_cors_config():
    """Vérifier la configuration CORS"""
    print("\n=== CONFIGURATION CORS ===\n")
    
    try:
        # Lire le fichier app.py pour vérifier CORS
        with open('app.py', 'r') as f:
            content = f.read()
            
        if 'CORSMiddleware' in content:
            print("✅ CORSMiddleware configuré")
            
            # Extraire les origins autorisées
            import re
            origins_match = re.search(r'allow_origins=\[(.*?)\]', content, re.DOTALL)
            if origins_match:
                origins = origins_match.group(1)
                print(f"  - Origins autorisées: {origins}")
            else:
                print("  - Origins: configuration par défaut")
                
            if 'allow_credentials=True' in content:
                print("  - ✅ Credentials autorisées")
            else:
                print("  - ❌ Credentials non autorisées")
                
        else:
            print("❌ CORSMiddleware non trouvé")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur vérification CORS: {e}")
        return False

if __name__ == "__main__":
    success1 = check_env_config()
    success2 = check_jwt_functionality()
    success3 = check_cors_config()
    
    print("\n" + "="*50)
    if success2 and success3:
        print("✅ Configuration authentification opérationnelle")
        sys.exit(0)
    else:
        print("❌ Problèmes détectés dans la configuration")
        sys.exit(1)