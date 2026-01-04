#!/usr/bin/env python3
"""Test spécifique d'apprentissage ML pour FRANPRIX"""

from sqlalchemy.orm import Session
from models.database import get_db
from services.ml_feedback_learning import MLFeedbackLearningService

def test_franprix_learning():
    """Test l'apprentissage ML spécifiquement pour FRANPRIX"""
    db = next(get_db())
    
    try:
        # Initialiser le service ML
        ml_service = MLFeedbackLearningService(db)
        print(f"🧠 ML service avec {len(ml_service.feedback_patterns)} patterns:")
        
        for pattern_key, pattern in ml_service.feedback_patterns.items():
            print(f"  • {pattern_key}: {pattern.learned_tag} ({pattern.confidence_score:.2f})")
        
        # Test avec différentes variantes de FRANPRIX
        test_cases = [
            "CARTE 24/11/24 FRANPRIX CB*8533",  # Format exact de la correction
            "CARTE 25/11/24 FRANPRIX CB*1234",  # Autre date
            "FRANPRIX BONNEUIL",                # Format simplifié
            "CARTE FRANPRIX CB*5678",          # Sans date
            "24/11/24 FRANPRIX CB*8533"        # Sans CARTE
        ]
        
        print(f"\n🧪 TEST DE L'APPRENTISSAGE FRANPRIX:")
        
        for i, test_label in enumerate(test_cases, 1):
            print(f"\n--- Test {i}: {test_label} ---")
            
            # Test ML classification
            result = ml_service.classify_with_feedback(
                transaction_label=test_label,
                amount=-7.67  # Même montant que l'exemple
            )
            
            # Normaliser le nom marchand pour debug
            normalized = ml_service.normalize_merchant_name(test_label)
            print(f"Nom normalisé: '{normalized}'")
            print(f"Tag suggéré: {result.suggested_tag}")
            print(f"Type: {result.expense_type}")
            print(f"Confiance: {result.confidence:.3f}")
            print(f"Explication: {result.tag_explanation}")
            
            if result.confidence > 0.5:
                print(f"✅ APPRENTISSAGE ML ACTIVÉ!")
            else:
                print(f"⚠️  ML insuffisant")
        
        # Afficher les statistiques des patterns
        print(f"\n📊 STATISTIQUES DES PATTERNS:")
        stats = ml_service.get_pattern_statistics()
        print(f"Total patterns: {stats['total_patterns']}")
        print(f"Patterns haute confiance: {stats['high_confidence_patterns']}")
        print(f"Patterns fréquents: {stats['frequently_used_patterns']}")
        print(f"Confiance moyenne: {stats['average_confidence']:.3f}")
        print(f"Patterns de correction: {stats['correction_patterns']}")
        
        if stats['top_patterns']:
            print(f"\nTop patterns:")
            for p in stats['top_patterns']:
                print(f"  • {p['pattern']}: {p['tag']} (confiance: {p['confidence']:.2f}, utilisé: {p['usage_count']} fois)")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    test_franprix_learning()