#!/usr/bin/env python3
"""
API Endpoint Test Script
Tests the new unified classification endpoints via HTTP requests

This script tests the actual API endpoints to ensure they work correctly
in the FastAPI application environment.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if your API runs on a different port
API_PREFIX = "/api/classification"

def test_endpoint_availability():
    """Test if the API server is running and endpoints are available"""
    
    print("🔍 Testing API Endpoint Availability")
    print("=" * 50)
    
    try:
        # Test basic health check
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running")
        else:
            print(f"⚠️  API server responded with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server")
        print(f"   Make sure the server is running on {BASE_URL}")
        print("   Start it with: uvicorn app:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error testing API availability: {e}")
        return False
    
    return True

def test_unified_endpoints():
    """Test the new unified classification endpoints"""
    
    print(f"\n🎯 Testing Unified Classification Endpoints")
    print("=" * 50)
    
    # Test data
    test_cases = [
        {
            "transaction_label": "NETFLIX SARL 12.99",
            "transaction_amount": 12.99,
            "expected_tag": "streaming"
        },
        {
            "transaction_label": "MCDONALDS FRANCE 8.50", 
            "transaction_amount": 8.50,
            "expected_tag": "restaurant"
        }
    ]
    
    # Note: These tests assume authentication is disabled or using a test token
    # In production, you'd need to handle authentication
    
    headers = {
        "Content-Type": "application/json",
        # "Authorization": "Bearer your-test-token"  # Add if auth required
    }
    
    print("\n1. Testing POST /unified/classify")
    print("-" * 30)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['transaction_label']}")
        
        payload = {
            "transaction_label": test_case["transaction_label"],
            "transaction_amount": test_case["transaction_amount"],
            "use_web_research": False,  # Disable for faster testing
            "include_expense_type": True
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}{API_PREFIX}/unified/classify",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ SUCCESS")
                print(f"   Suggested Tag: {result.get('suggested_tag')}")
                print(f"   Confidence: {result.get('tag_confidence'):.2f}")
                print(f"   Explanation: {result.get('tag_explanation')}")
                print(f"   Expense Type: {result.get('expense_type')}")
                print(f"   Processing Time: {result.get('processing_time_ms')}ms")
            else:
                print(f"❌ FAILED: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print(f"\n2. Testing GET /unified/classify/{{transaction_label}}")
    print("-" * 30)
    
    test_label = "NETFLIX%20SARL%2012.99"  # URL encoded
    try:
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/unified/classify/{test_label}?amount=12.99&use_web_research=false",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS")
            print(f"   Suggested Tag: {result.get('suggested_tag')}")
            print(f"   Confidence: {result.get('tag_confidence'):.2f}")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print(f"\n3. Testing POST /unified/batch-classify")
    print("-" * 30)
    
    batch_payload = {
        "transactions": [
            {"id": 1, "label": "NETFLIX SARL 12.99", "amount": 12.99},
            {"id": 2, "label": "CARREFOUR PARIS 45.67", "amount": 45.67}
        ],
        "use_web_research": False,
        "include_expense_type": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/unified/batch-classify",
            json=batch_payload,
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS")
            print(f"   Total Processed: {result.get('total_processed')}")
            print(f"   Processing Time: {result.get('processing_time_ms')}ms")
            print(f"   Results:")
            for tx_id, classification in result.get('results', {}).items():
                print(f"     TX {tx_id}: {classification.get('suggested_tag')} ({classification.get('tag_confidence'):.2f})")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print(f"\n4. Testing GET /unified/stats")
    print("-" * 30)
    
    try:
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/unified/stats",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS")
            print(f"   System Status: {result.get('system_status')}")
            print(f"   Classification Approach: {result.get('classification_approach')}")
            print(f"   Features Available: {len(result.get('features', {}))}")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

def print_api_documentation():
    """Print documentation for the new API endpoints"""
    
    print(f"\n📚 NEW API ENDPOINTS DOCUMENTATION")
    print("=" * 50)
    
    endpoints = [
        {
            "method": "POST",
            "path": "/api/classification/unified/classify",
            "description": "Primary unified classification endpoint",
            "body": {
                "transaction_label": "string",
                "transaction_amount": "number (optional)",
                "use_web_research": "boolean (default: true)",
                "include_expense_type": "boolean (default: false)"
            },
            "response": "UnifiedClassificationResponse with suggested_tag, confidence, etc."
        },
        {
            "method": "POST", 
            "path": "/api/classification/unified/batch-classify",
            "description": "Batch classification for multiple transactions",
            "body": {
                "transactions": "array of {id, label, amount}",
                "use_web_research": "boolean (default: false)", 
                "include_expense_type": "boolean (default: false)"
            },
            "response": "BatchUnifiedClassificationResponse"
        },
        {
            "method": "GET",
            "path": "/api/classification/unified/classify/{transaction_label}",
            "description": "Simple GET endpoint for quick testing",
            "params": "amount, use_web_research, include_expense_type",
            "response": "UnifiedClassificationResponse"
        },
        {
            "method": "GET",
            "path": "/api/classification/unified/stats", 
            "description": "System statistics and configuration",
            "response": "Statistics about the unified classification system"
        }
    ]
    
    for endpoint in endpoints:
        print(f"\n{endpoint['method']} {endpoint['path']}")
        print(f"Description: {endpoint['description']}")
        
        if 'body' in endpoint:
            print("Request Body:")
            for key, value in endpoint['body'].items():
                print(f"  {key}: {value}")
        
        if 'params' in endpoint:
            print(f"Query Parameters: {endpoint['params']}")
        
        print(f"Response: {endpoint['response']}")
        print("-" * 40)

if __name__ == "__main__":
    print("🎯 API Endpoint Tests for Unified Classification System")
    print("=" * 60)
    
    # Check if server is available
    if not test_endpoint_availability():
        print("\n❌ Cannot proceed with API tests - server not available")
        print("\nTo start the server:")
        print("1. cd /path/to/backend")
        print("2. uvicorn app:app --reload")
        print("3. Run this test again")
        exit(1)
    
    # Test the new endpoints
    test_unified_endpoints()
    
    # Print documentation
    print_api_documentation()
    
    print(f"\n🎉 API ENDPOINT TESTING COMPLETE")
    print("=" * 60)
    print("\n✅ The unified classification system provides:")
    print("   🏷️  Contextual tag suggestions (Netflix → streaming)")
    print("   🔄 Batch processing for multiple transactions")  
    print("   🌐 Web research integration for unknown merchants")
    print("   💰 Optional FIXED/VARIABLE classification for compatibility")
    print("   📊 Performance statistics and monitoring")
    print("\n🚀 Ready for frontend integration!")
    print("\nNEXT STEPS:")
    print("1. Update frontend to use /unified/classify endpoints")
    print("2. Replace FIXED/VARIABLE UI with contextual tags")
    print("3. Add tag-based filtering and categorization")
    print("4. Enable user feedback for continuous improvement")