#!/usr/bin/env python3
"""
Test rapide de la correction PATCH /transactions/{id}
"""
import requests
import json

# Test de l'authentification avec différents utilisateurs
users = [("demo", "demo"), ("admin", "admin"), ("test", "test")]

def test_auth():
    for username, password in users:
        response = requests.post("http://localhost:8000/token", data={
            "username": username,
            "password": password
        })
        if response.status_code == 200:
            print(f"✅ Authentifié avec {username}")
            return response.json()["access_token"], username
    print("❌ Aucune authentification réussie")
    return None, None

def test_patch_transaction(token, tx_id=1):
    """Test PATCH /transactions/{id} avec différents formats"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    test_cases = [
        {
            "name": "Tags string",
            "data": {"tags": "test,correction,fonctionnel"}
        },
        {
            "name": "Tags array", 
            "data": {"tags": ["test", "array", "format"]}
        },
        {
            "name": "Exclude seul",
            "data": {"exclude": False}
        },
        {
            "name": "Les deux",
            "data": {"exclude": True, "tags": "mixte,test"}
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Test: {test_case['name']}")
        response = requests.patch(
            f"http://localhost:8000/transactions/{tx_id}",
            headers=headers,
            json=test_case["data"]
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS - Tags: {result.get('tags', [])}, Exclude: {result.get('exclude')}")
        else:
            print(f"❌ ERROR {response.status_code}: {response.text}")

if __name__ == "__main__":
    print("🔧 Test correction PATCH /transactions/{id}")
    token, user = test_auth()
    if token:
        print(f"\n🔑 Utilisation utilisateur: {user}")
        test_patch_transaction(token)
    else:
        print("❌ Impossible de tester sans authentification")