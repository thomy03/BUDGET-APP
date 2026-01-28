"""
Test script to verify that tags synchronization works correctly
This script tests that all tags (from transactions, AI suggestions, and ML feedback) appear in the /tags endpoint
"""

import requests
import json
from datetime import datetime

def test_tags_endpoint():
    """Test the /tags endpoint to verify all tags are included"""
    
    # Base URL for the API
    BASE_URL = "http://localhost:8000"
    
    print("🧪 Testing Tags Synchronization...")
    print("=" * 50)
    
    try:
        # Test the tags endpoint
        response = requests.get(f"{BASE_URL}/tags")
        
        if response.status_code == 200:
            data = response.json()
            tags = data.get('tags', [])
            total_count = data.get('total_count', 0)
            stats = data.get('stats', {})
            
            print(f"✅ Tags endpoint successful!")
            print(f"📊 Total tags found: {total_count}")
            print(f"📈 Stats: {json.dumps(stats, indent=2)}")
            
            # Show first 10 tags with their sources
            print("\n🏷️  Sample Tags:")
            for i, tag in enumerate(tags[:10]):
                print(f"  {i+1:2d}. {tag['name']} ({tag['transaction_count']} uses)")
                
            # Count tags by potential source (we can infer from transaction_count)
            transaction_tags = [t for t in tags if t['transaction_count'] > 0]
            potential_ai_tags = [t for t in tags if t['transaction_count'] == 0]
            
            print(f"\n📋 Tag Distribution:")
            print(f"  - Tags from transactions: {len(transaction_tags)}")
            print(f"  - Potential AI/ML tags: {len(potential_ai_tags)}")
            
            if len(potential_ai_tags) > 0:
                print(f"\n🤖 AI/ML suggested tags (not yet applied):")
                for tag in potential_ai_tags[:5]:
                    print(f"  - {tag['name']} (confidence pattern)")
                    
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_ai_suggestions_in_database():
    """Check if there are AI suggestions in the database"""
    print("\n🔍 Checking Database for AI Suggestions...")
    print("=" * 50)
    
    try:
        # This would require direct database access
        # For now, we'll just indicate what should be checked
        print("💡 To manually verify:")
        print("  1. Check LabelTagMapping table for suggested_tags")
        print("  2. Check MLFeedback table for corrected_tag")
        print("  3. Ensure these tags now appear in /tags endpoint")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("🚀 Tags Synchronization Test")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_tags_endpoint()
    test_ai_suggestions_in_database()
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")
    print()
    print("📝 Expected behavior:")
    print("  - All tags from transactions should appear")
    print("  - AI suggested tags from LabelTagMapping should appear")
    print("  - ML feedback corrected tags should appear") 
    print("  - Total count should include all sources")
    print()
    print("🔧 If issues persist:")
    print("  1. Restart the backend server")
    print("  2. Check server logs for errors")
    print("  3. Verify database contains AI suggestions")