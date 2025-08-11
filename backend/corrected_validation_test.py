#!/usr/bin/env python3
"""
Corrected Validation Test for Budget Famille v2.3
==================================================

This is a focused validation to identify and fix the authentication and security issues.
"""

import requests
import json
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_authentication_and_security():
    """Test authentication system and endpoint protection"""
    base_url = "http://localhost:8000"
    session = requests.Session()
    
    print("\n" + "="*60)
    print("FOCUSED SECURITY VALIDATION - Budget Famille v2.3")
    print("="*60)
    
    # Test 1: Try to access protected endpoints without authentication
    print("\n1. Testing endpoint protection without authentication:")
    
    protected_endpoints = [
        ("/config", "GET"),
        ("/import", "POST"),
        ("/transactions", "GET"),
        ("/fixed-lines", "GET")
    ]
    
    unprotected_count = 0
    for endpoint, method in protected_endpoints:
        try:
            if method == "GET":
                response = session.get(f"{base_url}{endpoint}")
            else:
                response = session.post(f"{base_url}{endpoint}")
                
            if response.status_code == 200:
                print(f"   🚨 CRITICAL: {endpoint} accessible without auth (status: {response.status_code})")
                unprotected_count += 1
            elif response.status_code in [401, 403]:
                print(f"   ✅ {endpoint} properly protected (status: {response.status_code})")
            else:
                print(f"   ⚠️ {endpoint} returned {response.status_code} (expected 401/403)")
                
        except Exception as e:
            print(f"   ❌ Error testing {endpoint}: {e}")
    
    # Test 2: Try authentication with correct credentials  
    print("\n2. Testing authentication with correct credentials:")
    
    # From auth.py, the password for "admin" is "secret"
    auth_data = {
        "username": "admin",
        "password": "secret"
    }
    
    try:
        auth_response = session.post(
            f"{base_url}/token",
            data=auth_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if auth_response.status_code == 200:
            token_data = auth_response.json()
            if "access_token" in token_data:
                print(f"   ✅ Authentication successful")
                token = token_data["access_token"]
                
                # Test 3: Access protected endpoint with token
                print("\n3. Testing protected endpoint access with valid token:")
                
                auth_session = requests.Session()
                auth_session.headers.update({
                    "Authorization": f"Bearer {token}"
                })
                
                config_response = auth_session.get(f"{base_url}/config")
                if config_response.status_code == 200:
                    print("   ✅ Protected endpoint accessible with valid token")
                    config_data = config_response.json()
                    print(f"   📋 Config retrieved: {config_data.get('member1', 'N/A')} & {config_data.get('member2', 'N/A')}")
                else:
                    print(f"   ❌ Protected endpoint failed with token: {config_response.status_code}")
                    print(f"       Response: {config_response.text[:200]}")
                    
            else:
                print(f"   ❌ Authentication response missing access_token: {token_data}")
        else:
            print(f"   ❌ Authentication failed: {auth_response.status_code}")
            print(f"       Response: {auth_response.text}")
            
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
    
    # Test 4: Test with invalid credentials
    print("\n4. Testing authentication with invalid credentials:")
    
    invalid_auth_data = {
        "username": "admin",
        "password": "wrongpassword"
    }
    
    try:
        invalid_auth_response = session.post(
            f"{base_url}/token",
            data=invalid_auth_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if invalid_auth_response.status_code == 401:
            print("   ✅ Invalid credentials properly rejected")
        else:
            print(f"   ❌ Invalid credentials not properly rejected: {invalid_auth_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Invalid auth test error: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY:")
    print(f"   Unprotected endpoints: {unprotected_count}")
    
    if unprotected_count > 0:
        print("   🚨 CRITICAL SECURITY ISSUE: Protected endpoints accessible without authentication!")
        print("   🚨 This must be fixed before release!")
        return False
    else:
        print("   ✅ Security validation passed")
        return True

if __name__ == "__main__":
    success = test_authentication_and_security()
    if not success:
        sys.exit(1)
    else:
        print("   ✅ All security checks passed!")
        sys.exit(0)