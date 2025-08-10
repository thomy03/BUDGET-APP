#!/usr/bin/env python3
"""
Test script to reproduce the actual error scenario reported by user
"""

import requests
import json
import tempfile
import os
import time
from dotenv import load_dotenv
load_dotenv()

BASE_URL = "http://127.0.0.1:8000"

def test_real_world_scenario():
    print("=== Real World Scenario Test ===")
    
    # 1. Login and get token (simulating frontend login)
    print("\n1. Frontend-like login...")
    login_response = requests.post(f"{BASE_URL}/token", 
                                  data={"username": "admin", "password": "secret"},
                                  headers={"Content-Type": "application/x-www-form-urlencoded"})
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    token_data = login_response.json()
    token = token_data["access_token"]
    print(f"✅ Token received: {token[:50]}...")
    
    # 2. Test working endpoints first (as user mentioned they work)
    print(f"\n2. Testing working endpoints...")
    
    # Note: /config and /summary are actually NOT protected, so they work without auth
    config_response = requests.get(f"{BASE_URL}/config")
    print(f"GET /config (no auth): {config_response.status_code} - {'✅' if config_response.status_code == 200 else '❌'}")
    
    summary_response = requests.get(f"{BASE_URL}/summary?month=2024-01")
    print(f"GET /summary (no auth): {summary_response.status_code} - {'✅' if summary_response.status_code == 200 else '❌'}")
    
    # 3. Test import endpoint scenarios
    print(f"\n3. Testing /import endpoint scenarios...")
    
    # Create test CSV file
    csv_content = """dateOp,dateVal,label,category,categoryParent,amount,accountLabel
2024-01-15,2024-01-15,Test Transaction,Test Category,Test Parent,-50.00,Test Account
2024-01-16,2024-01-16,Another Test,Test Category 2,Test Parent 2,-30.00,Test Account"""
    
    scenarios = [
        {
            "name": "Correct Bearer Token",
            "headers": {"Authorization": f"Bearer {token}"},
            "expected": 200
        },
        {
            "name": "Browser-like with extra headers", 
            "headers": {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Origin": "http://localhost:3000",
                "Referer": "http://localhost:3000/"
            },
            "expected": 200
        },
        {
            "name": "Stale/old token (simulate server restart)",
            # Simulate scenario where token was created with different secret
            "headers": {"Authorization": f"Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTcxNjIxMjgwMH0.invalid_signature"},
            "expected": 401
        }
    ]
    
    for scenario in scenarios:
        print(f"\n   Testing: {scenario['name']}")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_csv_path = f.name
        
        try:
            with open(temp_csv_path, 'rb') as f:
                files = {'file': ('test.csv', f, 'text/csv')}
                response = requests.post(f"{BASE_URL}/import", 
                                       headers=scenario['headers'], 
                                       files=files)
            
            print(f"   Status: {response.status_code} (expected: {scenario['expected']})")
            
            if response.status_code != scenario['expected']:
                print(f"   ⚠️  UNEXPECTED!")
                
            if response.status_code == 401:
                try:
                    error_detail = response.json()
                    print(f"   Error detail: {error_detail}")
                except:
                    print(f"   Raw error: {response.text}")
            elif response.status_code == 200:
                print(f"   ✅ SUCCESS")
            else:
                print(f"   Error: {response.text[:200]}")
                
        finally:
            os.unlink(temp_csv_path)
    
    # 4. Check server logs and auth behavior
    print(f"\n4. Checking auth behavior details...")
    
    # Test direct auth validation
    from auth import get_current_user, security
    from fastapi.security import HTTPAuthorizationCredentials
    import asyncio
    
    async def validate_token_direct(token_to_test):
        try:
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_to_test)
            user = await get_current_user(credentials)
            return f"✅ Valid: {user.username}"
        except Exception as e:
            return f"❌ Invalid: {e}"
    
    print(f"   Direct validation of current token: {asyncio.run(validate_token_direct(token))}")
    
    print(f"\n=== Potential Root Causes ===")
    print(f"1. Server restart between token creation and validation")
    print(f"2. Multiple server instances with different JWT secrets")
    print(f"3. Environment variable changes at runtime")
    print(f"4. Frontend sending malformed Authorization header")
    print(f"5. Token created with different secret key")
    
    print(f"\n=== Recommended Debug Steps ===")
    print(f"1. Check server logs during failed import")
    print(f"2. Verify JWT_SECRET_KEY consistency") 
    print(f"3. Check if server restarts between login and import")
    print(f"4. Monitor Authorization header from frontend")
    print(f"5. Add more detailed JWT error logging")

if __name__ == "__main__":
    test_real_world_scenario()