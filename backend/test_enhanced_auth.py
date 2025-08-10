#!/usr/bin/env python3
"""
Test script to verify enhanced JWT authentication system
"""

import requests
import json
import tempfile
import os
from dotenv import load_dotenv
load_dotenv()

BASE_URL = "http://127.0.0.1:8000"

def test_enhanced_authentication():
    print("=== Enhanced JWT Authentication Test ===")
    
    # 1. Test health endpoint for auth info
    print("\n1. Checking health endpoint for auth info...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        health_data = response.json()
        auth_info = health_data.get("auth", {})
        print(f"✅ Auth info: {auth_info}")
    else:
        print(f"❌ Health check failed: {response.status_code}")
    
    # 2. Get fresh token and test import
    print("\n2. Getting fresh JWT token...")
    login_response = requests.post(f"{BASE_URL}/token", 
                                  data={"username": "admin", "password": "secret"})
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    token_data = login_response.json()
    token = token_data["access_token"]
    print(f"✅ Token received: {token[:50]}...")
    
    # 3. Test JWT debug endpoint
    print("\n3. Testing JWT debug endpoint...")
    debug_response = requests.post(f"{BASE_URL}/debug/jwt", 
                                  json={"token": token})
    if debug_response.status_code == 200:
        debug_data = debug_response.json()
        debug_info = debug_data["debug_info"]
        print(f"✅ JWT Debug Info:")
        print(f"   Status: {debug_info['status']}")
        print(f"   Secret key length: {debug_info['secret_key_length']}")
        print(f"   Algorithm: {debug_info['algorithm']}")
        if debug_info.get('payload'):
            print(f"   Valid for user: {debug_info['payload'].get('sub')}")
    else:
        print(f"❌ JWT debug failed: {debug_response.status_code}")
    
    # 4. Test import endpoint with enhanced logging
    print("\n4. Testing enhanced /import endpoint...")
    
    csv_content = """dateOp,dateVal,label,category,categoryParent,amount,accountLabel
2024-01-15,2024-01-15,Test Transaction,Test Category,Test Parent,-50.00,Test Account
2024-01-16,2024-01-16,Another Test,Test Category 2,Test Parent 2,-30.00,Test Account"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        temp_csv_path = f.name
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        with open(temp_csv_path, 'rb') as f:
            files = {'file': ('test_enhanced.csv', f, 'text/csv')}
            response = requests.post(f"{BASE_URL}/import", headers=headers, files=files)
        
        print(f"   Import Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Import successful with enhanced authentication!")
            import_data = response.json()
            print(f"   Import ID: {import_data.get('importId')}")
            print(f"   Months detected: {len(import_data.get('months', []))}")
        else:
            print(f"❌ Import failed")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   Raw error: {response.text[:200]}")
    
    finally:
        os.unlink(temp_csv_path)
    
    # 5. Test various error scenarios
    print("\n5. Testing enhanced error scenarios...")
    
    error_scenarios = [
        {
            "name": "Invalid token",
            "token": "invalid.jwt.token"
        },
        {
            "name": "Expired token", 
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTYxNjE2MTYwMH0.7Q4z5zJiPm9h5v_EwjU4T7mZL0fB2wR3lfj2G8uI2Ys"
        }
    ]
    
    for scenario in error_scenarios:
        print(f"\n   Testing: {scenario['name']}")
        
        debug_response = requests.post(f"{BASE_URL}/debug/jwt", 
                                      json={"token": scenario['token']})
        if debug_response.status_code == 200:
            debug_data = debug_response.json()
            debug_info = debug_data["debug_info"]
            print(f"     Debug Status: {debug_info['status']}")
            print(f"     Error: {debug_info.get('error', 'None')}")
        
        # Test actual import with invalid token
        headers = {"Authorization": f"Bearer {scenario['token']}"}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_csv_path = f.name
        
        try:
            with open(temp_csv_path, 'rb') as f:
                files = {'file': ('test.csv', f, 'text/csv')}
                response = requests.post(f"{BASE_URL}/import", headers=headers, files=files)
            
            print(f"     Import Status: {response.status_code} (expected: 401)")
        finally:
            os.unlink(temp_csv_path)
    
    print("\n=== Enhanced Authentication Test Complete ===")
    print("\n🔧 DEBUGGING TIPS FOR USERS:")
    print("1. Check server logs for detailed JWT error messages")
    print("2. Use GET /health to verify JWT configuration")  
    print("3. Use POST /debug/jwt to analyze specific tokens")
    print("4. Ensure server hasn't restarted between login and import")
    print("5. Verify JWT_SECRET_KEY hasn't changed in .env file")

if __name__ == "__main__":
    test_enhanced_authentication()