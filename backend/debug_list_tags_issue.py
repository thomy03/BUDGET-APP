#!/usr/bin/env python3
"""
Debug why list_tags is returning 0 tags when extract_tags_from_transactions returns 8
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from models.database import get_db
from routers.tags import extract_tags_from_transactions, get_tag_expense_type, get_tag_patterns
from models.schemas import TagOut
from datetime import datetime

def main():
    print("🔍 Debug list_tags Issue")
    print("=" * 50)
    
    db = next(get_db())
    
    # Extract tags data
    tags_data = extract_tags_from_transactions(db)
    print(f"📊 extract_tags_from_transactions found: {len(tags_data)} tags")
    
    # Simulate the list_tags logic step by step
    tags_list = []
    tag_id = 1
    
    for tag_name, stats in tags_data.items():
        print(f"\n🏷️ Processing tag: '{tag_name}'")
        print(f"   Transaction count: {stats['transaction_count']}")
        print(f"   Total amount: {stats['total_amount']}")
        
        # Apply filters (same as in list_tags)
        primary_expense_type = get_tag_expense_type(stats)
        print(f"   Primary expense type: '{primary_expense_type}'")
        
        primary_category = stats['categories'].most_common(1)[0][0] if stats['categories'] else None
        print(f"   Primary category: '{primary_category}'")
        
        # Check for filtering (there are no filters in our test, so this shouldn't filter anything)
        expense_type = None  # No filter
        category = None      # No filter
        min_usage = None     # No filter
        
        if expense_type and primary_expense_type != expense_type:
            print(f"   ❌ FILTERED by expense_type: {expense_type} != {primary_expense_type}")
            continue
        if category and primary_category != category:
            print(f"   ❌ FILTERED by category: {category} != {primary_category}")
            continue
        if min_usage and stats['transaction_count'] < min_usage:
            print(f"   ❌ FILTERED by min_usage: {stats['transaction_count']} < {min_usage}")
            continue
            
        print(f"   ✅ PASSED filters")
        
        # Get patterns for this tag
        patterns = get_tag_patterns(db, tag_name)
        print(f"   Patterns: {patterns}")
        
        # Create TagOut object
        try:
            tag_out = TagOut(
                id=tag_id,
                name=tag_name,
                expense_type=primary_expense_type,
                transaction_count=stats['transaction_count'],
                total_amount=stats['total_amount'],
                patterns=patterns,
                category=primary_category,
                created_at=datetime.now(),
                last_used=stats['last_used']
            )
            
            tags_list.append(tag_out)
            print(f"   ✅ TagOut created successfully")
            tag_id += 1
            
        except Exception as e:
            print(f"   ❌ ERROR creating TagOut: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n📊 Final result: {len(tags_list)} tags created")
    
    if len(tags_list) == 0:
        print("\n🚨 ISSUE FOUND: No tags were created despite having tag data")
        print("This suggests there's an error in the TagOut creation process")
    else:
        print("\n✅ Tags created successfully")
        for tag in tags_list[:3]:  # Show first 3 tags
            print(f"   - {tag.name}: {tag.transaction_count} transactions, {tag.expense_type}")

if __name__ == "__main__":
    main()