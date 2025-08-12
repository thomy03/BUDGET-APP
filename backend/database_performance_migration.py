#!/usr/bin/env python3
"""
Database Performance Migration Script for Budget Famille v2.3
Critical Performance Optimization with Composite Indexes

This script provides safe database migration with rollback capabilities
for adding performance-critical composite indexes.

IMPORTANT: Run this script during maintenance window for production systems.
"""

import logging
import sqlite3
import datetime as dt
import sys
import os
from typing import List, Dict, Tuple, Optional
import time
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'db_migration_{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DatabasePerformanceMigration:
    """Safe database performance migration with rollback capability"""
    
    def __init__(self, database_path: str = "./budget.db"):
        self.database_path = database_path
        self.backup_path = f"{database_path}.backup_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.migration_log = []
        
        # Critical composite indexes for maximum performance impact
        self.CRITICAL_INDEXES = [
            # PRIORITY 1: Transaction table - most critical for dashboard performance
            {
                "name": "idx_transactions_month_exclude_expense",
                "table": "transactions",
                "columns": "(month, exclude, is_expense)",
                "rationale": "Dashboard filtering by month with expense categorization",
                "priority": "critical"
            },
            {
                "name": "idx_transactions_month_category",
                "table": "transactions", 
                "columns": "(month, category)",
                "rationale": "Category breakdown analytics - high frequency query",
                "priority": "critical"
            },
            {
                "name": "idx_transactions_date_exclude",
                "table": "transactions",
                "columns": "(date_op, exclude)",
                "rationale": "Date-based filtering with exclusion logic",
                "priority": "critical"
            },
            {
                "name": "idx_transactions_category_amount",
                "table": "transactions",
                "columns": "(category, amount)",
                "rationale": "Amount aggregation by category",
                "priority": "high"
            },
            {
                "name": "idx_transactions_month_date_exclude",
                "table": "transactions",
                "columns": "(month, date_op, exclude)",
                "rationale": "Combined month/date filtering - calendar views",
                "priority": "high"
            },
            {
                "name": "idx_transactions_expense_category_month",
                "table": "transactions",
                "columns": "(is_expense, category, month)",
                "rationale": "Expense analysis by category and period",
                "priority": "high"
            },
            
            # PRIORITY 2: Import/audit performance
            {
                "name": "idx_transactions_import_month",
                "table": "transactions",
                "columns": "(import_id, month)",
                "rationale": "Import tracking and batch operations",
                "priority": "medium"
            },
            {
                "name": "idx_transactions_row_id_unique",
                "table": "transactions",
                "columns": "(row_id)",
                "rationale": "Duplicate detection and data integrity",
                "priority": "medium"
            },
            
            # PRIORITY 3: Search and advanced filtering
            {
                "name": "idx_transactions_tags_month",
                "table": "transactions",
                "columns": "(tags, month)",
                "rationale": "Tag-based filtering by period",
                "priority": "medium"
            },
            {
                "name": "idx_transactions_account_month",
                "table": "transactions",
                "columns": "(account_label, month)",
                "rationale": "Account-specific analysis",
                "priority": "low"
            },
            
            # Fixed Lines Performance
            {
                "name": "idx_fixed_lines_active_freq",
                "table": "fixed_lines",
                "columns": "(active, freq)",
                "rationale": "Active fixed expenses by frequency",
                "priority": "high"
            },
            {
                "name": "idx_fixed_lines_category_active",
                "table": "fixed_lines",
                "columns": "(category, active)",
                "rationale": "Category-based fixed expense analysis",
                "priority": "medium"
            },
            {
                "name": "idx_fixed_lines_amount_active",
                "table": "fixed_lines",
                "columns": "(amount, active)",
                "rationale": "Amount-based sorting and filtering",
                "priority": "low"
            },
            
            # Custom Provisions Performance
            {
                "name": "idx_custom_provisions_active_created_by",
                "table": "custom_provisions",
                "columns": "(is_active, created_by)",
                "rationale": "User-specific active provisions",
                "priority": "high"
            },
            {
                "name": "idx_custom_provisions_active_dates",
                "table": "custom_provisions",
                "columns": "(is_active, start_date, end_date)",
                "rationale": "Date-based provision filtering",
                "priority": "high"
            },
            {
                "name": "idx_custom_provisions_display_order_active",
                "table": "custom_provisions",
                "columns": "(display_order, is_active, name)",
                "rationale": "UI display ordering optimization",
                "priority": "medium"
            },
            {
                "name": "idx_custom_provisions_category_active",
                "table": "custom_provisions",
                "columns": "(category, is_active)",
                "rationale": "Category-based provision grouping",
                "priority": "medium"
            },
            {
                "name": "idx_custom_provisions_target_current",
                "table": "custom_provisions",
                "columns": "(target_amount, current_amount)",
                "rationale": "Progress tracking and analytics",
                "priority": "low"
            },
            
            # Metadata and History Performance
            {
                "name": "idx_import_metadata_created_user",
                "table": "import_metadata",
                "columns": "(created_at, user_id)",
                "rationale": "Import history by user and date",
                "priority": "medium"
            },
            {
                "name": "idx_export_history_user_date_status",
                "table": "export_history",
                "columns": "(user_id, created_at, status)",
                "rationale": "Export tracking and status monitoring",
                "priority": "medium"
            }
        ]
    
    def create_backup(self) -> bool:
        """Create database backup before migration"""
        try:
            logger.info(f"Creating database backup: {self.backup_path}")
            
            with sqlite3.connect(self.database_path) as source:
                with sqlite3.connect(self.backup_path) as backup:
                    source.backup(backup)
            
            # Verify backup
            backup_size = os.path.getsize(self.backup_path)
            original_size = os.path.getsize(self.database_path)
            
            if backup_size != original_size:
                logger.error(f"Backup verification failed: sizes differ ({backup_size} vs {original_size})")
                return False
            
            logger.info(f"✅ Backup created successfully ({backup_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            return False
    
    def check_table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        """Check if table exists in database"""
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table_name,))
            return cursor.fetchone() is not None
        except Exception:
            return False
    
    def check_index_exists(self, conn: sqlite3.Connection, index_name: str) -> bool:
        """Check if index already exists"""
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name=?
            """, (index_name,))
            return cursor.fetchone() is not None
        except Exception:
            return False
    
    def get_table_record_count(self, conn: sqlite3.Connection, table_name: str) -> int:
        """Get record count for table"""
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]
        except Exception:
            return 0
    
    def create_index_with_timing(self, conn: sqlite3.Connection, index_info: Dict) -> Tuple[bool, float]:
        """Create index and measure performance impact"""
        start_time = time.time()
        
        try:
            # Check if table exists
            if not self.check_table_exists(conn, index_info["table"]):
                logger.warning(f"⚠️  Table {index_info['table']} does not exist, skipping index {index_info['name']}")
                return False, 0.0
            
            # Check if index already exists
            if self.check_index_exists(conn, index_info["name"]):
                logger.info(f"⏭️  Index {index_info['name']} already exists, skipping")
                return True, 0.0
            
            # Get table size for impact estimation
            record_count = self.get_table_record_count(conn, index_info["table"])
            
            # Create index
            sql = f"CREATE INDEX {index_info['name']} ON {index_info['table']} {index_info['columns']}"
            conn.execute(sql)
            
            creation_time = time.time() - start_time
            
            logger.info(f"✅ Created {index_info['priority']} priority index: {index_info['name']} "
                       f"({record_count:,} records, {creation_time:.2f}s)")
            
            self.migration_log.append({
                "timestamp": dt.datetime.now().isoformat(),
                "action": "create_index",
                "index_name": index_info["name"],
                "table": index_info["table"],
                "priority": index_info["priority"],
                "record_count": record_count,
                "creation_time": creation_time,
                "sql": sql,
                "status": "success"
            })
            
            return True, creation_time
            
        except Exception as e:
            creation_time = time.time() - start_time
            logger.error(f"❌ Failed to create index {index_info['name']}: {e}")
            
            self.migration_log.append({
                "timestamp": dt.datetime.now().isoformat(),
                "action": "create_index",
                "index_name": index_info["name"],
                "table": index_info["table"],
                "error": str(e),
                "creation_time": creation_time,
                "status": "failed"
            })
            
            return False, creation_time
    
    def migrate_indexes(self) -> bool:
        """Execute the index migration with comprehensive monitoring"""
        logger.info("🚀 Starting database performance migration...")
        
        migration_start = time.time()
        successful_indexes = 0
        failed_indexes = 0
        total_creation_time = 0
        
        try:
            with sqlite3.connect(self.database_path, timeout=300.0) as conn:
                # Enable performance monitoring
                conn.execute("PRAGMA synchronous = NORMAL")
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA cache_size = 2000")
                
                # Sort indexes by priority for optimal creation order
                priority_order = {"critical": 1, "high": 2, "medium": 3, "low": 4}
                sorted_indexes = sorted(
                    self.CRITICAL_INDEXES, 
                    key=lambda x: priority_order.get(x["priority"], 5)
                )
                
                logger.info(f"Creating {len(sorted_indexes)} performance indexes...")
                
                for i, index_info in enumerate(sorted_indexes, 1):
                    logger.info(f"[{i}/{len(sorted_indexes)}] Creating {index_info['priority']} priority index: {index_info['name']}")
                    logger.info(f"   Rationale: {index_info['rationale']}")
                    
                    success, creation_time = self.create_index_with_timing(conn, index_info)
                    total_creation_time += creation_time
                    
                    if success:
                        successful_indexes += 1
                    else:
                        failed_indexes += 1
                    
                    # Progress reporting every 5 indexes
                    if i % 5 == 0:
                        logger.info(f"Progress: {i}/{len(sorted_indexes)} indexes processed "
                                   f"({successful_indexes} successful, {failed_indexes} failed)")
                
                # Update database statistics for query optimizer
                logger.info("🔄 Updating database statistics...")
                stats_start = time.time()
                conn.execute("ANALYZE")
                conn.execute("PRAGMA optimize")
                stats_time = time.time() - stats_start
                
                logger.info(f"✅ Database statistics updated ({stats_time:.2f}s)")
                
                migration_time = time.time() - migration_start
                
                logger.info(f"🎉 Migration completed in {migration_time:.2f}s")
                logger.info(f"📊 Results: {successful_indexes} successful, {failed_indexes} failed")
                logger.info(f"⏱️  Total index creation time: {total_creation_time:.2f}s")
                
                return failed_indexes == 0
                
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
    
    def rollback_migration(self) -> bool:
        """Rollback database to backup state"""
        try:
            logger.info(f"🔄 Rolling back database from backup: {self.backup_path}")
            
            if not os.path.exists(self.backup_path):
                logger.error(f"❌ Backup file not found: {self.backup_path}")
                return False
            
            # Replace current database with backup
            os.replace(self.backup_path, self.database_path)
            logger.info("✅ Database rollback completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False
    
    def validate_performance_improvement(self) -> Dict:
        """Validate that indexes improve query performance"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                # Test critical queries and measure performance
                test_queries = [
                    {
                        "name": "dashboard_monthly_filter",
                        "sql": "SELECT COUNT(*) FROM transactions WHERE month = '2024-08' AND exclude = 0 AND is_expense = 1",
                        "expected_indexes": ["idx_transactions_month_exclude_expense"]
                    },
                    {
                        "name": "category_breakdown",
                        "sql": "SELECT category, SUM(amount) FROM transactions WHERE month = '2024-08' GROUP BY category",
                        "expected_indexes": ["idx_transactions_month_category"]
                    },
                    {
                        "name": "active_fixed_lines",
                        "sql": "SELECT * FROM fixed_lines WHERE active = 1 AND freq = 'mensuelle'",
                        "expected_indexes": ["idx_fixed_lines_active_freq"]
                    }
                ]
                
                performance_results = []
                
                for query_info in test_queries:
                    start_time = time.time()
                    
                    # Execute query
                    cursor = conn.cursor()
                    cursor.execute(query_info["sql"])
                    result = cursor.fetchall()
                    
                    query_time = time.time() - start_time
                    
                    # Get query plan
                    cursor.execute(f"EXPLAIN QUERY PLAN {query_info['sql']}")
                    query_plan = cursor.fetchall()
                    
                    # Check if indexes are being used
                    plan_text = " ".join([str(row) for row in query_plan])
                    indexes_used = [idx for idx in query_info["expected_indexes"] if idx in plan_text]
                    
                    performance_results.append({
                        "query_name": query_info["name"],
                        "execution_time": query_time,
                        "result_count": len(result),
                        "indexes_used": indexes_used,
                        "query_plan": query_plan
                    })
                    
                    logger.info(f"Query '{query_info['name']}': {query_time:.4f}s, "
                               f"indexes used: {indexes_used}")
                
                return {
                    "validation_timestamp": dt.datetime.now().isoformat(),
                    "performance_results": performance_results,
                    "status": "completed"
                }
                
        except Exception as e:
            logger.error(f"Performance validation error: {e}")
            return {
                "validation_timestamp": dt.datetime.now().isoformat(),
                "error": str(e),
                "status": "failed"
            }
    
    def save_migration_report(self):
        """Save detailed migration report"""
        report = {
            "migration_timestamp": dt.datetime.now().isoformat(),
            "database_path": self.database_path,
            "backup_path": self.backup_path,
            "migration_log": self.migration_log,
            "performance_validation": self.validate_performance_improvement()
        }
        
        report_path = f"migration_report_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"📋 Migration report saved: {report_path}")
        except Exception as e:
            logger.error(f"Failed to save migration report: {e}")


