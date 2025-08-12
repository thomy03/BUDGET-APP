#!/usr/bin/env python3
"""
Check which database file has the data
"""

import sqlite3
import os

def check_database(db_path, db_name):
    if not os.path.exists(db_path):
        print(f"❌ {db_name}: File does not exist")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if transactions table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions';")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print(f"❌ {db_name}: No transactions table")
            conn.close()
            return
        
        # Count total transactions
        cursor.execute('SELECT COUNT(*) FROM transactions')
        total_count = cursor.fetchone()[0]
        print(f"📊 {db_name}: {total_count} total transactions")
        
        # Count transactions with tags
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE tags IS NOT NULL AND tags != ''")
        tagged_count = cursor.fetchone()[0]
        print(f"🏷️ {db_name}: {tagged_count} transactions with tags")
        
        # Show sample tagged transactions
        if tagged_count > 0:
            cursor.execute("SELECT id, tags, exclude FROM transactions WHERE tags IS NOT NULL AND tags != '' LIMIT 3")
            samples = cursor.fetchall()
            print(f"📋 {db_name} sample tagged transactions:")
            for sample in samples:
                print(f"   ID: {sample[0]}, Tags: '{sample[1]}', Exclude: {sample[2]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ {db_name}: Error - {e}")

def main():
    backend_dir = "/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend"
    
    print("🔍 Checking Database Files")
    print("=" * 50)
    
    check_database(os.path.join(backend_dir, "budget.db"), "budget.db")
    check_database(os.path.join(backend_dir, "database.db"), "database.db")

if __name__ == "__main__":
    main()