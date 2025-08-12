#!/usr/bin/env python3
"""
CORS Validation Script - Docker Frontend to Backend
Tests critical endpoints from frontend Docker origin (localhost:45678)
"""
import requests
import json
import sys
from typing import Dict, List, Tuple

def test_endpoint(endpoint: str, method: str = "GET", headers: Dict = None, data: Dict = None) -> Tuple[bool, str, Dict]:
    """Test single endpoint with CORS headers"""
    base_headers = {
        "Origin": "http://localhost:45678",
        "Content-Type": "application/json"
    }
    
    if headers:
        base_headers.update(headers)
    
    try:
        url = f"http://localhost:8000{endpoint}"
        
        if method == "OPTIONS":
            # Preflight request
            base_headers.update({
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type"
            })
            response = requests.options(url, headers=base_headers, timeout=5)
        elif method == "GET":
            response = requests.get(url, headers=base_headers, timeout=5)
        elif method == "POST":
            response = requests.post(url, headers=base_headers, json=data, timeout=5)
        else:
            return False, f"Method {method} not supported", {}
        
        # Check CORS headers
        cors_headers = {}
        for header in ["access-control-allow-origin", "access-control-allow-credentials", 
                      "access-control-allow-methods", "access-control-allow-headers"]:
            cors_headers[header] = response.headers.get(header, "MISSING")
        
        success = (
            response.status_code < 500 and  # Not server error
            cors_headers["access-control-allow-origin"] == "http://localhost:45678"
        )
        
        return success, f"Status: {response.status_code}", cors_headers
        
    except requests.exceptions.RequestException as e:
        return False, f"Connection error: {str(e)}", {}

def main():
    """Run CORS validation tests"""
    print("🔍 CORS Docker Frontend Validation")
    print("="*50)
    print(f"Testing communication: http://localhost:45678 → http://localhost:8000")
    print()
    
    # Test endpoints
    tests = [
        ("/health", "GET", None, None),
        ("/health", "OPTIONS", None, None),
        ("/fixed-lines", "OPTIONS", None, None),
        ("/custom-provisions", "OPTIONS", None, None),
        ("/config", "OPTIONS", None, None),
    ]
    
    # Try to get token for authenticated endpoints
    token = None
    try:
        with open("token.txt", "r") as f:
            token = f.read().strip()
            print(f"✅ Token loaded: {token[:20]}...")
    except FileNotFoundError:
        print("⚠️  No token file found, skipping authenticated tests")
    
    if token:
        auth_headers = {"Authorization": f"Bearer {token}"}
        tests.extend([
            ("/fixed-lines", "GET", auth_headers, None),
            ("/custom-provisions", "GET", auth_headers, None),
            ("/config", "GET", auth_headers, None),
            ("/summary?month=2025-08", "GET", auth_headers, None),
        ])
    
    print()
    results = []
    for endpoint, method, extra_headers, data in tests:
        print(f"Testing {method} {endpoint}...")
        success, message, cors_headers = test_endpoint(endpoint, method, extra_headers, data)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {message}")
        
        if cors_headers.get("access-control-allow-origin") == "http://localhost:45678":
            print(f"  🔒 CORS Origin: ✅ {cors_headers['access-control-allow-origin']}")
        else:
            print(f"  🔒 CORS Origin: ❌ {cors_headers.get('access-control-allow-origin', 'MISSING')}")
        
        results.append((endpoint, method, success, message))
        print()
    
    # Summary
    total_tests = len(results)
    passed_tests = sum(1 for _, _, success, _ in results if success)
    
    print("="*50)
    print("📊 SUMMARY")
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print()
        print("🎉 ALL TESTS PASSED!")
        print("Frontend Docker → Backend communication is working correctly")
        print("CORS is properly configured for http://localhost:45678")
        return 0
    else:
        print()
        print("🚨 SOME TESTS FAILED!")
        print("Check the failed endpoints above")
        return 1

if __name__ == "__main__":
    sys.exit(main())