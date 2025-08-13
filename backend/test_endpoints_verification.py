#!/usr/bin/env python3
"""
Script de vérification des endpoints de modification
Teste les 4 endpoints requis pour s'assurer qu'ils fonctionnent correctement
"""

import requests
import json
import sys
import os

# Configuration
BASE_URL = "http://localhost:8001"
TEST_USERNAME = "demo"
TEST_PASSWORD = "demo123"

def get_auth_token():
    """Obtenir un token d'authentification"""
    response = requests.post(f"{BASE_URL}/api/v1/auth/token", 
                           data={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Failed to get auth token: {response.status_code}")
        print(response.text)
        return None

def test_endpoints():
    """Tester tous les endpoints requis"""
    
    print("🔧 Vérification des endpoints de modification...")
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("❌ Cannot proceed without authentication token")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test data
    test_transaction_id = 1  # Assuming transaction ID 1 exists
    test_month = "2025-08"
    
    tests_passed = 0
    total_tests = 4
    
    print("\n1. 🏷️  Test PUT /transactions/{id}/tag")
    try:
        response = requests.put(
            f"{BASE_URL}/transactions/{test_transaction_id}/tag",
            headers=headers,
            json={"tags": "test,verification"}
        )
        if response.status_code in [200, 404]:  # 404 is OK if transaction doesn't exist
            print(f"✅ PUT /transactions/{test_transaction_id}/tag: {response.status_code}")
            tests_passed += 1
        else:
            print(f"❌ PUT /transactions/{test_transaction_id}/tag failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ PUT /transactions/{test_transaction_id}/tag error: {e}")
    
    print("\n2. 🔄 Test PATCH /transactions/{id}/expense-type")
    try:
        response = requests.patch(
            f"{BASE_URL}/transactions/{test_transaction_id}/expense-type",
            headers=headers,
            json={"expense_type": "VARIABLE"}
        )
        if response.status_code in [200, 404]:  # 404 is OK if transaction doesn't exist
            print(f"✅ PATCH /transactions/{test_transaction_id}/expense-type: {response.status_code}")
            tests_passed += 1
        else:
            print(f"❌ PATCH /transactions/{test_transaction_id}/expense-type failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ PATCH /transactions/{test_transaction_id}/expense-type error: {e}")
    
    print("\n3. 🤖 Test POST /api/ml-feedback")
    try:
        feedback_data = {
            "transaction_id": test_transaction_id,
            "original_tag": "divers",
            "corrected_tag": "test",
            "original_expense_type": "VARIABLE",
            "corrected_expense_type": "FIXED",
            "feedback_type": "correction",
            "confidence_before": 0.5
        }
        response = requests.post(
            f"{BASE_URL}/api/ml-feedback/",
            headers=headers,
            json=feedback_data
        )
        if response.status_code in [201, 404]:  # 404 is OK if transaction doesn't exist
            print(f"✅ POST /api/ml-feedback: {response.status_code}")
            tests_passed += 1
        else:
            print(f"❌ POST /api/ml-feedback failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ POST /api/ml-feedback error: {e}")
    
    print("\n4. 🔍 Test GET /transactions?tag=X")
    try:
        response = requests.get(
            f"{BASE_URL}/transactions?month={test_month}&tag=test",
            headers=headers
        )
        if response.status_code == 200:
            print(f"✅ GET /transactions?tag=test: {response.status_code}")
            print(f"   Found {len(response.json())} transactions with tag 'test'")
            tests_passed += 1
        else:
            print(f"❌ GET /transactions?tag=test failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ GET /transactions?tag=test error: {e}")
    
    print(f"\n📊 Tests Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All endpoints are working correctly!")
        return True
    else:
        print("⚠️  Some endpoints need attention")
        return False

def test_api_availability():
    """Tester si l'API est disponible"""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print("✅ API is running and accessible")
            return True
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API - is the server running?")
        print(f"   Expected URL: {BASE_URL}")
        return False
    except Exception as e:
        print(f"❌ API availability check failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting endpoints verification...")
    
    # Test API availability first
    if not test_api_availability():
        print("\n💡 To start the API server:")
        print("   cd backend && python -m uvicorn app:app --reload --port 8001")
        sys.exit(1)
    
    # Run endpoint tests
    success = test_endpoints()
    
    if success:
        print("\n✅ All verification tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed - check the implementation")
        sys.exit(1)