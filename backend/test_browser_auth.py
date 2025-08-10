#!/usr/bin/env python3
"""
Test script to simulate browser-based authentication issues
"""

import requests
import json
import tempfile
import os
from dotenv import load_dotenv
load_dotenv()

BASE_URL = "http://127.0.0.1:8000"

def test_browser_like_auth():
    print("=== Browser-like Authentication Test ===")
    
    # 1. Get JWT token
    print("\n1. Getting JWT token...")
    login_data = {
        "username": "admin", 
        "password": "secret"
    }
    
    response = requests.post(f"{BASE_URL}/token", data=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return
    
    token_data = response.json()
    token = token_data["access_token"]
    print(f"✅ Token obtained: {token[:50]}...")
    
    # 2. Test with various header formats (common browser issues)
    test_scenarios = [
        {
            "name": "Standard Bearer Token",
            "headers": {
                "Authorization": f"Bearer {token}",
                "Content-Type": "multipart/form-data"  # This might cause issues
            }
        },
        {
            "name": "Standard Bearer Token (no content-type)",
            "headers": {
                "Authorization": f"Bearer {token}"
            }
        },
        {
            "name": "Malformed Bearer Token", 
            "headers": {
                "Authorization": f"bearer {token}",  # lowercase 'bearer'
            }
        },
        {
            "name": "Missing Bearer prefix",
            "headers": {
                "Authorization": token,  # missing Bearer prefix
            }
        },
        {
            "name": "Expired/Invalid Token",
            "headers": {
                "Authorization": f"Bearer invalid_token_12345",
            }
        },
        {
            "name": "CORS Preflight Simulation",
            "method": "OPTIONS",
            "headers": {
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
                "Origin": "http://localhost:3000"
            }
        }
    ]
    
    # Create test CSV
    csv_content = """dateOp,dateVal,label,category,categoryParent,amount,accountLabel
2024-01-15,2024-01-15,Test Transaction,Test Category,Test Parent,-50.00,Test Account"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        temp_csv_path = f.name
    
    try:
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n{i}. Testing: {scenario['name']}")
            
            method = scenario.get('method', 'POST')
            headers = scenario['headers']
            
            if method == 'OPTIONS':
                # CORS preflight request
                response = requests.options(f"{BASE_URL}/import", headers=headers)
                print(f"   {method} /import: {response.status_code}")
                print(f"   CORS Headers: {dict(response.headers)}")
            else:
                # Normal POST request
                with open(temp_csv_path, 'rb') as f:
                    files = {'file': ('test.csv', f, 'text/csv')}
                    
                    # Remove Content-Type from headers if present (let requests handle it)
                    clean_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
                    
                    response = requests.post(f"{BASE_URL}/import", headers=clean_headers, files=files)
                
                print(f"   {method} /import: {response.status_code}")
                if response.status_code != 200:
                    try:
                        error_data = response.json()
                        print(f"   Error: {error_data.get('detail', 'Unknown error')}")
                    except:
                        print(f"   Error: {response.text[:200]}")
                else:
                    print(f"   ✅ SUCCESS")
    
    finally:
        os.unlink(temp_csv_path)
    
    # 3. Test token validation directly
    print(f"\n=== Direct Token Validation Test ===")
    
    try:
        from auth import get_current_user, security
        from fastapi.security import HTTPAuthorizationCredentials
        import asyncio
        
        async def test_token_validation():
            try:
                credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
                user = await get_current_user(credentials)
                print(f"✅ Token validation successful: {user.username}")
                return True
            except Exception as e:
                print(f"❌ Token validation failed: {e}")
                return False
                
        result = asyncio.run(test_token_validation())
        
    except Exception as e:
        print(f"❌ Could not test token validation directly: {e}")
    
    print("\n=== End Browser-like Authentication Test ===")

if __name__ == "__main__":
    test_browser_like_auth()