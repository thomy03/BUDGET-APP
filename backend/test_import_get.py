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
    
    # Le dernier import ID de notre test précédent  
    import_id = "1c78334b-633a-47c5-97c3-d713659ca78e"
    
    # Test de l'endpoint GET /imports/{id}
    get_response = requests.get(
        f"http://127.0.0.1:8000/imports/{import_id}",
        headers=headers
    )
    
    print(f"📥 GET Import Response Status: {get_response.status_code}")
    
    if get_response.status_code == 200:
        result = get_response.json()
        print(f"✅ Récupération métadonnées réussie!")
        print(f"📊 Import ID: {result['importId']}")
        print(f"📁 Fichier: {result['fileName']}")
        print(f"📅 Mois détectés: {len(result['months'])}")
        for month in result['months']:
            print(f"   - {month['month']}: {month['newCount']} nouvelles, {month['totalCount']} total")
            print(f"     Période: {month['firstDate']} → {month['lastDate']}")
        print(f"🎯 Mois suggéré: {result['suggestedMonth']}")
        print(f"⏱️  Temps de traitement: {result['processingMs']}ms")
        
        # Test des transactions pour janvier 2024
        print(f"\n📋 Test récupération transactions janvier 2024:")
        tx_response = requests.get(
            f"http://127.0.0.1:8000/transactions?month=2024-01",
            headers=headers
        )
        
        if tx_response.status_code == 200:
            transactions = tx_response.json()
            print(f"✅ {len(transactions)} transactions récupérées pour janvier 2024")
            for tx in transactions[:3]:  # Afficher les 3 premières
                print(f"   - {tx['date_op']}: {tx['label']} → {tx['amount']}€")
        else:
            print(f"❌ Erreur récupération transactions: {tx_response.status_code}")
            
    else:
        print(f"❌ Erreur récupération métadonnées:")
        print(get_response.text)
        
else:
    print(f"❌ Erreur authentification: {auth_response.status_code}")