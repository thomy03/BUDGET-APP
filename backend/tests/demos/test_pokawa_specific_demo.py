#!/usr/bin/env python3
"""
Specific test for POKAWA merchant recognition
Demonstrates the fuzzy matching system's ability to recognize POKAWA variations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.core_functions import (
    normalize_merchant_name_enhanced,
    compute_similarity_score,
    create_merchant_inverted_index,
    fast_merchant_lookup
)

def demonstrate_pokawa_recognition():
    """Demonstrate POKAWA merchant recognition"""
    print("🥢 POKAWA Merchant Recognition Demo")
    print("=" * 50)
    
    # Simulate a learned pattern for POKAWA
    learned_patterns = {
        "pokawa": {
            "learned_tag": "Restaurant",
            "learned_expense_type": "VARIABLE",
            "confidence_score": 0.95,
            "usage_count": 25,
            "success_rate": 0.98
        }
    }
    
    # Create inverted index
    inverted_index = create_merchant_inverted_index(learned_patterns)
    
    # Real-world POKAWA transaction variations
    pokawa_variations = [
        "CB POKAWA PARIS 75001 15/11 12:30",
        "CARTE POKAWA 75008 CHAMPS ELYSEES",
        "POKAWA PARIS 2EME ARRONDISSEMENT",
        "POKAWA LYON PART DIEU",
        "POKAWA SAS CHATELET",
        "POKAWA BOULOGNE BILLANCOURT",
        "CB POKAWA NATION 75011",
        "POKAWA EXPRESS GARE DU NORD",
        "POKAWA DELIVERY PARIS",
        "pokawa",  # Simple case
        "POKAWA",  # Uppercase
        "Pokawa Paris",  # Mixed case
        # Edge cases
        "POKE BOWL POKAWA RESTAURANT",
        "POKAWA SUSHI & POKE",
        "CB POKAWA RESTO 75001 15:30",
    ]
    
    print("\n📊 Testing POKAWA Variations Recognition:")
    print("-" * 50)
    
    successful_matches = 0
    total_tests = len(pokawa_variations)
    
    for i, variation in enumerate(pokawa_variations, 1):
        print(f"\n{i:2d}. Input: '{variation}'")
        
        # Normalize
        normalized = normalize_merchant_name_enhanced(variation)
        print(f"    Normalized: '{normalized}'")
        
        # Find matches
        matches = fast_merchant_lookup(
            variation, 
            learned_patterns, 
            inverted_index,
            threshold=0.8
        )
        
        if matches:
            pattern_key, similarity = matches[0]
            pattern = learned_patterns[pattern_key]
            
            print(f"    ✅ MATCHED: '{pattern_key}' (similarity: {similarity:.3f})")
            print(f"       Tag: {pattern['learned_tag']}")
            print(f"       Confidence: {pattern['confidence_score']:.2f}")
            print(f"       Final confidence: {pattern['confidence_score'] * similarity:.3f}")
            
            successful_matches += 1
        else:
            print(f"    ❌ NO MATCH found above threshold")
    
    # Results summary
    print("\n" + "=" * 50)
    print("📈 RECOGNITION RESULTS:")
    print(f"   Successfully matched: {successful_matches}/{total_tests} ({successful_matches/total_tests*100:.1f}%)")
    print(f"   Failed to match: {total_tests - successful_matches}/{total_tests}")
    
    if successful_matches >= total_tests * 0.9:
        print("   🎉 EXCELLENT: System recognizes POKAWA variations very well!")
    elif successful_matches >= total_tests * 0.8:
        print("   ✅ GOOD: System recognizes most POKAWA variations!")
    else:
        print("   ⚠️  NEEDS IMPROVEMENT: Some variations not recognized")
    
    return successful_matches / total_tests

def test_other_merchants_with_pokawa():
    """Test that POKAWA doesn't match unrelated merchants"""
    print("\n\n🔍 Testing Specificity (avoiding false positives)")
    print("=" * 50)
    
    learned_patterns = {
        "pokawa": {"learned_tag": "Restaurant", "confidence_score": 0.95},
        "franprix": {"learned_tag": "Alimentation", "confidence_score": 0.90},
        "carrefour": {"learned_tag": "Hypermarché", "confidence_score": 0.92}
    }
    
    inverted_index = create_merchant_inverted_index(learned_patterns)
    
    # These should NOT match POKAWA
    non_pokawa_merchants = [
        "FRANPRIX EXPRESS PARIS",
        "CARREFOUR MARKET BOULOGNE",
        "MCDONALDS CHAMPS ELYSEES",
        "STARBUCKS COFFEE OPERA",
        "MONOPRIX GRENELLE",
        "PICARD SURGELES",
        "LECLERC DRIVE",
        "SUSHI SHOP PARIS",  # Similar food category but different
        "PANDA WOK",  # Similar name pattern but different
        "RANDOM RESTAURANT 123"
    ]
    
    false_positives = 0
    
    for merchant in non_pokawa_merchants:
        matches = fast_merchant_lookup(merchant, learned_patterns, inverted_index, threshold=0.8)
        
        # Check if it incorrectly matched POKAWA
        pokawa_match = any(match[0] == "pokawa" for match in matches)
        
        if pokawa_match:
            false_positives += 1
            print(f"❌ FALSE POSITIVE: '{merchant}' incorrectly matched POKAWA")
        else:
            if matches:
                best_match = matches[0]
                print(f"✅ '{merchant}' correctly matched '{best_match[0]}' (not POKAWA)")
            else:
                print(f"✅ '{merchant}' no match (correctly not POKAWA)")
    
    print(f"\n📊 SPECIFICITY RESULTS:")
    print(f"   False positives: {false_positives}/{len(non_pokawa_merchants)}")
    print(f"   Specificity: {(len(non_pokawa_merchants) - false_positives)/len(non_pokawa_merchants)*100:.1f}%")
    
    return false_positives == 0

def main():
    """Run POKAWA-specific tests"""
    print("🧪 POKAWA Merchant Recognition System Test")
    print("Testing the ML feedback learning fuzzy matching capabilities")
    print("=" * 60)
    
    try:
        # Test POKAWA recognition
        recognition_rate = demonstrate_pokawa_recognition()
        
        # Test specificity
        specificity_good = test_other_merchants_with_pokawa()
        
        # Final assessment
        print("\n" + "=" * 60)
        print("🎯 FINAL ASSESSMENT:")
        print(f"   POKAWA Recognition Rate: {recognition_rate*100:.1f}%")
        print(f"   Specificity (no false positives): {'✅ PASS' if specificity_good else '❌ FAIL'}")
        
        if recognition_rate >= 0.9 and specificity_good:
            print("\n🏆 SYSTEM PERFORMANCE: EXCELLENT")
            print("   The fuzzy matching system successfully:")
            print("   ✅ Recognizes POKAWA, POKAWA PARIS, POKAWA 75001 as the same merchant")
            print("   ✅ Handles various banking transaction formats")
            print("   ✅ Maintains high specificity (no false positives)")
            print("   ✅ Uses 80%+ similarity threshold effectively")
        elif recognition_rate >= 0.8:
            print("\n✅ SYSTEM PERFORMANCE: GOOD")
            print("   System works well but could be improved")
        else:
            print("\n⚠️  SYSTEM PERFORMANCE: NEEDS IMPROVEMENT")
            
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()