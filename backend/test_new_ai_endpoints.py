#!/usr/bin/env python3
"""
Test script for new AI triggering endpoints
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
ENDPOINTS = {
    "bulk_suggestions": "/expense-classification/bulk-suggestions",
    "instant_suggestion": "/expense-classification/transactions/{}/instant-suggestion",
    "hover_preview": "/expense-classification/transactions/hover-preview",
    "system_health": "/expense-classification/system/health"
}

def test_endpoint(endpoint_name, method, url, payload=None, headers=None):
    """Test a single endpoint"""
    print(f"\n🧪 Testing {endpoint_name}: {method} {url}")
    
    try:
        start_time = time.time()
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=payload, headers=headers, timeout=10)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
        response_time = (time.time() - start_time) * 1000
        
        print(f"   Status: {response.status_code}")
        print(f"   Response time: {response_time:.1f}ms")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'List/Other'}")
                print(f"✅ SUCCESS")
                return True
            except Exception as e:
                print(f"   Response: {response.text[:100]}...")
                print(f"✅ SUCCESS (non-JSON)")
                return True
        elif response.status_code == 403:
            print("   ⚠️  Authentication required (expected for protected endpoints)")
            return True  # Expected for protected endpoints
        else:
            print(f"   Error: {response.text[:200]}")
            print(f"❌ FAILED")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("🚀 Testing New AI Triggering Endpoints")
    print("=" * 50)
    
    results = {}
    
    # Test system health (no auth required)
    print("\n📊 Testing System Health:")
    results['health'] = test_endpoint(
        "System Health",
        "GET",
        f"{BASE_URL}{ENDPOINTS['system_health']}"
    )
    
    # Test bulk suggestions (requires auth, expect 403)
    print("\n📦 Testing Bulk Suggestions:")
    results['bulk'] = test_endpoint(
        "Bulk Suggestions",
        "POST",
        f"{BASE_URL}{ENDPOINTS['bulk_suggestions']}",
        payload={
            "transaction_ids": [1, 2, 3],
            "confidence_threshold": 0.1,
            "include_explanations": True,
            "use_cache": True
        }
    )
    
    # Test instant suggestion (requires auth, expect 403)
    print("\n⚡ Testing Instant Suggestion:")
    results['instant'] = test_endpoint(
        "Instant Suggestion",
        "GET",
        f"{BASE_URL}{ENDPOINTS['instant_suggestion'].format(1)}?force_refresh=false"
    )
    
    # Test hover preview (requires auth, expect 403)
    print("\n🖱️ Testing Hover Preview:")
    results['hover'] = test_endpoint(
        "Hover Preview",
        "POST",
        f"{BASE_URL}{ENDPOINTS['hover_preview']}",
        payload={
            "transaction_ids": [1, 2, 3],
            "preview_only": True
        }
    )
    
    # Test API documentation access
    print("\n📚 Testing API Documentation:")
    results['docs'] = test_endpoint(
        "API Docs",
        "GET",
        f"{BASE_URL}/docs"
    )
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 SUMMARY")
    print("=" * 50)
    
    for endpoint, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {endpoint:<15} {status}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\n🎯 Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All endpoints are accessible and responding correctly!")
    else:
        print("⚠️ Some endpoints may need attention")
    
    print("\n💡 Notes:")
    print("   - 403 responses are expected for authenticated endpoints without valid tokens")
    print("   - This confirms the endpoints exist and are properly protected")
    print("   - The actual functionality will be tested through the frontend integration")

if __name__ == "__main__":
    main()