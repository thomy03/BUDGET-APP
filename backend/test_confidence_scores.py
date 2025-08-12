#!/usr/bin/env python3
"""
Test des scores de confiance IA pour identifier le problème des 55%
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.expense_classification import ExpenseClassificationService
from models.database import get_db

def test_confidence_scores():
    """Test différents cas pour vérifier les scores de confiance"""
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    # Get classification service
    service = ExpenseClassificationService(db)
    
    # Test cases avec différents niveaux de confiance attendus
    test_cases = [
        # Cas haute confiance FIXED (devrait être >90%)
        {"tag": "netflix", "amount": 15.99, "expected_high": True},
        {"tag": "spotify", "amount": 9.99, "expected_high": True},
        {"tag": "loyer", "amount": 800.0, "expected_high": True},
        {"tag": "assurance auto", "amount": 120.0, "expected_high": True},
        
        # Cas haute confiance VARIABLE (devrait être >90%)
        {"tag": "restaurant", "amount": 25.50, "expected_high": True},
        {"tag": "courses", "amount": 45.30, "expected_high": True},
        {"tag": "essence", "amount": 55.00, "expected_high": True},
        
        # Cas ambigus (devrait être <70%)
        {"tag": "divers", "amount": 10.0, "expected_high": False},
        {"tag": "achat", "amount": 20.0, "expected_high": False},
        {"tag": "paiement", "amount": 15.0, "expected_high": False},
        
        # Cas spécifiques qui pourraient tomber dans le défaut à 55%
        {"tag": "test", "amount": 12.34, "expected_high": False},
        {"tag": "unknown", "amount": 100.0, "expected_high": False},
    ]
    
    print("=== TEST DES SCORES DE CONFIANCE IA ===\n")
    
    problematic_cases = []
    
    for i, case in enumerate(test_cases, 1):
        tag = case["tag"]
        amount = case["amount"]
        expected_high = case["expected_high"]
        
        try:
            # Tester la méthode fast (utilisée par le frontend)
            result_fast = service.classify_expense_fast(
                tag_name=tag,
                transaction_amount=amount,
                transaction_description=""
            )
            
            # Tester la méthode normale
            result_normal = service.classify_expense(
                tag_name=tag,
                transaction_amount=amount,
                transaction_description=""
            )
            
            print(f"{i:2d}. Tag: '{tag}' ({amount}€)")
            print(f"    Fast:   {result_fast.expense_type} - {result_fast.confidence:.3f} - {result_fast.primary_reason}")
            print(f"    Normal: {result_normal.expense_type} - {result_normal.confidence:.3f} - {result_normal.primary_reason}")
            
            # Vérifier si on a le problème des 55%
            if abs(result_fast.confidence - 0.55) < 0.001:
                problematic_cases.append({
                    "tag": tag,
                    "amount": amount,
                    "method": "fast",
                    "confidence": result_fast.confidence
                })
                print(f"    ⚠️  PROBLÈME: Score fixe à 55% détecté (fast)")
            
            if abs(result_normal.confidence - 0.55) < 0.001:
                problematic_cases.append({
                    "tag": tag,
                    "amount": amount,
                    "method": "normal", 
                    "confidence": result_normal.confidence
                })
                print(f"    ⚠️  PROBLÈME: Score fixe à 55% détecté (normal)")
                
            # Vérifier la cohérence des attentes
            if expected_high and result_fast.confidence < 0.7:
                print(f"    ⚠️  ATTENTION: Confiance faible pour cas attendu haute confiance")
            elif not expected_high and result_fast.confidence > 0.8:
                print(f"    ✅ Surprenant: Confiance élevée pour cas attendu ambigu")
                
        except Exception as e:
            print(f"    ❌ ERREUR: {e}")
        
        print()
    
    # Rapport final
    print("\n=== RAPPORT FINAL ===")
    print(f"Total cas testés: {len(test_cases)}")
    print(f"Cas problématiques (55%): {len(problematic_cases)}")
    
    if problematic_cases:
        print("\n⚠️  CAS PROBLÉMATIQUES DÉTECTÉS:")
        for case in problematic_cases:
            print(f"  - Tag: '{case['tag']}' (méthode: {case['method']}) = {case['confidence']:.3f}")
        
        print(f"\n🔍 CAUSE IDENTIFIÉE:")
        print(f"   Valeur hardcodée à 0.55 ligne 321 dans classify_expense_fast()")
        print(f"   Quand confidence_score est entre -0.3 et 0.3 (patterns non conclusifs)")
        
        print(f"\n💡 SOLUTION:")
        print(f"   Remplacer la valeur fixe 0.55 par un calcul dynamique basé sur:")
        print(f"   - Le score de confiance réel de _calculate_fast_confidence")
        print(f"   - Le type de tag (mots reconnus vs inconnus)")
        print(f"   - L'historique des transactions similaires")
    else:
        print("✅ Aucun cas problématique détecté - les scores sont variables")
    
    # Test de la méthode _calculate_fast_confidence directement
    print(f"\n=== TEST DIRECT _calculate_fast_confidence ===")
    confidence_scores = []
    for case in test_cases[:5]:  # Test sur les 5 premiers cas
        text = f"{case['tag']} transaction"
        score = service._calculate_fast_confidence(text, case['amount'])
        confidence_scores.append(score)
        print(f"'{case['tag']}' → confidence_score: {score:.3f}")
    
    # Vérifier si tous les scores sont identiques (signe de problème)
    unique_scores = set(confidence_scores)
    if len(unique_scores) == 1:
        print(f"⚠️  PROBLÈME: Tous les scores identiques = {list(unique_scores)[0]}")
    else:
        print(f"✅ Scores variables détectés: {len(unique_scores)} valeurs uniques")

if __name__ == "__main__":
    test_confidence_scores()