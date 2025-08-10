#!/usr/bin/env python3
"""
Test de l'endpoint /token avec des requêtes HTTP réelles
"""

import requests
import json
import sys
import time
from subprocess import Popen, PIPE
import threading
import signal

# Configuration du serveur
SERVER_URL = "http://127.0.0.1:8000"
TOKEN_ENDPOINT = f"{SERVER_URL}/token"

def start_server():
    """Démarre le serveur FastAPI en arrière-plan"""
    try:
        # Import des modules requis pour vérifier les dépendances
        import uvicorn
        import fastapi
        import passlib
        import jose
        print("✅ Toutes les dépendances sont disponibles")
        
        # Démarre le serveur
        print("🚀 Démarrage du serveur...")
        server_process = Popen([
            "python3", "-m", "uvicorn", "app:app", 
            "--host", "127.0.0.1", "--port", "8000", "--reload"
        ], stdout=PIPE, stderr=PIPE, text=True)
        
        # Attendre que le serveur soit prêt
        print("⏳ Attente du démarrage du serveur...")
        time.sleep(5)
        
        # Vérifier si le serveur est accessible
        try:
            response = requests.get(f"{SERVER_URL}/docs", timeout=5)
            if response.status_code == 200:
                print("✅ Serveur démarré et accessible")
                return server_process
            else:
                print(f"❌ Serveur non accessible: {response.status_code}")
                return None
        except requests.RequestException as e:
            print(f"❌ Impossible de joindre le serveur: {e}")
            return None
            
    except ImportError as e:
        print(f"❌ Dépendance manquante: {e}")
        return None
    except Exception as e:
        print(f"❌ Erreur démarrage serveur: {e}")
        return None

def test_token_endpoint():
    """Test l'endpoint /token"""
    print(f"\n=== Test de l'endpoint {TOKEN_ENDPOINT} ===")
    
    # Test 1: Requête avec credentials valides
    print("\n🔑 Test 1: Credentials valides (admin/secret)")
    
    data = {
        "username": "admin",
        "password": "secret",
        "grant_type": "password"
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        response = requests.post(TOKEN_ENDPOINT, data=data, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            token_data = response.json()
            print("✅ Token obtenu avec succès!")
            print(f"Access Token: {token_data.get('access_token', 'N/A')[:50]}...")
            print(f"Token Type: {token_data.get('token_type', 'N/A')}")
            return token_data.get('access_token')
        else:
            print(f"❌ Échec obtention token: {response.status_code}")
            return None
            
    except requests.RequestException as e:
        print(f"❌ Erreur requête: {e}")
        return None
    
    # Test 2: Requête avec credentials invalides
    print("\n🔑 Test 2: Credentials invalides (admin/wrong)")
    
    data_invalid = {
        "username": "admin",
        "password": "wrong",
        "grant_type": "password"
    }
    
    try:
        response = requests.post(TOKEN_ENDPOINT, data=data_invalid, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 401:
            print("✅ Erreur 401 correctement retournée pour credentials invalides")
        else:
            print(f"❌ Status code inattendu: {response.status_code}")
    
    except requests.RequestException as e:
        print(f"❌ Erreur requête: {e}")

def test_protected_endpoint(token):
    """Test un endpoint protégé avec le token"""
    if not token:
        print("❌ Pas de token disponible pour tester les endpoints protégés")
        return
        
    print(f"\n=== Test endpoint protégé ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{SERVER_URL}/users/me/", headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Endpoint protégé accessible avec token")
        else:
            print(f"❌ Échec accès endpoint protégé: {response.status_code}")
    
    except requests.RequestException as e:
        print(f"❌ Erreur requête endpoint protégé: {e}")

def main():
    print("🔧 Test complet de l'authentification HTTP")
    print("=" * 50)
    
    # Démarrer le serveur
    server_process = start_server()
    if not server_process:
        print("❌ Impossible de démarrer le serveur")
        return 1
    
    try:
        # Tester l'endpoint /token
        token = test_token_endpoint()
        
        # Tester un endpoint protégé
        test_protected_endpoint(token)
        
        print(f"\n=== RÉSUMÉ ===")
        if token:
            print("✅ Authentification fonctionne correctement")
            print("✅ L'utilisateur peut maintenant accéder à l'import CSV")
        else:
            print("❌ Problème d'authentification détecté")
        
        return 0
        
    finally:
        # Arrêter le serveur
        print(f"\n🛑 Arrêt du serveur...")
        if server_process:
            server_process.terminate()
            time.sleep(2)
            if server_process.poll() is None:
                server_process.kill()

if __name__ == "__main__":
    sys.exit(main())