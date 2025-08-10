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
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Réimport du même fichier (devrait détecter des doublons)
    test_file_path = "test_simple.csv"
    
    print("🔄 Test de détection de doublons - Réimport du même fichier")
    
    with open(test_file_path, 'rb') as f:
        files = {"file": (test_file_path, f, "text/csv")}
        
        import_response = requests.post(
            "http://127.0.0.1:8000/import",
            headers=headers,
            files=files
        )
        
        print(f"📤 Réimport Status: {import_response.status_code}")
        
        if import_response.status_code == 200:
            result = import_response.json()
            print(f"✅ Réimport traité!")
            print(f"📊 Import ID: {result['importId']}")
            print(f"📅 Mois détectés: {len(result['months'])}")
            for month in result['months']:
                print(f"   - {month['month']}: {month['newCount']} nouvelles transactions")
            print(f"🔄 Doublons détectés: {result['duplicatesCount']} ✨")
            if result['warnings']:
                print(f"⚠️  Warnings: {result['warnings']}")
                
            # Vérification que les transactions n'ont pas été doublées
            print(f"\n📋 Vérification des transactions janvier 2024:")
            tx_response = requests.get(
                f"http://127.0.0.1:8000/transactions?month=2024-01",
                headers=headers
            )
            
            if tx_response.status_code == 200:
                transactions = tx_response.json()
                print(f"✅ {len(transactions)} transactions en base (devrait rester 2)")
                if len(transactions) == 2:
                    print("🎯 Parfait ! Aucun doublon créé")
                else:
                    print("⚠️  Il y a eu duplication")
            else:
                print(f"❌ Erreur récupération transactions")
                
        else:
            print(f"❌ Erreur réimport:")
            print(import_response.text)
            
else:
    print(f"❌ Erreur authentification")