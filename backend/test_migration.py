#!/usr/bin/env python3
"""
Tests de vérification de la migration
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_health():
    """Test de santé de l'API"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health: {response.status_code}")
    return response.status_code == 200

def get_auth_token():
    """Obtenir un token d'authentification"""
    # Essayer différents mots de passe
    passwords = ["admin123", "secret123", "password", "admin"]
    
    for password in passwords:
        try:
            response = requests.post(f"{BASE_URL}/token", 
                data={"username": "admin", "password": password})
            
            if response.status_code == 200:
                token = response.json()["access_token"]
                print(f"✅ Token obtenu avec password: {password}")
                return token
        except:
            continue
    
    print("❌ Impossible d'obtenir un token")
    return None

def test_endpoints_with_token(token):
    """Tester les endpoints avec authentification"""
    headers = {"Authorization": f"Bearer {token}"}
    
    tests = [
        ("GET", "/config", "Configuration"),
        ("GET", "/provisions", "Provisions personnalisables"),
        ("GET", "/fixed-lines", "Dépenses fixes"),
        ("GET", "/summary?month=2025-08", "Résumé mensuel"),
    ]
    
    for method, endpoint, name in tests:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            
            print(f"{name}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if endpoint == "/summary?month=2025-08":
                    # Vérifier la structure du résumé
                    print(f"  - Nouvelles structures: fixed_lines_total={data.get('fixed_lines_total')}, provisions_total={data.get('provisions_total')}")
                elif endpoint == "/provisions":
                    print(f"  - Provisions trouvées: {len(data)} (dont migrée)")
                elif endpoint == "/fixed-lines":
                    print(f"  - Lignes fixes trouvées: {len(data)} (dont migrées)")
            else:
                print(f"  ❌ Erreur: {response.text}")
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")

def main():
    print("🧪 Tests de vérification de la migration")
    print("=" * 50)
    
    # Test de santé
    if not test_health():
        print("❌ Serveur non accessible")
        return
    
    # Obtenir un token
    token = get_auth_token()
    if not token:
        print("❌ Impossible de s'authentifier")
        return
    
    # Tests des endpoints
    test_endpoints_with_token(token)
    
    print("=" * 50)
    print("🎉 Tests terminés")

if __name__ == "__main__":
    main()