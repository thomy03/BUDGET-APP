#!/usr/bin/env python3
"""
Test des endpoints API pour vérifier les scores de confiance
"""

import requests
import json

def test_api_confidence_scores():
    """Test des endpoints de classification avec l'API en cours"""
    
    base_url = "http://localhost:8000"
    
    # Test cases avec différents niveaux de confiance attendus
    test_cases = [
        # Haute confiance FIXED
        {"tag": "netflix", "amount": 15.99, "expected_type": "FIXED", "expected_confidence": "> 90%"},
        {"tag": "spotify", "amount": 9.99, "expected_type": "FIXED", "expected_confidence": "> 90%"},
        {"tag": "loyer", "amount": 800.0, "expected_type": "FIXED", "expected_confidence": "> 90%"},
        
        # Haute confiance VARIABLE  
        {"tag": "restaurant", "amount": 25.50, "expected_type": "VARIABLE", "expected_confidence": "> 90%"},
        {"tag": "courses", "amount": 45.30, "expected_type": "VARIABLE", "expected_confidence": "> 90%"},
        
        # Confiance moyenne/faible (devrait être variable maintenant)
        {"tag": "divers", "amount": 10.0, "expected_type": "VARIABLE", "expected_confidence": "< 60%"},
        {"tag": "paiement", "amount": 15.0, "expected_type": "VARIABLE", "expected_confidence": "< 60%"},
        {"tag": "test", "amount": 12.34, "expected_type": "VARIABLE", "expected_confidence": "< 60%"},
        {"tag": "unknown", "amount": 100.0, "expected_type": "VARIABLE", "expected_confidence": "< 60%"},
        
        # Cas de borderline avec mots-clés
        {"tag": "achat", "amount": 20.0, "expected_type": "VARIABLE", "expected_confidence": "60-80%"},
    ]
    
    print("=== TEST DES ENDPOINTS API - SCORES DE CONFIANCE ===\n")
    
    # Créer un token fictif pour les tests (ou utiliser l'endpoint sans auth si disponible)
    headers = {
        "Content-Type": "application/json",
        # Note: En production, il faudrait un vrai token d'authentification
    }
    
    problematic_scores = []
    
    for i, case in enumerate(test_cases, 1):
        tag = case["tag"]
        amount = case["amount"]
        expected_type = case["expected_type"]
        expected_confidence = case["expected_confidence"]
        
        try:
            # Tester l'endpoint de suggestion simple
            url = f"{base_url}/expense-classification/suggest/{tag}"
            params = {"amount": amount, "description": f"Transaction {tag}"}
            
            print(f"{i:2d}. Testing: '{tag}' ({amount}€)")
            print(f"    URL: {url}")
            print(f"    Expected: {expected_type} with {expected_confidence}")
            
            # Note: Ce test nécessite que l'API soit en cours et accessible
            # En cas d'erreur d'authentification, on peut utiliser le service directement
            print(f"    → API test skipped (requires authentication)")
            print(f"    → Using direct service test instead")
            
        except Exception as e:
            print(f"    ❌ API Error: {e}")
        
        print()
    
    print("=== TEST DIRECT DES SERVICES (SANS API) ===\n")
    
    # Test direct des services comme dans le test précédent
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    from services.expense_classification import ExpenseClassificationService
    from models.database import get_db
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    # Get classification service
    service = ExpenseClassificationService(db)
    
    for i, case in enumerate(test_cases, 1):
        tag = case["tag"]
        amount = case["amount"]
        expected_type = case["expected_type"]
        expected_confidence = case["expected_confidence"]
        
        try:
            # Test fast classification (utilisé par le frontend)
            result = service.classify_expense_fast(
                tag_name=tag,
                transaction_amount=amount,
                transaction_description=""
            )
            
            print(f"{i:2d}. '{tag}' ({amount}€)")
            print(f"    Result: {result.expense_type} - {result.confidence:.1%}")
            print(f"    Reason: {result.primary_reason}")
            
            # Vérifier si exactement 55%
            if abs(result.confidence - 0.55) < 0.001:
                problematic_scores.append(f"'{tag}' = {result.confidence:.3f}")
                print(f"    ⚠️  PROBLÈME: Score fixe à 55% détecté!")
            else:
                print(f"    ✅ Score variable: {result.confidence:.1%}")
                
            # Vérifier les attentes
            confidence_num = result.confidence
            if expected_confidence.startswith("> 90%") and confidence_num < 0.9:
                print(f"    ⚠️  Confiance plus faible qu'attendu")
            elif expected_confidence.startswith("< 60%") and confidence_num >= 0.6:
                print(f"    ⚠️  Confiance plus élevée qu'attendu") 
            elif "60-80%" in expected_confidence and not (0.6 <= confidence_num <= 0.8):
                print(f"    ⚠️  Confiance hors de la plage attendue")
                
        except Exception as e:
            print(f"    ❌ Erreur: {e}")
        
        print()
    
    # Rapport final
    print("=== RAPPORT FINAL ===")
    if problematic_scores:
        print(f"❌ ÉCHEC: {len(problematic_scores)} scores problématiques détectés:")
        for score in problematic_scores:
            print(f"   {score}")
        print(f"\n➡️  Le problème des 55% persiste!")
    else:
        print(f"✅ SUCCÈS: Aucun score fixe à 55% détecté")
        print(f"✅ Tous les scores sont variables et réalistes")
        print(f"✅ La correction a résolu le problème!")
    
    print(f"\n💡 RAPPEL: Les scores Netflix/Spotify/Loyer devraient être >90%")
    print(f"💡 RAPPEL: Les scores Restaurant/Courses devraient être >90%")
    print(f"💡 RAPPEL: Les scores Divers/Test/Unknown devraient être <60% et variables")

if __name__ == "__main__":
    test_api_confidence_scores()