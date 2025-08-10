#!/usr/bin/env python3

import requests
import json

# 1. Authentification
auth_response = requests.post(
    "http://127.0.0.1:8000/token",
    data={"username": "admin", "password": "secret"},
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

if auth_response.status_code == 200:
    token = auth_response.json()["access_token"]
    print(f"✅ Authentification réussie")
    
    # 2. Test import CSV
    headers = {"Authorization": f"Bearer {token}"}
    
    # Utilisons un fichier de test simple
    test_file_path = "test_simple.csv"
    
    try:
        with open(test_file_path, 'rb') as f:
            files = {"file": (test_file_path, f, "text/csv")}
            
            import_response = requests.post(
                "http://127.0.0.1:8000/import",
                headers=headers,
                files=files
            )
            
            print(f"\n📤 Import Response Status: {import_response.status_code}")
            
            if import_response.status_code == 200:
                result = import_response.json()
                print(f"✅ Import réussi!")
                print(f"📊 Import ID: {result['importId']}")
                print(f"📅 Mois détectés: {len(result['months'])}")
                for month in result['months']:
                    print(f"   - {month['month']}: {month['newCount']} nouvelles transactions")
                print(f"🎯 Mois suggéré: {result['suggestedMonth']}")
                print(f"🔄 Doublons: {result['duplicatesCount']}")
                if result['warnings']:
                    print(f"⚠️  Warnings: {result['warnings']}")
                print(f"⏱️  Temps de traitement: {result['processingMs']}ms")
                
            else:
                print(f"❌ Erreur import:")
                print(import_response.text)
                
    except FileNotFoundError:
        print(f"❌ Fichier de test introuvable: {test_file_path}")
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        
else:
    print(f"❌ Erreur authentification: {auth_response.status_code}")
    print(auth_response.text)