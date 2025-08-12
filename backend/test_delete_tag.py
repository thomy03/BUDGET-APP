#!/usr/bin/env python3
"""
Test DELETE endpoint for tags (requires cascade parameter)
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def create_token():
    """Generate a token for testing"""
    from datetime import datetime, timedelta, timezone
    from auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": "admin"}, expires_delta=expire - datetime.now(timezone.utc))
    return token

def test_delete_endpoint():
    """Test the DELETE /tags/{tag_id} endpoint"""
    
    token = create_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # First get all tags to see what we have
    print("📋 Getting current tags...")
    response = requests.get(f"{BASE_URL}/tags", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data['total_count']} tags")
        for tag in data['tags'][:3]:  # Show first 3
            print(f"   - ID {tag['id']}: {tag['name']} ({tag['transaction_count']} transactions, {tag['expense_type']})")
    else:
        print(f"❌ Error getting tags: {response.text}")
        return
    
    # Test DELETE without cascade - should fail if tag is used
    if data['tags']:
        tag_id = data['tags'][0]['id']  # Pick first tag
        tag_name = data['tags'][0]['name']
        transaction_count = data['tags'][0]['transaction_count']
        
        print(f"\n🚫 Testing DELETE /tags/{tag_id} WITHOUT cascade (should fail if tag is used)")
        response = requests.delete(f"{BASE_URL}/tags/{tag_id}?cascade=false", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 409:
            print(f"✅ Expected 409 error: {response.json()['detail']}")
        elif response.status_code == 200:
            print(f"✅ Tag deleted successfully (was unused): {response.json()['message']}")
        else:
            print(f"❌ Unexpected response: {response.text}")
        
        # Test DELETE with cascade - should work
        print(f"\n🗑️  Testing DELETE /tags/{tag_id} WITH cascade=true")
        response = requests.delete(f"{BASE_URL}/tags/{tag_id}?cascade=true", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Tag '{tag_name}' deleted successfully!")
            print(f"   Stats: {result['stats']}")
        else:
            print(f"❌ Error: {response.text}")
        
        # Verify tag was deleted
        print(f"\n🔍 Verifying tag deletion...")
        response = requests.get(f"{BASE_URL}/tags", headers=headers)
        if response.status_code == 200:
            new_data = response.json()
            print(f"✅ Now have {new_data['total_count']} tags (was {data['total_count']})")
            if new_data['total_count'] < data['total_count']:
                print("   Tag was successfully deleted!")
            else:
                print("   Warning: Tag count did not decrease")
        else:
            print(f"❌ Error verifying deletion: {response.text}")

if __name__ == "__main__":
    test_delete_endpoint()