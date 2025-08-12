#!/usr/bin/env python3
"""
Test script for the new tags endpoints
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"

def create_token():
    """Generate a token for testing (using existing system)"""
    from datetime import datetime, timedelta, timezone
    from auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": "admin"}, expires_delta=expire - datetime.now(timezone.utc))
    return token

def test_tags_endpoints():
    """Test all tags endpoints"""
    
    # Generate token
    token = create_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"🔑 Generated token: {token[:50]}...")
    
    # Test 1: GET /tags - List all tags
    print("\n📋 Testing GET /tags")
    response = requests.get(f"{BASE_URL}/tags", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data['total_count']} tags")
        if data['tags']:
            print(f"   First tag: {data['tags'][0]['name']} ({data['tags'][0]['transaction_count']} transactions)")
        print(f"   Stats: {data['stats']}")
    else:
        print(f"❌ Error: {response.text}")
    
    # Test 2: GET /tags/search
    print("\n🔍 Testing GET /tags/search")
    response = requests.get(f"{BASE_URL}/tags/search?query=courses", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Search results: {data['total_found']} tags found")
        for tag in data['results']:
            print(f"   - {tag['name']}: {tag['transaction_count']} transactions")
    else:
        print(f"❌ Error: {response.text}")
    
    # Test 3: GET /tags/{tag_id}/transactions (if we have tags)
    if response.status_code == 200 and 'data' in locals():
        first_response = requests.get(f"{BASE_URL}/tags", headers=headers)
        if first_response.status_code == 200:
            tags_data = first_response.json()
            if tags_data['tags']:
                tag_id = tags_data['tags'][0]['id']
                print(f"\n📊 Testing GET /tags/{tag_id}/transactions")
                response = requests.get(f"{BASE_URL}/tags/{tag_id}/transactions", headers=headers)
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Found {data['stats']['filtered_count']} transactions for tag '{data['tag_name']}'")
                    print(f"   Total amount: {data['stats']['total_amount']:.2f}")
                else:
                    print(f"❌ Error: {response.text}")
    
    # Test 4: PUT /tags/{tag_id} - Update tag (if we have tags)
    if 'tags_data' in locals() and tags_data['tags']:
        tag_id = tags_data['tags'][0]['id']
        print(f"\n✏️  Testing PUT /tags/{tag_id}")
        update_payload = {
            "patterns": ["TEST_PATTERN", "ANOTHER_PATTERN"]
        }
        response = requests.put(f"{BASE_URL}/tags/{tag_id}", 
                              json=update_payload, headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Updated tag: {data['updates']}")
        else:
            print(f"❌ Error: {response.text}")
    
    # Test 5: POST /tags/{tag_id}/patterns - Add patterns
    if 'tags_data' in locals() and tags_data['tags']:
        tag_id = tags_data['tags'][0]['id']
        print(f"\n➕ Testing POST /tags/{tag_id}/patterns")
        patterns_payload = {
            "patterns": ["PATTERN_1", "PATTERN_2"]
        }
        response = requests.post(f"{BASE_URL}/tags/{tag_id}/patterns", 
                               json=patterns_payload, headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Added patterns: {data['message']}")
        else:
            print(f"❌ Error: {response.text}")
    
    # Test 6: POST /tags/{tag_id}/toggle-type - Toggle expense type
    if 'tags_data' in locals() and tags_data['tags']:
        tag_id = tags_data['tags'][0]['id']
        print(f"\n🔄 Testing POST /tags/{tag_id}/toggle-type")
        response = requests.post(f"{BASE_URL}/tags/{tag_id}/toggle-type", 
                               json={}, headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Toggled expense type: {data['previous_type']} → {data['new_type']}")
        else:
            print(f"❌ Error: {response.text}")
    
    print("\n🎯 All tests completed!")

if __name__ == "__main__":
    test_tags_endpoints()