#!/usr/bin/env python3
"""
Test script pour vérifier les endpoints de classification
"""

import sys
import os
sys.path.append('.')

from fastapi.testclient import TestClient
from app import app
from models.database import SessionLocal, Transaction
from sqlalchemy import text

def test_classification_endpoints():
    """Test les nouveaux endpoints de classification"""
    
    client = TestClient(app)
    
    print("🧪 Test des endpoints de classification")
    print("=" * 50)
    
    # 1. Obtenir une transaction existante pour le test
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT id, label, tags FROM transactions WHERE tags IS NOT NULL AND tags != '' LIMIT 1")).fetchone()
        if not result:
            print("❌ Aucune transaction avec tags trouvée pour le test")
            return False
            
        transaction_id = result.id
        label = result.label
        tags = result.tags
        
        print(f"✅ Transaction de test trouvée:")
        print(f"   ID: {transaction_id}")  
        print(f"   Label: {label}")
        print(f"   Tags: {tags}")
        print()
        
    finally:
        db.close()
    
    # 2. Test de l'endpoint de classification individuelle
    print(f"🔍 Test: POST /expense-classification/classify/{transaction_id}")
    
    try:
        # Créer un utilisateur mock pour bypasser l'auth temporairement
        from unittest.mock import patch
        
        # Mock user object
        class MockUser:
            username = "test_user"
            
        mock_user = MockUser()
        
        # Patcher la dépendance d'authentification
        with patch('routers.classification.get_current_user', return_value=mock_user):
            response = client.post(f"/expense-classification/classify/{transaction_id}")
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Classification réussie!")
                print(f"   Transaction ID: {data.get('transaction_id')}")
                print(f"   Type suggéré: {data.get('suggested_type')}")
                print(f"   Confiance: {data.get('confidence_score', 0):.2f}")
                print(f"   Raisonnement: {data.get('reasoning', 'N/A')[:100]}...")
                print(f"   Tag utilisé: {data.get('tag_name', 'N/A')}")
                
            elif response.status_code == 404:
                print(f"❌ Transaction {transaction_id} non trouvée")
                print(f"   Réponse: {response.text}")
                return False
                
            else:
                print(f"❌ Erreur {response.status_code}")
                print(f"   Réponse: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # 3. Test de l'endpoint de classification mensuelle
    print("🔍 Test: POST /expense-classification/classify-month")
    
    try:
        with patch('routers.classification.get_current_user', return_value=mock_user):
            # Obtenir un mois avec des transactions
            db = SessionLocal()
            try:
                month_result = db.execute(text("SELECT DISTINCT month FROM transactions WHERE tags IS NOT NULL AND tags != '' LIMIT 1")).fetchone()
                if not month_result:
                    print("❌ Aucun mois avec transactions taggées trouvé")
                    return False
                    
                test_month = month_result.month
                print(f"   Test avec le mois: {test_month}")
                
            finally:
                db.close()
            
            response = client.post(
                "/expense-classification/classify-month",
                json={"month": test_month}
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Classification mensuelle réussie!")
                print(f"   Nombre de classifications: {len(data)}")
                
                if data:
                    first_result = data[0]
                    print(f"   Exemple - Transaction ID: {first_result.get('transaction_id')}")
                    print(f"   Exemple - Type suggéré: {first_result.get('suggested_type')}")
                    print(f"   Exemple - Confiance: {first_result.get('confidence_score', 0):.2f}")
                
            else:
                print(f"❌ Erreur {response.status_code}")
                print(f"   Réponse: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Erreur lors du test mensuel: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("🎉 Tous les tests de classification sont passés avec succès!")
    return True

if __name__ == "__main__":
    success = test_classification_endpoints()
    sys.exit(0 if success else 1)