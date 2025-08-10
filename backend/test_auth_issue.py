#!/usr/bin/env python3
"""
Test script to reproduce JWT authentication issue on /import endpoint
"""

import requests
import os
import tempfile
from dotenv import load_dotenv
load_dotenv()

BASE_URL = "http://127.0.0.1:8000"

def test_authentication_issue():
    print("=== JWT Authentication Issue Diagnosis ===")
    
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
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 2. Test working endpoints
    print("\n2. Testing working endpoints...")
    
    # Test /config
    response = requests.get(f"{BASE_URL}/config", headers=headers)
    print(f"GET /config: {response.status_code} - {'✅ SUCCESS' if response.status_code == 200 else '❌ FAILED'}")
    if response.status_code != 200:
        print(f"   Error: {response.text}")
    
    # Test /summary 
    response = requests.get(f"{BASE_URL}/summary?month=2024-01", headers=headers)
    print(f"GET /summary: {response.status_code} - {'✅ SUCCESS' if response.status_code == 200 else '❌ FAILED'}")
    if response.status_code != 200:
        print(f"   Error: {response.text}")
    
    # 3. Test /import endpoint (the failing one)
    print("\n3. Testing /import endpoint...")
    
    # Create a simple test CSV
    csv_content = """dateOp,dateVal,label,category,categoryParent,amount,accountLabel
2024-01-15,2024-01-15,Test Transaction,Test Category,Test Parent,-50.00,Test Account
2024-01-16,2024-01-16,Another Test,Test Category 2,Test Parent 2,-30.00,Test Account"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        temp_csv_path = f.name
    
    try:
        # Test POST /import with multipart/form-data
        import_headers = {
            "Authorization": f"Bearer {token}"
            # Note: NOT setting Content-Type for multipart data - requests will set it
        }
        
        with open(temp_csv_path, 'rb') as f:
            files = {'file': ('test.csv', f, 'text/csv')}
            response = requests.post(f"{BASE_URL}/import", headers=import_headers, files=files)
        
        print(f"POST /import: {response.status_code} - {'✅ SUCCESS' if response.status_code == 200 else '❌ FAILED'}")
        if response.status_code != 200:
            print(f"   Error: {response.text}")
            print(f"   Headers sent: {import_headers}")
            
            # Try to get more details
            try:
                error_data = response.json()
                print(f"   Error details: {error_data}")
            except:
                print(f"   Raw response: {response.text}")
    
    finally:
        os.unlink(temp_csv_path)
    
    print("\n=== End Diagnosis ===")

if __name__ == "__main__":
    test_authentication_issue()