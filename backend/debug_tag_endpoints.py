#!/usr/bin/env python3
"""
Debug script for tag endpoints that are returning 500/422 errors
This script will directly call the tag functions to identify the root cause
"""

import sys
import os
import traceback
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import necessary components
from sqlalchemy.orm import Session
from models.database import get_db, Transaction, LabelTagMapping, TagFixedLineMapping
from routers.tags import extract_tags_from_transactions, get_tags_stats, list_tags
from models.schemas import TagsListResponse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test basic database connectivity"""
    print("🔍 Testing database connection...")
    try:
        db = next(get_db())
        count = db.query(Transaction).count()
        print(f"✅ Database connection successful - Found {count} transactions")
        return db
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def test_extract_tags_function(db: Session):
    """Test the extract_tags_from_transactions function"""
    print("\n🔍 Testing extract_tags_from_transactions function...")
    try:
        tags_data = extract_tags_from_transactions(db)
        print(f"✅ Function succeeded - Found {len(tags_data)} unique tags")
        
        # Show sample data
        if tags_data:
            sample_tag = next(iter(tags_data.items()))
            print(f"📋 Sample tag: {sample_tag[0]} -> {sample_tag[1]['transaction_count']} transactions")
        
        return tags_data
    except Exception as e:
        print(f"❌ extract_tags_from_transactions failed: {e}")
        traceback.print_exc()
        return None

def test_get_tags_stats_function(db: Session):
    """Test the get_tags_stats function"""
    print("\n🔍 Testing get_tags_stats function...")
    try:
        # Create a mock user object
        class MockUser:
            username = "test_user"
            
        mock_user = MockUser()
        
        # Call the function directly
        from routers.tags import get_tags_stats
        import asyncio
        
        async def run_test():
            return await get_tags_stats(current_user=mock_user, db=db)
        
        stats = asyncio.run(run_test())
        print(f"✅ get_tags_stats succeeded")
        print(f"📊 Stats keys: {list(stats.keys())}")
        return stats
    except Exception as e:
        print(f"❌ get_tags_stats failed: {e}")
        traceback.print_exc()
        return None

def test_list_tags_function(db: Session):
    """Test the list_tags function"""
    print("\n🔍 Testing list_tags function...")
    try:
        # Create a mock user object
        class MockUser:
            username = "test_user"
            
        mock_user = MockUser()
        
        # Call the function directly
        from routers.tags import list_tags
        import asyncio
        
        async def run_test():
            return await list_tags(current_user=mock_user, db=db)
        
        result = asyncio.run(run_test())
        print(f"✅ list_tags succeeded")
        print(f"📊 Found {result.total_count} tags")
        return result
    except Exception as e:
        print(f"❌ list_tags failed: {e}")
        traceback.print_exc()
        return None

def test_transactions_tags_summary(db: Session):
    """Test the tags-summary endpoint logic"""
    print("\n🔍 Testing transactions/tags-summary logic...")
    try:
        from collections import defaultdict
        
        # Simulate the tags-summary endpoint
        month = "2024-08"  # Use a test month
        txs = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.tags.isnot(None),
            Transaction.tags != ""
        ).all()
        
        tag_stats = defaultdict(lambda: {"count": 0, "total_amount": 0})
        
        for tx in txs:
            if tx.tags:
                tags = [t.strip() for t in tx.tags.split(',') if t.strip()]
                for tag in tags:
                    tag_stats[tag]["count"] += 1
                    tag_stats[tag]["total_amount"] += abs(tx.amount or 0)
        
        result = {
            "month": month,
            "tags": dict(tag_stats),
            "total_tagged_transactions": len(txs)
        }
        
        print(f"✅ tags-summary logic succeeded")
        print(f"📊 Month: {month}, Tagged transactions: {len(txs)}, Unique tags: {len(tag_stats)}")
        return result
    except Exception as e:
        print(f"❌ tags-summary logic failed: {e}")
        traceback.print_exc()
        return None

def check_database_schema():
    """Check if all required tables and columns exist"""
    print("\n🔍 Checking database schema...")
    try:
        db = next(get_db())
        
        # Check transactions table
        transactions = db.query(Transaction).limit(1).first()
        if transactions:
            print(f"✅ Transactions table exists")
            print(f"📋 Sample transaction has tags: {bool(transactions.tags)}")
            
            # Check if tags column exists and has data
            tagged_count = db.query(Transaction).filter(
                Transaction.tags.isnot(None),
                Transaction.tags != ""
            ).count()
            print(f"📊 Found {tagged_count} transactions with tags")
        
        # Check label_tag_mappings table
        mapping_count = db.query(LabelTagMapping).count()
        print(f"✅ LabelTagMapping table exists with {mapping_count} entries")
        
        # Check tag_fixed_line_mappings table
        fixed_mapping_count = db.query(TagFixedLineMapping).count()
        print(f"✅ TagFixedLineMapping table exists with {fixed_mapping_count} entries")
        
        return True
    except Exception as e:
        print(f"❌ Schema check failed: {e}")
        traceback.print_exc()
        return False

def main():
    print("🚀 Debug Tag Endpoints")
    print("=" * 50)
    
    # Test database connection
    db = test_database_connection()
    if not db:
        return
    
    # Check database schema
    if not check_database_schema():
        return
    
    # Test individual functions
    tags_data = test_extract_tags_function(db)
    
    if tags_data is not None:
        # Test get_tags_stats function
        stats = test_get_tags_stats_function(db)
        
        # Test list_tags function
        tags_list = test_list_tags_function(db)
        
        # Test tags-summary logic
        summary = test_transactions_tags_summary(db)
        
        print("\n" + "=" * 50)
        print("📋 SUMMARY")
        print("=" * 50)
        
        results = {
            "Database Connection": db is not None,
            "Schema Check": True,
            "Extract Tags": tags_data is not None,
            "Get Tags Stats": stats is not None,
            "List Tags": tags_list is not None,
            "Tags Summary": summary is not None
        }
        
        for test, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {test:<20} {status}")
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        
        print(f"\n🎯 Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tag functions are working correctly!")
            print("💡 The 500/422 errors might be related to authentication or HTTP request handling")
        else:
            print("⚠️ Some tag functions have issues that need to be resolved")

if __name__ == "__main__":
    main()