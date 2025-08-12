#!/usr/bin/env python3
"""
Inspect the actual tag data to understand the format issues
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from models.database import get_db, Transaction
from routers.tags import extract_tags_from_transactions, get_tag_expense_type
from collections import Counter

def main():
    print("🔍 Inspecting Tag Data")
    print("=" * 50)
    
    db = next(get_db())
    
    # Get all transactions with tags
    transactions = db.query(Transaction).filter(
        Transaction.tags != "",
        Transaction.tags.is_not(None),
        Transaction.exclude == False
    ).all()
    
    print(f"📊 Found {len(transactions)} transactions with tags")
    
    # Analyze expense types in transactions
    expense_types = Counter()
    for tx in transactions:
        expense_types[tx.expense_type or 'None'] += 1
    
    print(f"📋 Expense types in tagged transactions:")
    for exp_type, count in expense_types.most_common():
        print(f"   {exp_type}: {count}")
    
    # Extract tags data and examine structure
    tags_data = extract_tags_from_transactions(db)
    print(f"\n🏷️ Found {len(tags_data)} unique tags")
    
    # Examine first few tags
    for i, (tag_name, stats) in enumerate(list(tags_data.items())[:3]):
        print(f"\n📋 Tag: '{tag_name}'")
        print(f"   Transaction count: {stats['transaction_count']}")
        print(f"   Expense types: {dict(stats['expense_types'])}")
        
        # Test get_tag_expense_type function
        primary_type = get_tag_expense_type(stats)
        print(f"   Primary expense type: '{primary_type}' (type: {type(primary_type)})")
    
    # Check what types are returned vs expected
    all_primary_types = set()
    for tag_name, stats in tags_data.items():
        primary_type = get_tag_expense_type(stats)
        all_primary_types.add(primary_type)
    
    print(f"\n🎯 All primary expense types found: {sorted(all_primary_types)}")
    print("💡 Expected types: ['FIXED', 'VARIABLE', 'PROVISION']")
    
    # Check for case sensitivity issues
    expected_types = {"FIXED", "VARIABLE", "PROVISION"}
    found_types = set(all_primary_types)
    
    print(f"\n⚠️  Case sensitivity check:")
    for found_type in found_types:
        if found_type not in expected_types:
            print(f"   '{found_type}' not in expected set")
        else:
            print(f"   '{found_type}' ✅")

if __name__ == "__main__":
    main()