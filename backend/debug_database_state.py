#!/usr/bin/env python3
"""
Debug database state to understand the inconsistent tag results
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from models.database import get_db, Transaction

def main():
    print("🔍 Debug Database State")
    print("=" * 50)
    
    db = next(get_db())
    
    # Check total transactions
    total_txs = db.query(Transaction).count()
    print(f"📊 Total transactions: {total_txs}")
    
    # Check transactions with tags (not null and not empty)
    txs_with_tags = db.query(Transaction).filter(
        Transaction.tags != "",
        Transaction.tags.is_not(None)
    ).all()
    
    print(f"📊 Transactions with tags (tags != '' AND tags IS NOT NULL): {len(txs_with_tags)}")
    
    # Check transactions not excluded
    txs_not_excluded = db.query(Transaction).filter(
        Transaction.exclude == False
    ).count()
    print(f"📊 Transactions not excluded: {txs_not_excluded}")
    
    # Check transactions with tags AND not excluded
    txs_with_tags_not_excluded = db.query(Transaction).filter(
        Transaction.tags != "",
        Transaction.tags.is_not(None),
        Transaction.exclude == False
    ).all()
    
    print(f"📊 Transactions with tags AND not excluded: {len(txs_with_tags_not_excluded)}")
    
    # Show sample of transactions with tags
    print(f"\n📋 Sample transactions with tags:")
    for i, tx in enumerate(txs_with_tags_not_excluded[:5]):
        print(f"   {i+1}. ID: {tx.id}, Tags: '{tx.tags}', Excluded: {tx.exclude}, Amount: {tx.amount}")
    
    # Check what's in the exclude column
    exclude_values = db.query(Transaction.exclude).distinct().all()
    print(f"\n🔍 Distinct exclude values in database: {[v[0] for v in exclude_values]}")
    
    # Check exclude column type
    sample_tx = db.query(Transaction).first()
    if sample_tx:
        print(f"🔍 Sample exclude value type: {type(sample_tx.exclude)} -> {sample_tx.exclude}")
    
    # Manual test of the exact query from extract_tags_from_transactions
    print(f"\n🧪 Testing exact query from extract_tags_from_transactions:")
    exact_query = db.query(Transaction).filter(
        Transaction.tags != "",
        Transaction.tags.is_not(None),
        Transaction.exclude == False
    )
    print(f"   Query: {exact_query}")
    exact_results = exact_query.all()
    print(f"   Results: {len(exact_results)} transactions")
    
    if len(exact_results) > 0:
        print("   ✅ Query returns results")
        # Extract tags from these results
        from collections import defaultdict, Counter
        
        tags_data = defaultdict(lambda: {
            'transactions': [],
            'total_amount': 0.0,
            'transaction_count': 0,
            'last_used': None,
            'expense_types': Counter(),
            'categories': Counter(),
            'merchants': Counter()
        })
        
        for tx in exact_results:
            if not tx.tags:
                continue
                
            # Split tags by comma and clean them
            tx_tags = [tag.strip().lower() for tag in tx.tags.split(',') if tag.strip()]
            print(f"   Transaction {tx.id}: tags='{tx.tags}' -> parsed: {tx_tags}")
            
            for tag in tx_tags:
                tag_data = tags_data[tag]
                tag_data['transactions'].append(tx)
                tag_data['total_amount'] += abs(tx.amount) if tx.amount else 0
                tag_data['transaction_count'] += 1
                
                # Update counters
                tag_data['expense_types'][tx.expense_type or 'VARIABLE'] += 1
        
        print(f"   ✅ Extracted {len(tags_data)} unique tags: {list(tags_data.keys())}")
    else:
        print("   ❌ Query returns no results")

if __name__ == "__main__":
    main()