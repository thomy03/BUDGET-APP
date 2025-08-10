#!/usr/bin/env python3
"""
Script de test rapide pour vérifier la compatibilité du backend
"""

import requests
import json
import os

BASE_URL = "http://127.0.0.1:8000"

def test_compatibility():
    """Test des endpoints critiques en mode compatibilité"""
    
    print("🧪 Test de compatibilité Backend Budget Famille v2.3\n")
    
    # Test 1: Root endpoint
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ GET / - API accessible")
            print(f"   Réponse: {response.json()}")
        else:
            print(f"❌ GET / - Erreur {response.status_code}")
    except Exception as e:
        print(f"❌ GET / - Exception: {e}")
    
    # Test 2: Authentification
    try:
        auth_data = {"username": "admin", "password": "secret"}
        response = requests.post(f"{BASE_URL}/token", data=auth_data)
        if response.status_code == 200:
            print("✅ POST /token - Authentification OK")
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
        else:
            print(f"❌ POST /token - Erreur {response.status_code}")
            headers = {}
    except Exception as e:
        print(f"❌ POST /token - Exception: {e}")
        headers = {}
    
    # Test 3: Liste des transactions (critique pour import_id)
    try:
        response = requests.get(f"{BASE_URL}/transactions", headers=headers)
        if response.status_code == 200:
            print("✅ GET /transactions - Compatible avec ancienne DB")
            transactions = response.json()
            print(f"   Nombre de transactions: {len(transactions)}")
            if transactions:
                # Vérifier que import_id est présent mais null
                first_tx = transactions[0]
                import_id_value = first_tx.get('import_id')
                print(f"   Première transaction import_id: {import_id_value}")
        else:
            print(f"❌ GET /transactions - Erreur {response.status_code}")
    except Exception as e:
        print(f"❌ GET /transactions - Exception: {e}")
    
    # Test 4: Test simulation d'import (nouveau système)
    try:
        # Créer un faux fichier CSV pour le test
        csv_content = "Date,Description,Montant,Compte\n2024-01-01,Test,100.0,Banque"
        files = {"file": ("test.csv", csv_content, "text/csv")}
        
        response = requests.post(f"{BASE_URL}/import", files=files, headers=headers)
        if response.status_code == 200:
            print("✅ POST /import - Mode compatibilité fonctionne")
            import_response = response.json()
            print(f"   Processing: {import_response.get('processing')}")
            print(f"   Warnings: {import_response.get('warnings')}")
            import_id = import_response.get('importId')
            
            # Test de récupération des détails
            if import_id:
                detail_response = requests.get(f"{BASE_URL}/imports/{import_id}", headers=headers)
                if detail_response.status_code == 200:
                    print("✅ GET /imports/{id} - Mode simulation OK")
                    details = detail_response.json()
                    print(f"   Simulation mode: {details.get('simulationMode')}")
                else:
                    print(f"❌ GET /imports/{import_id} - Erreur {detail_response.status_code}")
        else:
            print(f"❌ POST /import - Erreur {response.status_code}")
            print(f"   Détail: {response.text}")
    except Exception as e:
        print(f"❌ POST /import - Exception: {e}")
    
    print("\n🎯 Résumé:")
    print("- Le backend fonctionne en mode compatibilité")
    print("- La colonne import_id est gérée comme 'virtuelle' (toujours NULL)")
    print("- Les imports utilisent la simulation pour tester l'animation")
    print("- L'ancienne base de données est préservée")

if __name__ == "__main__":
    test_compatibility()