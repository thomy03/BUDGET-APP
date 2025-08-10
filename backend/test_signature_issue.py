#!/usr/bin/env python3
"""
Test script to diagnose JWT signature verification issues
"""

import requests
import tempfile
import os
import jwt
from auth import SECRET_KEY, create_access_token
from datetime import timedelta, datetime
from dotenv import load_dotenv
load_dotenv()

BASE_URL = "http://127.0.0.1:8000"

def test_signature_verification_issues():
    print("=== JWT Signature Verification Issues Diagnosis ===")
    
    # 1. Create a valid token
    print("\n1. Creating valid token...")
    valid_token = create_access_token(
        data={"sub": "admin"}, 
        expires_delta=timedelta(minutes=30)
    )
    print(f"Valid token: {valid_token[:50]}...")
    
    # 2. Create tokens with various signature issues
    print("\n2. Testing signature verification scenarios...")
    
    test_tokens = [
        {
            "name": "Valid Token",
            "token": valid_token,
            "expected": 200
        },
        {
            "name": "Token with wrong secret", 
            "token": jwt.encode({"sub": "admin", "exp": datetime.utcnow() + timedelta(minutes=30)}, 
                               "wrong_secret", algorithm="HS256"),
            "expected": 401
        },
        {
            "name": "Token with wrong algorithm",
            "token": jwt.encode({"sub": "admin", "exp": datetime.utcnow() + timedelta(minutes=30)}, 
                               SECRET_KEY, algorithm="HS512"),  # Wrong algorithm
            "expected": 401
        },
        {
            "name": "Expired token",
            "token": jwt.encode({"sub": "admin", "exp": datetime.utcnow() - timedelta(minutes=1)}, 
                               SECRET_KEY, algorithm="HS256"),
            "expected": 401
        },
        {
            "name": "Token without exp claim",
            "token": jwt.encode({"sub": "admin"}, SECRET_KEY, algorithm="HS256"),
            "expected": 401
        },
        {
            "name": "Token without sub claim", 
            "token": jwt.encode({"exp": datetime.utcnow() + timedelta(minutes=30)}, 
                               SECRET_KEY, algorithm="HS256"),
            "expected": 401
        },
        {
            "name": "Malformed token",
            "token": "invalid.jwt.token",
            "expected": 401
        },
        {
            "name": "Token with tampered signature",
            "token": valid_token[:-5] + "XXXXX",  # Change last 5 chars of signature
            "expected": 401
        }
    ]
    
    # Create test CSV
    csv_content = """dateOp,dateVal,label,category,categoryParent,amount,accountLabel
2024-01-15,2024-01-15,Test Transaction,Test Category,Test Parent,-50.00,Test Account"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        temp_csv_path = f.name
    
    try:
        for i, scenario in enumerate(test_tokens, 1):
            print(f"\n{i}. Testing: {scenario['name']}")
            
            headers = {
                "Authorization": f"Bearer {scenario['token']}"
            }
            
            with open(temp_csv_path, 'rb') as f:
                files = {'file': ('test.csv', f, 'text/csv')}
                response = requests.post(f"{BASE_URL}/import", headers=headers, files=files)
            
            print(f"   Status: {response.status_code} (expected: {scenario['expected']})")
            
            if response.status_code != scenario['expected']:
                print(f"   ⚠️  UNEXPECTED RESULT!")
            
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
    
    # 3. Test JWT decoding directly
    print(f"\n=== Direct JWT Signature Verification ===")
    
    for scenario in test_tokens[:3]:  # Test first 3 scenarios
        print(f"\nTesting: {scenario['name']}")
        try:
            payload = jwt.decode(scenario['token'], SECRET_KEY, algorithms=["HS256"])
            print(f"  ✅ JWT decode successful: {payload}")
        except jwt.ExpiredSignatureError:
            print(f"  ❌ JWT expired")
        except jwt.InvalidSignatureError:
            print(f"  ❌ JWT signature verification failed")
        except jwt.InvalidTokenError as e:
            print(f"  ❌ JWT invalid: {e}")
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
    
    print("\n=== End Signature Verification Diagnosis ===")

if __name__ == "__main__":
    test_signature_verification_issues()