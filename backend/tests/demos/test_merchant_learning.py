#!/usr/bin/env python3
"""
Test du système d'apprentissage merchant → tag
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Headers d'authentification (à adapter)
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer test_token"  # Remplacer par un vrai token si nécessaire
}

def test_merchant_learning():
    print("🧪 Test du système d'apprentissage merchant → tag")
    print("=" * 50)
    
    # Test 1: Enregistrer un apprentissage pour FRANPRIX
    print("\n📝 Test 1: Apprentissage pour FRANPRIX")
    print("-" * 30)
    
    # Simuler une validation de tag par l'utilisateur
    payload = {
        "transaction_id": 123,  # ID fictif pour test
        "label": "FRANPRIX PARIS 11",
        "amount": -45.50,
        "selected_tag": "courses",
        "confidence": 1.0,
        "source": "manual"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/ml-feedback/confirm",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Apprentissage enregistré")
            print(f"   - Merchant: {result.get('merchant_learned', 'N/A')}")
            print(f"   - Tag appris: courses")
            print(f"   - Transactions similaires mises à jour: {result.get('similar_transactions_updated', 0)}")
        else:
            print(f"❌ Erreur: {response.status_code}")
            print(f"   Détails: {response.text}")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
    
    # Attendre un peu
    time.sleep(1)
    
    # Test 2: Vérifier que le tag est suggéré pour FRANPRIX
    print("\n🔍 Test 2: Récupération des tags appris pour FRANPRIX")
    print("-" * 30)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/ml-feedback/merchant-tags/FRANPRIX",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Tags trouvés pour FRANPRIX:")
            print(f"   - Tags: {result.get('tags', [])}")
            print(f"   - Confiance: {result.get('confidence', 0)}")
            print(f"   - Source: {result.get('source', 'N/A')}")
        else:
            print(f"⚠️ Pas de tags appris pour FRANPRIX")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 3: Tester avec une variation du nom
    print("\n🔍 Test 3: Test avec variation (FRANPRIX MONTMARTRE)")
    print("-" * 30)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/ml-feedback/merchant-tags/FRANPRIX%20MONTMARTRE",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Tags trouvés pour FRANPRIX MONTMARTRE:")
            print(f"   - Tags: {result.get('tags', [])}")
            print(f"   - Le système devrait reconnaître FRANPRIX")
        else:
            print(f"⚠️ Pas de reconnaissance pour la variation")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 4: Apprentissage multiple
    print("\n📝 Test 4: Apprentissage multiple pour E.LECLERC")
    print("-" * 30)
    
    # Première validation
    payload1 = {
        "transaction_id": 456,
        "label": "E.LECLERC DRIVE",
        "amount": -120.00,
        "selected_tag": "courses",
        "confidence": 1.0,
        "source": "manual"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/ml-feedback/confirm",
            json=payload1,
            headers=headers
        )
        print(f"   Première validation: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Deuxième validation avec un autre tag
    payload2 = {
        "transaction_id": 789,
        "label": "E.LECLERC",
        "amount": -50.00,
        "selected_tag": "alimentation",
        "confidence": 1.0,
        "source": "manual"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/ml-feedback/confirm",
            json=payload2,
            headers=headers
        )
        print(f"   Deuxième validation: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Vérifier les tags appris
    time.sleep(1)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/ml-feedback/merchant-tags/E.LECLERC",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Tags consolidés pour E.LECLERC:")
            print(f"   - Tags: {result.get('tags', [])}")
            print(f"   - Devrait contenir 'courses' et 'alimentation'")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    print("\n" + "=" * 50)
    print("✨ Tests terminés!")

if __name__ == "__main__":
    test_merchant_learning()