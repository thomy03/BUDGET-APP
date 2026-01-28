#!/usr/bin/env python3
"""Test de détection des hôtels et Deliveroo"""

import asyncio
from services.web_research_service import WebResearchService

async def test_detection():
    service = WebResearchService()
    
    test_cases = [
        "CARTE 10/08/24 UNIVERSAL HOTEL F CB*8533",
        "CARTE 09/11/24 Deliveroo CB*8533",
        "VIR Virement 1er hotel Majorque",
        "HOTEL IBIS PARIS",
        "BOOKING.COM RESERVATION",
        "AIRBNB PARIS"
    ]
    
    print("🧪 Test de détection des patterns hôtels et restaurants")
    print("=" * 60)
    
    for label in test_cases:
        # Test classification directe
        business_type, confidence, keywords = service.classify_by_keywords(label)
        
        if business_type:
            config = service.business_patterns[business_type]
            print(f"\n✅ {label}")
            print(f"   Type: {business_type}")
            print(f"   Confiance: {confidence:.2%}")
            print(f"   Tags suggérés: {config['tags']}")
            print(f"   Mots-clés détectés: {keywords}")
        else:
            print(f"\n❌ {label}")
            print(f"   Aucune détection")
    
    print("\n" + "=" * 60)
    print("Test terminé!")

if __name__ == "__main__":
    asyncio.run(test_detection())