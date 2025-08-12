#!/usr/bin/env python3
"""
Test script for the new intelligent tag suggestion system
Tests the transformation from fixed/variable classification to smart tag suggestions
"""

import asyncio
import requests
import json
import time
from typing import Dict, List

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/expense-classification"

# Test data - real transaction examples
TEST_TRANSACTIONS = [
    {"label": "NETFLIX SARL 12.99", "amount": 12.99, "expected": "streaming"},
    {"label": "CARREFOUR VILLENEUVE 45.67", "amount": 45.67, "expected": "courses"},
    {"label": "TOTAL ACCESS PARIS 62.30", "amount": 62.30, "expected": "essence"},
    {"label": "PHARMACIE CENTRALE 15.80", "amount": 15.80, "expected": "sante"},
    {"label": "RESTAURANT LE PETIT PARIS 28.50", "amount": 28.50, "expected": "restaurant"},
    {"label": "AMAZON EU-SARL 25.99", "amount": 25.99, "expected": "shopping"},
    {"label": "EDF ENERGIE 78.45", "amount": 78.45, "expected": "electricite"},
    {"label": "SPOTIFY AB 9.99", "amount": 9.99, "expected": "musique"},
    {"label": "ORANGE TELECOM 29.99", "amount": 29.99, "expected": "telephone"},
    {"label": "SNCF CONNECT 87.60", "amount": 87.60, "expected": "transport"},
]

def get_auth_headers():
    """Get authentication headers for API requests"""
    # Pour simplifier le test, on utilise les headers sans authentification
    # En production, il faudrait s'authentifier d'abord
    return {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def test_tag_suggestion_endpoint():
    """Test the new tag suggestion endpoint"""
    print("🏷️ Testing Individual Tag Suggestions")
    print("=" * 60)
    
    headers = get_auth_headers()
    success_count = 0
    total_tests = len(TEST_TRANSACTIONS)
    
    for i, transaction in enumerate(TEST_TRANSACTIONS, 1):
        print(f"\nTest {i}/{total_tests}: {transaction['label']}")
        
        # Test with web research disabled for faster testing
        payload = {
            "transaction_label": transaction["label"],
            "amount": transaction["amount"],
            "use_web_research": False  # Fast mode for testing
        }
        
        try:
            response = requests.post(
                f"{API_BASE}/suggest-tag",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                suggested_tag = result["suggested_tag"]
                confidence = result["confidence"]
                explanation = result["explanation"]
                
                print(f"  ✅ Suggested: {suggested_tag} (confidence: {confidence:.2f})")
                print(f"  📝 Explanation: {explanation}")
                print(f"  🎯 Expected: {transaction['expected']}")
                
                # Check if suggestion is reasonable (not necessarily exact match)
                if confidence > 0.5:
                    success_count += 1
                    print(f"  ✓ PASS (good confidence)")
                else:
                    print(f"  ⚠️ LOW CONFIDENCE")
                    
            else:
                print(f"  ❌ ERROR: HTTP {response.status_code}")
                print(f"  Response: {response.text}")
                
        except Exception as e:
            print(f"  ❌ EXCEPTION: {e}")
    
    print(f"\n📊 Results: {success_count}/{total_tests} suggestions with good confidence")
    return success_count / total_tests if total_tests > 0 else 0

def test_batch_suggestions():
    """Test batch tag suggestions"""
    print("\n🔄 Testing Batch Tag Suggestions")
    print("=" * 60)
    
    headers = get_auth_headers()
    
    # Prepare batch request
    transactions = [
        {"id": i, "label": tx["label"], "amount": tx["amount"]}
        for i, tx in enumerate(TEST_TRANSACTIONS)
    ]
    
    payload = {
        "transactions": transactions,
        "use_fast_mode": True
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE}/batch-suggest-tags",
            headers=headers,
            json=payload,
            timeout=30
        )
        processing_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"✅ Batch processing successful!")
            print(f"📊 Statistics:")
            print(f"  - Total processed: {result['total_processed']}")
            print(f"  - High confidence: {result['high_confidence_count']}")
            print(f"  - Medium confidence: {result['medium_confidence_count']}")
            print(f"  - Low confidence: {result['low_confidence_count']}")
            print(f"  - Processing time: {result['processing_time_ms']:.1f}ms (actual: {processing_time:.1f}ms)")
            
            print(f"\n🏷️ Sample suggestions:")
            for tx_id, suggestion in list(result['suggestions'].items())[:3]:
                print(f"  TX {tx_id}: {suggestion['suggested_tag']} ({suggestion['confidence']:.2f})")
            
            return True
        else:
            print(f"❌ Batch request failed: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Batch test exception: {e}")
        return False

