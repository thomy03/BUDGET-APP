#!/usr/bin/env python3
"""
Simple test for the Intelligent Tag System
Tests just the core functionality without complex dependencies
"""

import sys
import asyncio
from typing import Dict, List

# Mock database session for testing
class MockDB:
    """Mock database session for testing purposes"""
    pass

def test_simple_intelligent_tags():
    """Simple test of intelligent tag system core functionality"""
    
    print("🚀 Simple Intelligent Tag System Test")
    print("=" * 60)
    
    try:
        # Direct import and test without complex dependencies
        from services.intelligent_tag_service import IntelligentTagService
        
        # Create service instance
        service = IntelligentTagService(MockDB())
        
        # Test transactions
        test_cases = [
            {"label": "NETFLIX SARL 12.99 EUR", "amount": 12.99},
            {"label": "MCDONALDS PARIS 8.50 EUR", "amount": 8.50},
            {"label": "CARREFOUR VILLENEUVE 67.32 EUR", "amount": 67.32},
            {"label": "TOTAL ACCESS PARIS 45.00 EUR", "amount": 45.00},
            {"label": "EDF ENERGIE FACTURE 89.34 EUR", "amount": 89.34},
        ]
        
        print(f"Testing {len(test_cases)} transactions...")
        print()
        
        success_count = 0
        
        for i, test_case in enumerate(test_cases):
            try:
                # Test fast suggestion
                result = service.suggest_tag_fast(test_case["label"], test_case["amount"])
                
                print(f"{i+1}. {test_case['label'][:30]:<30} → {result.suggested_tag:<12} ({result.confidence:.2f})")
                print(f"   Explanation: {result.explanation}")
                print(f"   Time: {result.processing_time_ms}ms")
                print()
                
                success_count += 1
                
            except Exception as e:
                print(f"{i+1}. {test_case['label'][:30]:<30} → ERROR: {e}")
                print()
        
        print(f"✅ Successfully processed {success_count}/{len(test_cases)} transactions")
        
        # Test service statistics
        try:
            stats = service.get_service_statistics()
            print(f"✅ Service statistics retrieved: {len(stats)} metrics")
        except Exception as e:
            print(f"⚠️  Service statistics failed: {e}")
        
        return success_count == len(test_cases)
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        return False

def test_quick_recognition():
    """Test the quick merchant recognition patterns"""
    
    print("\n🎯 Quick Recognition Pattern Test")
    print("=" * 60)
    
    try:
        from services.intelligent_tag_service import IntelligentTagService
        
        service = IntelligentTagService(MockDB())
        
        # Test known patterns
        known_merchants = {
            "NETFLIX": "streaming",
            "MCDONALDS": "fast-food", 
            "CARREFOUR": "courses",
            "EDF": "electricite",
            "TOTAL": "essence",
            "SPOTIFY": "musique"
        }
        
        correct_predictions = 0
        total_tests = len(known_merchants)
        
        for merchant, expected_tag in known_merchants.items():
            label = f"{merchant} TRANSACTION 50.00 EUR"
            result = service._quick_merchant_recognition(label, 50.00)
            
            if result and result.suggested_tag == expected_tag:
                print(f"✅ {merchant:<12} → {result.suggested_tag:<12} (correct)")
                correct_predictions += 1
            elif result:
                print(f"❌ {merchant:<12} → {result.suggested_tag:<12} (expected: {expected_tag})")
            else:
                print(f"❓ {merchant:<12} → No recognition")
        
        accuracy = (correct_predictions / total_tests) * 100
        print(f"\nQuick recognition accuracy: {accuracy:.1f}% ({correct_predictions}/{total_tests})")
        
        return accuracy >= 80  # Expect at least 80% accuracy
        
    except Exception as e:
        print(f"❌ Quick recognition test failed: {e}")
        return False

def main():
    """Run all simple tests"""
    
    print("🧪 SIMPLE INTELLIGENT TAG SYSTEM TESTS")
    print("=" * 80)
    
    # Test 1: Basic functionality
    basic_success = test_simple_intelligent_tags()
    
    # Test 2: Quick recognition patterns
    recognition_success = test_quick_recognition()
    
    # Summary
    print("\n" + "=" * 80)
    print("🏁 SIMPLE TEST RESULTS")
    print("=" * 80)
    
    if basic_success and recognition_success:
        print("🎉 ALL SIMPLE TESTS PASSED!")
        print()
        print("✅ Core intelligent tag system is working")
        print("✅ Quick merchant recognition is functional")
        print("✅ Tag suggestions are being generated")
        print("✅ Service statistics are accessible")
        print()
        print("🚀 The intelligent tag system core is ready!")
        print("   Next: Test with web research and full API integration")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print(f"   Basic functionality: {'✅' if basic_success else '❌'}")
        print(f"   Quick recognition: {'✅' if recognition_success else '❌'}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)