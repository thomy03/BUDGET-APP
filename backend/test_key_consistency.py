#!/usr/bin/env python3
"""
Test script to check JWT key consistency issues
"""

import os
import sys
from dotenv import load_dotenv

# Test multiple loads to see if key changes
print("=== JWT Key Consistency Test ===")

for i in range(3):
    print(f"\n--- Test {i+1} ---")
    
    # Force reload environment
    if '.env' in os.environ:
        del os.environ['.env']
    load_dotenv(override=True)
    
    # Import auth module fresh
    if 'auth' in sys.modules:
        del sys.modules['auth']
    
    import auth
    print(f"JWT_SECRET_KEY from env: {os.getenv('JWT_SECRET_KEY')}")
    print(f"SECRET_KEY from auth: {auth.SECRET_KEY}")
    
    # Create token and test consistency
    from datetime import timedelta
    token = auth.create_access_token(
        data={"sub": "admin"}, 
        expires_delta=timedelta(minutes=30)
    )
    print(f"Token created: {token[:50]}...")
    
    # Test decoding with same key
    try:
        import jwt
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=["HS256"])
        print(f"✅ Token decode successful: {payload['sub']}")
    except Exception as e:
        print(f"❌ Token decode failed: {e}")

# Test if keys are consistent across imports
print(f"\n=== Cross-Import Consistency ===")
from auth import SECRET_KEY as key1
import importlib
importlib.reload(sys.modules['auth'])
from auth import SECRET_KEY as key2

print(f"Key 1: {key1}")
print(f"Key 2: {key2}")
print(f"Keys match: {key1 == key2}")

# Test .env file content
print(f"\n=== .env File Analysis ===")
env_path = "/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend/.env"
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        content = f.read()
    print(f".env content:\n{content}")
    
    # Check for multiple JWT_SECRET_KEY lines
    jwt_lines = [line for line in content.split('\n') if 'JWT_SECRET_KEY' in line]
    print(f"JWT_SECRET_KEY lines found: {len(jwt_lines)}")
    for line in jwt_lines:
        print(f"  {line}")
else:
    print(".env file not found")

print("\n=== End Key Consistency Test ===")