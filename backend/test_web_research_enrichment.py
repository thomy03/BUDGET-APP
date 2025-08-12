#!/usr/bin/env python3
"""
Test et démonstration de l'enrichissement web pour le système d'auto-tagging
"""

import asyncio
import json
from services.web_research_service import WebResearchService
from services.ml_tagging_engine import MLTaggingEngine

async def test_web_research():
    """Test la recherche web sur différents types de marchands"""
    
    test_merchants = [
        ("NETFLIX", 15.99),
        ("CARREFOUR CITY PARIS", 45.67),
        ("AMAZON MARKETPLACE", 89.99),
        ("UBER EATS", 24.50),
        ("FNAC LYON", 129.99),
        ("SNCF TER", 35.00),
        ("SPOTIFY PREMIUM", 9.99),
        ("LECLERC DRIVE", 156.78)
    ]
    
    print("🔍 Test de recherche web et enrichissement automatique\n")
    print("=" * 70)
    
    # Initialiser le moteur ML avec recherche web
    engine = MLTaggingEngine()
    
    for merchant, amount in test_merchants:
        print(f"\n📍 Traitement: {merchant} ({amount}€)")
        print("-" * 50)
        
        # Obtenir la classification avec recherche web
        result = await engine.suggest_tag(
            transaction_label=merchant,
            amount=amount,
            use_web_research=True
        )
        
        print(f"✅ Tag suggéré: {result.suggested_tag}")
        print(f"📊 Confiance totale: {result.confidence:.2%}")
        print(f"🔎 Recherche web effectuée: {'Oui' if result.web_research_performed else 'Non'}")
        
        if result.web_research_performed:
            print(f"🌐 Type business (web): {result.web_business_type or 'Non trouvé'}")
            print(f"📈 Confiance web: {result.web_confidence:.2%}")
        
        print(f"💼 Type de dépense: {result.expense_type}")
        print(f"📝 Sources de données: {', '.join(result.data_sources)}")
        
        # Afficher les facteurs de confiance
        cf = result.confidence_factors
        print(f"\n📊 Détail des facteurs de confiance:")
        print(f"  • Pattern matching: {cf.pattern_match_score:.2%}")
        print(f"  • Recherche web: {cf.web_research_score:.2%}")
        print(f"  • Apprentissage: {cf.user_feedback_score:.2%}")
        print(f"  • Contexte: {cf.context_score:.2%}")
        
        if result.alternative_tags:
            print(f"\n🔄 Tags alternatifs: {', '.join(result.alternative_tags[:3])}")
    
    print("\n" + "=" * 70)
    print("✅ Test terminé - La recherche web enrichit bien la base de données!")

async def test_merchant_knowledge_base():
    """Vérifie l'enrichissement de la base de connaissances des marchands"""
    
    import sqlite3
    
    print("\n\n📚 Vérification de la base de connaissances des marchands")
    print("=" * 70)
    
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()
    
    # Compter les entrées avant et après
    cursor.execute("SELECT COUNT(*) FROM merchant_knowledge_base")
    count_before = cursor.fetchone()[0]
    print(f"Entrées avant enrichissement: {count_before}")
    
    # Tester l'enrichissement avec de nouveaux marchands
    async with WebResearchService() as research_service:
        new_merchants = [
            "DECATHLON PARIS",
            "APPLE STORE",
            "IKEA FRANCE"
        ]
        
        for merchant in new_merchants:
            print(f"\n🔍 Recherche pour: {merchant}")
            merchant_info = await research_service.research_merchant(merchant, 100.0)
            
            if merchant_info:
                print(f"  ✅ Trouvé: {merchant_info.business_type}")
                print(f"  📍 Catégorie: {merchant_info.category}")
                print(f"  🏷️ Tags: {', '.join(merchant_info.suggested_tags or [])}")
                print(f"  📊 Confiance: {merchant_info.confidence_score:.2%}")
                
                # Sauvegarder dans la base
                success = await research_service.save_to_knowledge_base(merchant_info)
                if success:
                    print(f"  💾 Sauvegardé dans la base de connaissances")
    
    # Vérifier le nouvel état
    cursor.execute("SELECT COUNT(*) FROM merchant_knowledge_base")
    count_after = cursor.fetchone()[0]
    print(f"\nEntrées après enrichissement: {count_after}")
    print(f"Nouvelles entrées ajoutées: {count_after - count_before}")
    
    # Afficher les dernières entrées
    cursor.execute("""
        SELECT merchant_name, business_type, suggested_tags, confidence_score
        FROM merchant_knowledge_base
        ORDER BY created_at DESC
        LIMIT 3
    """)
    
    print("\nDernières entrées dans la base:")
    for row in cursor.fetchall():
        print(f"  • {row[0]}: {row[1]} | Tags: {row[2]} | Confiance: {row[3]:.2%}")
    
    conn.close()

if __name__ == "__main__":
    print("🚀 Démarrage des tests d'enrichissement web\n")
    
    # Test 1: Recherche web et classification
    asyncio.run(test_web_research())
    
    # Test 2: Base de connaissances
    asyncio.run(test_merchant_knowledge_base())
    
    print("\n✨ Tous les tests sont terminés!")
    print("La recherche web enrichit automatiquement la base de données à chaque classification.")