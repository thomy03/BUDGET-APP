#!/usr/bin/env python3
"""
Simple Database Index Validation Script
Budget Famille v2.3

This script validates that the critical performance indexes exist
and are being used by the database query planner.
"""

import sqlite3
import sys
import time
import json
from datetime import datetime


def validate_database_indexes(database_path="./budget.db"):
    """Validate that critical indexes exist and are working"""
    
    print(f"🔍 Validating database indexes: {database_path}")
    
    # Critical indexes that should exist for optimal performance
    EXPECTED_INDEXES = [
        # Transaction performance indexes
        "idx_transactions_month_exclude_expense",
        "idx_transactions_month_category", 
        "idx_transactions_date_exclude",
        "idx_transactions_category_amount",
        "idx_transactions_month_date_exclude",
        "idx_transactions_expense_category_month",
        
        # Fixed lines indexes
        "idx_fixed_lines_active_freq",
        "idx_fixed_lines_category_active", 
        "idx_fixed_lines_amount_active",
        
        # Custom provisions indexes
        "idx_custom_provisions_active_created_by",
        "idx_custom_provisions_active_dates",
        "idx_custom_provisions_display_order_active",
        
        # Metadata indexes
        "idx_import_metadata_created_user",
        "idx_export_history_user_date_status",
        
        # Legacy indexes for compatibility
        "idx_transactions_month_exclude",
        "idx_transactions_category_month",
        "idx_fixed_lines_active"
    ]
    
    results = {
        "validation_timestamp": datetime.now().isoformat(),
        "database_path": database_path,
        "index_validation": {},
        "query_performance_test": {},
        "overall_status": "unknown"
    }
    
    try:
        with sqlite3.connect(database_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            
            # Check which indexes exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            existing_indexes = {row[0] for row in cursor.fetchall()}
            
            print(f"📊 Found {len(existing_indexes)} total indexes in database")
            
            # Validate expected indexes
            missing_indexes = []
            existing_critical_indexes = []
            
            for index_name in EXPECTED_INDEXES:
                if index_name in existing_indexes:
                    existing_critical_indexes.append(index_name)
                    results["index_validation"][index_name] = "exists"
                    print(f"✅ {index_name}")
                else:
                    missing_indexes.append(index_name)
                    results["index_validation"][index_name] = "missing"
                    print(f"❌ {index_name} (MISSING)")
            
            print(f"\n📈 Index Summary:")
            print(f"   Critical indexes found: {len(existing_critical_indexes)}/{len(EXPECTED_INDEXES)}")
            print(f"   Missing indexes: {len(missing_indexes)}")
            
            if missing_indexes:
                print(f"\n⚠️  Missing Critical Indexes:")
                for idx in missing_indexes[:5]:  # Show first 5
                    print(f"   - {idx}")
                if len(missing_indexes) > 5:
                    print(f"   ... and {len(missing_indexes) - 5} more")
            
            # Test query performance on critical queries
            print(f"\n⚡ Testing Query Performance...")
            
            test_queries = [
                {
                    "name": "monthly_transactions", 
                    "sql": "SELECT COUNT(*) FROM transactions WHERE month = '2024-08' AND exclude = 0 LIMIT 1000",
                    "expected_index": "idx_transactions_month_exclude"
                },
                {
                    "name": "active_fixed_lines",
                    "sql": "SELECT COUNT(*) FROM fixed_lines WHERE active = 1 LIMIT 100",
                    "expected_index": "idx_fixed_lines_active"
                },
                {
                    "name": "category_analysis",
                    "sql": "SELECT category, COUNT(*) FROM transactions WHERE month = '2024-08' GROUP BY category LIMIT 50",
                    "expected_index": "idx_transactions_month_category"
                }
            ]
            
            total_query_time = 0
            successful_queries = 0
            
            for test in test_queries:
                try:
                    start_time = time.time()
                    cursor.execute(test["sql"])
                    result = cursor.fetchall()
                    execution_time = time.time() - start_time
                    total_query_time += execution_time
                    
                    # Get query plan
                    cursor.execute(f"EXPLAIN QUERY PLAN {test['sql']}")
                    plan = cursor.fetchall()
                    plan_text = " ".join([str(row) for row in plan])
                    
                    # Check if using an index
                    using_index = "USING INDEX" in plan_text or "INDEX" in plan_text
                    
                    results["query_performance_test"][test["name"]] = {
                        "execution_time": execution_time,
                        "result_count": len(result),
                        "using_index": using_index,
                        "query_plan": plan_text,
                        "status": "success"
                    }
                    
                    status_icon = "🚀" if execution_time < 0.1 else "✅" if execution_time < 0.5 else "⚠️"
                    index_icon = "📍" if using_index else "🔍"
                    
                    print(f"   {status_icon} {test['name']}: {execution_time:.3f}s {index_icon}")
                    successful_queries += 1
                    
                except Exception as e:
                    results["query_performance_test"][test["name"]] = {
                        "error": str(e),
                        "status": "failed"
                    }
                    print(f"   ❌ {test['name']}: ERROR - {e}")
            
            avg_query_time = total_query_time / successful_queries if successful_queries > 0 else float('inf')
            
            # Overall assessment
            index_coverage = len(existing_critical_indexes) / len(EXPECTED_INDEXES)
            performance_good = avg_query_time < 0.5
            
            if index_coverage > 0.8 and performance_good:
                overall_status = "excellent"
                status_icon = "🎉"
                message = "Database indexes are optimally configured!"
            elif index_coverage > 0.6 and avg_query_time < 1.0:
                overall_status = "good"
                status_icon = "✅"
                message = "Database performance is good with room for improvement"
            elif index_coverage > 0.4:
                overall_status = "needs_improvement"
                status_icon = "⚠️"
                message = "Database needs index optimization"
            else:
                overall_status = "poor"
                status_icon = "❌"
                message = "Database performance needs immediate attention"
            
            results["overall_status"] = overall_status
            results["index_coverage_percent"] = index_coverage * 100
            results["avg_query_time"] = avg_query_time
            results["successful_queries"] = successful_queries
            
            print(f"\n{status_icon} Overall Assessment: {overall_status.upper()}")
            print(f"   {message}")
            print(f"   Index coverage: {index_coverage*100:.1f}%")
            print(f"   Average query time: {avg_query_time:.3f}s")
            
            if overall_status in ["needs_improvement", "poor"]:
                print(f"\n💡 Recommendations:")
                print(f"   1. Run the database migration script to create missing indexes")
                print(f"   2. Use: python3 database_performance_migration.py --database {database_path}")
                print(f"   3. Expected 60-70% performance improvement after migration")
            
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        results["error"] = str(e)
        results["overall_status"] = "error"
    
    return results


def main():
    """Main validation execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Index Validation")
    parser.add_argument("--database", default="./budget.db", help="Database file path")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    if not sqlite3:
        print("❌ sqlite3 module not available")
        sys.exit(1)
    
    try:
        # Run validation
        results = validate_database_indexes(args.database)
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n📋 Results saved to: {args.output}")
        
        # Exit with appropriate code
        status = results.get("overall_status", "error")
        if status == "excellent":
            sys.exit(0)
        elif status in ["good", "needs_improvement"]:
            sys.exit(1)  # Warning
        else:
            sys.exit(2)  # Error
            
    except Exception as e:
        print(f"❌ Validation script failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()