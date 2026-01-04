"""
Test script to verify tags display in transactions
This script will:
1. Check if transactions have tags
2. Add some test tags if none exist
3. Verify the /transactions endpoint returns tags correctly
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_transactions_with_tags():
    """Test if transactions endpoint returns tags correctly"""
    
    print("🧪 Testing Transactions Tags Display...")
    print("=" * 50)
    
    try:
        # Test the transactions endpoint for current month
        current_month = datetime.now().strftime('%Y-%m')
        response = requests.get(f"{BASE_URL}/transactions?month={current_month}")
        
        if response.status_code == 403:
            print("❌ Authentication required. Please test from the frontend with a logged-in user.")
            return
            
        if response.status_code == 200:
            transactions = response.json()
            print(f"✅ Found {len(transactions)} transactions for {current_month}")
            
            # Check which transactions have tags
            tagged_transactions = [tx for tx in transactions if tx.get('tags') and len(tx['tags']) > 0]
            print(f"📊 Transactions with tags: {len(tagged_transactions)} / {len(transactions)}")
            
            if tagged_transactions:
                print("\n🏷️  Transactions with tags:")
                for tx in tagged_transactions[:5]:  # Show first 5
                    print(f"  - ID: {tx['id']}, Label: {tx['label'][:50]}, Tags: {tx['tags']}")
            else:
                print("\n⚠️  No transactions have tags!")
                print("💡 This explains why you don't see tags in the frontend.")
                print("\n📝 To fix this:")
                print("  1. Go to your transactions page")
                print("  2. Click on a transaction to add tags")
                print("  3. Use the AI suggestions or add manual tags")
                print("  4. Save the tags")
                
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_add_sample_tag():
    """Test adding a tag to a transaction"""
    print("\n🔧 Testing Tag Addition...")
    print("=" * 30)
    
    try:
        # First get a transaction without tags
        current_month = datetime.now().strftime('%Y-%m')
        response = requests.get(f"{BASE_URL}/transactions?month={current_month}")
        
        if response.status_code == 200:
            transactions = response.json()
            untagged = [tx for tx in transactions if not tx.get('tags') or len(tx['tags']) == 0]
            
            if untagged:
                test_tx = untagged[0]
                print(f"📝 Adding test tag to transaction: {test_tx['label'][:50]}")
                
                # Add a test tag
                tag_response = requests.put(
                    f"{BASE_URL}/transactions/{test_tx['id']}/tag",
                    json={"tags": "test-tag, alimentation"}
                )
                
                if tag_response.status_code == 200:
                    print("✅ Test tag added successfully!")
                    print("🔄 Now check your frontend - you should see tags!")
                else:
                    print(f"❌ Failed to add tag: {tag_response.status_code}")
                    print(f"Response: {tag_response.text}")
            else:
                print("ℹ️  All transactions already have tags")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("🚀 Tags Display Test")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_transactions_with_tags()
    
    print("\n" + "=" * 50)
    print("📋 Summary:")
    print("  - If no tags are shown, transactions simply don't have tags yet")
    print("  - Use the frontend to add tags to transactions")  
    print("  - The AI classification system can automatically add tags")
    print("  - Tags will appear immediately after being saved")
    print()
    print("🎯 Next steps:")
    print("  1. Go to /transactions page")
    print("  2. Click on any transaction without tags")
    print("  3. Add some tags and save")
    print("  4. Tags should appear immediately")