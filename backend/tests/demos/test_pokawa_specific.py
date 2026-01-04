#!/usr/bin/env python3
"""Test spécifique du pattern POKAWA appris"""

from services.ml_feedback_learning import MLFeedbackLearningService
from models.database import get_db

def test_pokawa_pattern():
    """Test le pattern POKAWA appris"""
    db = next(get_db())
    
    try:
        ml_service = MLFeedbackLearningService(db)
        
        # Test sur la transaction POKAWA exacte
        result = ml_service.classify_with_feedback(
            transaction_label="CARTE 22/11/24 Pokawa St Maur F CB*8533",
            amount=-21.3
        )
        
        print(f"🧪 TEST TRANSACTION POKAWA:")
        print(f"Label: CARTE 22/11/24 Pokawa St Maur F CB*8533")
        print(f"Montant: -21.3€")
        print(f"")
        print(f"🤖 RÉSULTAT ML:")
        print(f"Tag suggéré: {result.suggested_tag}")
        print(f"Type: {result.expense_type}")
        print(f"Confiance: {result.confidence:.3f}")
        print(f"Explication: {result.tag_explanation}")
        print(f"Alternatives: {result.alternative_tags}")
        
        if result.confidence > 0.5 and result.suggested_tag == "restaurant":
            print(f"")
            print(f"🎉 SUCCÈS TOTAL! L'apprentissage ML fonctionne:")
            print(f"   ✅ Confiance suffisante: {result.confidence:.3f} > 0.5")
            print(f"   ✅ Tag correct suggéré: '{result.suggested_tag}'")
            print(f"   ✅ Le système a appris que POKAWA = restaurant")
        elif result.suggested_tag == "restaurant":
            print(f"✅ Tag correct mais confiance faible")
        else:
            print(f"⚠️  Problème d'apprentissage")
        
        # Test variations
        variations = [
            "POKAWA PARIS",
            "CARTE POKAWA CB*1234",
            "31/12/24 POKAWA BONNEUIL"
        ]
        
        print(f"\n🧪 TEST VARIATIONS:")
        for var in variations:
            result_var = ml_service.classify_with_feedback(
                transaction_label=var,
                amount=-15.0
            )
            print(f"  {var} -> {result_var.suggested_tag} ({result_var.confidence:.2f})")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_pokawa_pattern()