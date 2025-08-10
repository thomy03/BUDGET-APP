#!/usr/bin/env python3
"""
Script de validation de l'authentification
Teste le bon fonctionnement du système d'authentification avec admin/secret
"""

import requests
import sys
from passlib.context import CryptContext

# Configuration
BASE_URL = "http://127.0.0.1:8000"
TEST_USERNAME = "admin"
TEST_PASSWORD = "secret"

def test_password_hash():
    """Test du hash bcrypt stocké"""
    print("=== Test du hash bcrypt ===")
    
    pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
    stored_hash = "$2b$12$4A9H9JK7bYMdk7oYEeO/a.2FqfkGRp2HPvrx4BKEjDpYdM/Zmyf0G"
    
    try:
        result = pwd_context.verify(TEST_PASSWORD, stored_hash)
        print(f"✅ Hash bcrypt valide: {result}")
        return result
    except Exception as e:
        print(f"❌ Erreur lors de la validation du hash: {e}")
        return False

def test_authentication():
    """Test de l'authentification via API"""
    print("\n=== Test authentification API ===")
    
    try:
        # Test connexion valide
        response = requests.post(
            f"{BASE_URL}/token",
            data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            timeout=10
        )
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"✅ Authentification réussie")
            print(f"   Token: {token_data['access_token'][:50]}...")
            print(f"   Type: {token_data['token_type']}")
            return token_data['access_token']
        else:
            print(f"❌ Authentification échouée: {response.status_code}")
            print(f"   Réponse: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au serveur")
        print("   Assurez-vous que le serveur est démarré sur le port 8000")
        return None
    except Exception as e:
        print(f"❌ Erreur lors du test d'authentification: {e}")
        return None

def test_protected_access(token):
    """Test d'accès aux endpoints protégés"""
    if not token:
        print("\n❌ Pas de token disponible pour tester l'accès protégé")
        return False
        
    print("\n=== Test accès endpoints protégés ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Test endpoint /config
        response = requests.get(f"{BASE_URL}/config", headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Accès autorisé à /config")
            return True
        else:
            print(f"❌ Accès refusé à /config: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test d'accès protégé: {e}")
        return False

def test_invalid_credentials():
    """Test avec des identifiants invalides"""
    print("\n=== Test identifiants invalides ===")
    
    try:
        response = requests.post(
            f"{BASE_URL}/token",
            data={"username": TEST_USERNAME, "password": "wrongpassword"},
            timeout=10
        )
        
        if response.status_code == 401:
            print("✅ Rejet correct des identifiants invalides")
            return True
        else:
            print(f"❌ Comportement inattendu: {response.status_code}")
            print(f"   Réponse: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test d'identifiants invalides: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("🔐 VALIDATION SYSTÈME D'AUTHENTIFICATION")
    print("=" * 50)
    
    success = True
    
    # Test 1: Validation du hash
    if not test_password_hash():
        success = False
    
    # Test 2: Authentification API
    token = test_authentication()
    if not token:
        success = False
    
    # Test 3: Accès protégé
    if not test_protected_access(token):
        success = False
    
    # Test 4: Identifiants invalides
    if not test_invalid_credentials():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 TOUS LES TESTS RÉUSSIS!")
        print("   L'authentification fonctionne correctement.")
        print("   Vous pouvez vous connecter avec admin/secret")
        return 0
    else:
        print("💥 CERTAINS TESTS ONT ÉCHOUÉ!")
        print("   Vérifiez les erreurs ci-dessus.")
        return 1

if __name__ == "__main__":
    sys.exit(main())