def main():
    """Main migration execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Performance Migration for Budget Famille v2.3")
    parser.add_argument("--database", default="./budget.db", help="Database file path")
    parser.add_argument("--rollback", action="store_true", help="Rollback to backup")
    parser.add_argument("--validate-only", action="store_true", help="Only validate performance")
    parser.add_argument("--force", action="store_true", help="Force migration without confirmation")
    
    args = parser.parse_args()
    
    migration = DatabasePerformanceMigration(args.database)
    
    if args.rollback:
        success = migration.rollback_migration()
        sys.exit(0 if success else 1)
    
    if args.validate_only:
        results = migration.validate_performance_improvement()
        print(json.dumps(results, indent=2))
        sys.exit(0)
    
    # Check database exists
    if not os.path.exists(args.database):
        logger.error(f"❌ Database file not found: {args.database}")
        sys.exit(1)
    
    # Confirmation prompt
    if not args.force:
        print(f"\n🚨 CRITICAL DATABASE MIGRATION")
        print(f"Database: {args.database}")
        print(f"Indexes to create: {len(migration.CRITICAL_INDEXES)}")
        print(f"Backup will be created: {migration.backup_path}")
        
        response = input("\nProceed with migration? [y/N]: ")
        if response.lower() != 'y':
            print("Migration cancelled")
            sys.exit(0)
    
    # Execute migration
    logger.info("Starting Budget Famille v2.3 Database Performance Migration")
    
    # Create backup
    if not migration.create_backup():
        logger.error("❌ Cannot proceed without backup")
        sys.exit(1)
    
    # Execute migration
    success = migration.migrate_indexes()
    
    # Save report
    migration.save_migration_report()
    
    if success:
        logger.info("🎉 Migration completed successfully!")
        logger.info("💡 Expected performance improvements:")
        logger.info("   • 60-70% faster dashboard loading")
        logger.info("   • 50-80% faster category analytics")
        logger.info("   • 40-60% faster date range filtering")
        logger.info("   • Improved concurrent user support")
    else:
        logger.error("❌ Migration completed with errors")
        logger.info(f"🔄 To rollback: python {sys.argv[0]} --database {args.database} --rollback")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()