#!/usr/bin/env python3
"""
Script pour tester et diagnostiquer le problème CORS
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_cors_detailed():
    """Test détaillé des headers CORS"""
    print("🔍 DIAGNOSTIC CORS DÉTAILLÉ\n")
    
    # Test avec différentes méthodes
    methods = ["GET", "POST", "OPTIONS"]
    endpoints = ["/health", "/token", "/config"]
    
    for endpoint in endpoints:
        print(f"📍 Test endpoint: {endpoint}")
        
        for method in methods:
            try:
                if method == "GET":
                    response = requests.get(f"{BASE_URL}{endpoint}")
                elif method == "POST":
                    response = requests.post(f"{BASE_URL}{endpoint}")
                elif method == "OPTIONS":
                    response = requests.options(f"{BASE_URL}{endpoint}")
                
                print(f"  {method}: Status {response.status_code}")
                
                # Vérifier les headers CORS
                cors_headers = {
                    "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                    "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                    "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
                    "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials"),
                }
                
                found_headers = {k: v for k, v in cors_headers.items() if v}
                if found_headers:
                    print(f"    CORS Headers: {found_headers}")
                else:
                    print("    ⚠️  Aucun header CORS trouvé")
                    
            except Exception as e:
                print(f"  {method}: Erreur - {e}")
        
        print()

def test_preflight_request():
    """Test de la requête preflight CORS"""
    print("🚀 TEST REQUÊTE PREFLIGHT\n")
    
    # Simuler une requête preflight
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,Authorization"
    }
    
    try:
        response = requests.options(f"{BASE_URL}/token", headers=headers)
        print(f"Status: {response.status_code}")
        print("Headers de réponse:")
        for header, value in response.headers.items():
            if "access-control" in header.lower():
                print(f"  {header}: {value}")
        
        if response.status_code == 200:
            print("✅ Requête preflight acceptée")
        else:
            print("❌ Requête preflight rejetée")
            
    except Exception as e:
        print(f"❌ Erreur preflight: {e}")

if __name__ == "__main__":
    test_cors_detailed()
    test_preflight_request()