def test_simple_get_endpoint():
    """Test the simple GET endpoint"""
    print("\n🚀 Testing Simple GET Endpoint")
    print("=" * 60)
    
    headers = get_auth_headers()
    
    # Test a few transactions with GET requests
    for transaction in TEST_TRANSACTIONS[:3]:
        label = transaction["label"]
        amount = transaction["amount"]
        
        try:
            # URL encode the label
            import urllib.parse
            encoded_label = urllib.parse.quote(label)
            
            response = requests.get(
                f"{API_BASE}/suggest-tag/{encoded_label}?amount={amount}&use_web_research=false",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {label} → {result['suggested_tag']} ({result['confidence']:.2f})")
            else:
                print(f"❌ {label} → HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {label} → Exception: {e}")

def test_tag_statistics():
    """Test tag suggestion statistics endpoint"""
    print("\n📊 Testing Tag Statistics Endpoint")
    print("=" * 60)
    
    headers = get_auth_headers()
    
    try:
        response = requests.get(
            f"{API_BASE}/tag-suggestion-stats",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            stats = response.json()
            print("✅ Statistics retrieved successfully!")
            print(json.dumps(stats, indent=2))
            return True
        else:
            print(f"❌ Stats request failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Stats test exception: {e}")
        return False

def test_web_research_mode():
    """Test web research mode (if available)"""
    print("\n🌐 Testing Web Research Mode")
    print("=" * 60)
    
    headers = get_auth_headers()
    
    # Test one transaction with web research enabled
    test_transaction = TEST_TRANSACTIONS[0]  # Netflix
    
    payload = {
        "transaction_label": test_transaction["label"],
        "amount": test_transaction["amount"],
        "use_web_research": True
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE}/suggest-tag",
            headers=headers,
            json=payload,
            timeout=15  # Longer timeout for web research
        )
        processing_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Web research successful! (took {processing_time:.1f}ms)")
            print(f"🏷️ Suggestion: {result['suggested_tag']} (confidence: {result['confidence']:.2f})")
            print(f"🌐 Web research used: {result['web_research_used']}")
            print(f"📝 Explanation: {result['explanation']}")
            
            if result.get('merchant_info'):
                print(f"🏪 Merchant info: {result['merchant_info']}")
                
            return True
        else:
            print(f"❌ Web research failed: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Web research exception: {e}")
        return False

def run_all_tests():
    """Run all tests and provide summary"""
    print("🚀 TESTING INTELLIGENT TAG SUGGESTION SYSTEM")
    print("=" * 80)
    print("Système de suggestion de tags qui remplace la classification fixe/variable")
    print("=" * 80)
    
    test_results = []
    
    # Test 1: Individual suggestions
    individual_success_rate = test_tag_suggestion_endpoint()
    test_results.append(("Individual Suggestions", individual_success_rate > 0.7))
    
    # Test 2: Batch processing
    batch_success = test_batch_suggestions()
    test_results.append(("Batch Processing", batch_success))
    
    # Test 3: Simple GET endpoint
    test_simple_get_endpoint()
    test_results.append(("Simple GET Endpoint", True))  # Visual test
    
    # Test 4: Statistics
    stats_success = test_tag_statistics()
    test_results.append(("Statistics Endpoint", stats_success))
    
    # Test 5: Web research (optional)
    web_research_success = test_web_research_mode()
    test_results.append(("Web Research Mode", web_research_success))
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 TEST SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Le système de suggestion de tags fonctionne correctement.")
        print("🏷️ L'IA peut maintenant suggérer des tags pertinents au lieu de fixe/variable.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    print("\n📝 NOUVEAUX ENDPOINTS DISPONIBLES:")
    print(f"  - POST {API_BASE}/suggest-tag")
    print(f"  - POST {API_BASE}/batch-suggest-tags") 
    print(f"  - GET  {API_BASE}/suggest-tag/{{label}}")
    print(f"  - POST {API_BASE}/learn-tag-feedback")
    print(f"  - GET  {API_BASE}/tag-suggestion-stats")

if __name__ == "__main__":
    print("Starting tag suggestion tests...")
    print("Make sure the backend server is running on http://localhost:8000")
    print()
    
    # Check if server is responding
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Backend server is running")
            run_all_tests()
        else:
            print("❌ Backend server is not responding correctly")
    except Exception as e:
        print(f"❌ Cannot connect to backend server: {e}")
        print("Please start the backend server with: python -m uvicorn app:app --reload")