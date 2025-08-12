#!/usr/bin/env python3
"""
Diagnostic script for Settings page CORS and validation issues
"""
import requests
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
FRONTEND_ORIGIN = "http://localhost:3000"

def test_cors_headers(url, method="GET", data=None, headers=None):
    """Test CORS headers on an endpoint"""
    if headers is None:
        headers = {}
    
    # Add CORS preflight headers
    headers.update({
        'Origin': FRONTEND_ORIGIN,
        'Access-Control-Request-Method': method,
        'Access-Control-Request-Headers': 'Content-Type,Authorization'
    })
    
    try:
        if method == "OPTIONS":
            response = requests.options(url, headers=headers)
        elif method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers)
        else:
            response = requests.request(method, url, json=data, headers=headers)
        
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
            'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials')
        }
        
        return {
            'status_code': response.status_code,
            'cors_headers': cors_headers,
            'response_text': response.text[:200] if response.text else None
        }
    except Exception as e:
        return {'error': str(e)}

def get_auth_token():
    """Get authentication token"""
    token_data = {
        'username': 'admin',
        'password': 'secret'
    }
    
    response = requests.post(f"{BASE_URL}/token", data=token_data)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        logger.error(f"Failed to get token: {response.status_code} {response.text}")
        return None

def test_custom_provisions_endpoint():
    """Test /custom-provisions endpoint with different payloads"""
    token = get_auth_token()
    if not token:
        return {"error": "No auth token available"}
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Origin': FRONTEND_ORIGIN
    }
    
    # Test different payload variations
    test_payloads = [
        # Minimal payload
        {
            "name": "Test Provision 1",
            "description": "Test description",
            "base_calculation": "total",
            "percentage": 10.0
        },
        # Full payload matching frontend
        {
            "name": "Test Provision 2", 
            "description": "Test description 2",
            "percentage": 15.0,
            "base_calculation": "total",
            "fixed_amount": None,
            "split_mode": "key",
            "split_member1": 50.0,
            "split_member2": 50.0,
            "icon": "💰",
            "color": "#3B82F6",
            "display_order": 0,
            "is_active": True,
            "is_temporary": False,
            "start_date": None,
            "end_date": None,
            "target_amount": 1000.0,
            "category": "épargne"
        },
        # Payload with potentially problematic fields
        {
            "name": "Test Provision 3",
            "description": "",
            "percentage": 0,
            "base_calculation": "fixed",
            "fixed_amount": 200.0,
            "split_mode": "custom",
            "split_member1": 60.0,
            "split_member2": 40.0
        }
    ]
    
    results = []
    for i, payload in enumerate(test_payloads, 1):
        logger.info(f"Testing payload {i}: {payload['name']}")
        
        # Test OPTIONS (CORS preflight)
        options_result = test_cors_headers(f"{BASE_URL}/custom-provisions", "OPTIONS", headers=headers)
        
        # Test POST
        try:
            response = requests.post(f"{BASE_URL}/custom-provisions", json=payload, headers=headers)
            results.append({
                'payload_index': i,
                'payload': payload,
                'options_cors': options_result,
                'post_status': response.status_code,
                'post_response': response.text[:300],
                'post_headers': dict(response.headers)
            })
        except Exception as e:
            results.append({
                'payload_index': i,
                'payload': payload,
                'options_cors': options_result,
                'error': str(e)
            })
    
    return results

def test_fixed_lines_endpoint():
    """Test /fixed-lines/{id} endpoint CORS"""
    token = get_auth_token()
    if not token:
        return {"error": "No auth token available"}
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Origin': FRONTEND_ORIGIN
    }
    
    # First get list of fixed lines to find an ID
    try:
        response = requests.get(f"{BASE_URL}/fixed-lines", headers=headers)
        if response.status_code == 200:
            fixed_lines = response.json()
            if fixed_lines:
                test_id = fixed_lines[0]['id']
                logger.info(f"Testing with fixed line ID: {test_id}")
                
                # Test different methods on the specific ID endpoint
                test_results = {}
                
                # Test OPTIONS (CORS preflight)
                test_results['options'] = test_cors_headers(
                    f"{BASE_URL}/fixed-lines/{test_id}", 
                    "OPTIONS", 
                    headers=headers
                )
                
                # Test GET
                test_results['get'] = test_cors_headers(
                    f"{BASE_URL}/fixed-lines/{test_id}", 
                    "GET", 
                    headers=headers
                )
                
                # Test PUT with sample data
                put_data = {
                    "label": "Updated Fixed Line",
                    "amount": 150.0,
                    "freq": "mensuelle", 
                    "split_mode": "clé",
                    "split1": 50.0,
                    "split2": 50.0,
                    "category": "autres",
                    "active": True
                }
                
                test_results['put'] = test_cors_headers(
                    f"{BASE_URL}/fixed-lines/{test_id}",
                    "PUT",
                    data=put_data,
                    headers=headers
                )
                
                return test_results
            else:
                return {"error": "No fixed lines found to test with"}
        else:
            return {"error": f"Failed to get fixed lines: {response.status_code}"}
    
    except Exception as e:
        return {"error": str(e)}

def main():
    """Run comprehensive diagnostics"""
    logger.info("🔍 Starting Settings page CORS and validation diagnostics")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'base_url': BASE_URL,
        'frontend_origin': FRONTEND_ORIGIN,
        'tests': {}
    }
    
    # Test 1: Health check
    logger.info("1. Testing health endpoint")
    results['tests']['health'] = test_cors_headers(f"{BASE_URL}/health")
    
    # Test 2: Custom provisions endpoint
    logger.info("2. Testing /custom-provisions endpoint")
    results['tests']['custom_provisions'] = test_custom_provisions_endpoint()
    
    # Test 3: Fixed lines endpoint
    logger.info("3. Testing /fixed-lines/{id} endpoint")  
    results['tests']['fixed_lines'] = test_fixed_lines_endpoint()
    
    # Test 4: Basic CORS check on main routes
    logger.info("4. Testing basic CORS on key endpoints")
    basic_endpoints = [
        "/",
        "/docs",
        "/config", 
        "/summary?month=2024-08"
    ]
    
    basic_tests = {}
    for endpoint in basic_endpoints:
        basic_tests[endpoint] = test_cors_headers(f"{BASE_URL}{endpoint}")
    
    results['tests']['basic_cors'] = basic_tests
    
    # Save results
    report_file = f"settings_diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"📊 Diagnostic complete. Report saved to: {report_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("🚨 CRITICAL ISSUES FOUND:")
    print("="*60)
    
    # Check for missing CORS headers
    for test_name, test_result in results['tests'].items():
        if isinstance(test_result, dict) and 'cors_headers' in test_result:
            cors = test_result['cors_headers']
            if not cors.get('Access-Control-Allow-Origin'):
                print(f"❌ {test_name}: Missing Access-Control-Allow-Origin header")
        elif isinstance(test_result, list):  # custom_provisions test
            for item in test_result:
                if 'post_status' in item and item['post_status'] >= 400:
                    print(f"❌ custom-provisions: HTTP {item['post_status']} error")
                    print(f"   Response: {item['post_response'][:100]}...")
    
    return results

if __name__ == "__main__":
    main()