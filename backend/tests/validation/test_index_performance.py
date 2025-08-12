#!/usr/bin/env python3
"""
Database Index Performance Validation Test
Budget Famille v2.3

This script validates the performance impact of the new composite indexes
by running benchmark queries and measuring execution times.
"""

import logging
import time
import sqlite3
import statistics
import datetime as dt
import sys
import os
from typing import List, Dict, Tuple, Optional
import json
import random
from contextlib import contextmanager

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.database import engine, SessionLocal, Transaction, FixedLine, CustomProvision
from services.calculations import calculate_monthly_trends, calculate_category_breakdown, calculate_fixed_lines_total
from services.query_performance import query_monitor, get_query_performance_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IndexPerformanceValidator:
    """Validate database index performance improvements"""
    
    def __init__(self, database_path: str = "./budget.db"):
        self.database_path = database_path
        self.test_results = {}
        
    @contextmanager
    def get_db_session(self):
        """Get database session for testing"""
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def time_query_execution(self, query_func, *args, iterations: int = 5) -> Dict:
        """Time query execution multiple times for statistical analysis"""
        execution_times = []
        results = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                result = query_func(*args)
                execution_time = time.time() - start_time
                execution_times.append(execution_time)
                results.append(len(result) if hasattr(result, '__len__') else 1)
            except Exception as e:
                logger.error(f"Query execution failed on iteration {i+1}: {e}")
                execution_times.append(float('inf'))
                results.append(0)
        
        # Filter out failed executions
        valid_times = [t for t in execution_times if t != float('inf')]
        
        if not valid_times:
            return {
                'error': 'All query executions failed',
                'iterations': iterations,
                'success_rate': 0.0
            }
        
        return {
            'iterations': iterations,
            'success_rate': len(valid_times) / iterations * 100,
            'min_time': min(valid_times),
            'max_time': max(valid_times),
            'avg_time': statistics.mean(valid_times),
            'median_time': statistics.median(valid_times),
            'std_dev': statistics.stdev(valid_times) if len(valid_times) > 1 else 0,
            'total_time': sum(valid_times),
            'avg_result_count': statistics.mean(results) if results else 0
        }
    
    def test_transaction_queries(self) -> Dict:
        """Test transaction table query performance"""
        logger.info("Testing transaction query performance...")
        
        test_results = {}
        
        with self.get_db_session() as db:
            # Test 1: Monthly filtering with exclusions (should use idx_transactions_month_exclude_expense)
            def monthly_expense_filter():
                return db.query(Transaction).filter(
                    Transaction.month == "2024-08",
                    Transaction.exclude == False,
                    Transaction.is_expense == True
                ).all()
            
            test_results['monthly_expense_filter'] = self.time_query_execution(monthly_expense_filter)
            
            # Test 2: Category breakdown query (should use idx_transactions_month_category)
            def category_breakdown_query():
                return db.query(Transaction).filter(
                    Transaction.month == "2024-08",
                    Transaction.category.isnot(None)
                ).all()
            
            test_results['category_breakdown'] = self.time_query_execution(category_breakdown_query)
            
            # Test 3: Date range filtering (should use idx_transactions_date_exclude)
            def date_range_query():
                return db.query(Transaction).filter(
                    Transaction.date_op >= dt.date(2024, 8, 1),
                    Transaction.date_op <= dt.date(2024, 8, 31),
                    Transaction.exclude == False
                ).all()
            
            test_results['date_range_filter'] = self.time_query_execution(date_range_query)
            
            # Test 4: Amount aggregation by category (should use idx_transactions_category_amount)
            def amount_by_category():
                from sqlalchemy import func
                return db.query(
                    Transaction.category,
                    func.sum(Transaction.amount),
                    func.count(Transaction.id)
                ).filter(
                    Transaction.category.isnot(None)
                ).group_by(Transaction.category).all()
            
            test_results['amount_aggregation'] = self.time_query_execution(amount_by_category)
            
            # Test 5: Complex month/date/exclude query (should use idx_transactions_month_date_exclude)
            def complex_filtering():
                return db.query(Transaction).filter(
                    Transaction.month == "2024-08",
                    Transaction.date_op.isnot(None),
                    Transaction.exclude == False
                ).order_by(Transaction.date_op).all()
            
            test_results['complex_filtering'] = self.time_query_execution(complex_filtering)
        
        return test_results
    
    def test_fixed_lines_queries(self) -> Dict:
        """Test fixed lines query performance"""
        logger.info("Testing fixed lines query performance...")
        
        test_results = {}
        
        with self.get_db_session() as db:
            # Test 1: Active fixed lines by frequency (should use idx_fixed_lines_active_freq)
            def active_monthly_lines():
                return db.query(FixedLine).filter(
                    FixedLine.active == True,
                    FixedLine.freq == "mensuelle"
                ).all()
            
            test_results['active_monthly_lines'] = self.time_query_execution(active_monthly_lines)
            
            # Test 2: Category-based filtering (should use idx_fixed_lines_category_active)
            def category_active_lines():
                return db.query(FixedLine).filter(
                    FixedLine.category == "logement",
                    FixedLine.active == True
                ).all()
            
            test_results['category_filtering'] = self.time_query_execution(category_active_lines)
            
            # Test 3: Amount-based sorting (should use idx_fixed_lines_amount_active)
            def amount_sorted_lines():
                return db.query(FixedLine).filter(
                    FixedLine.active == True
                ).order_by(FixedLine.amount.desc()).all()
            
            test_results['amount_sorting'] = self.time_query_execution(amount_sorted_lines)
        
        return test_results
    
    def test_provisions_queries(self) -> Dict:
        """Test custom provisions query performance"""
        logger.info("Testing custom provisions query performance...")
        
        test_results = {}
        
        with self.get_db_session() as db:
            # Test 1: Active provisions by user (should use idx_custom_provisions_active_created_by)
            def active_user_provisions():
                return db.query(CustomProvision).filter(
                    CustomProvision.is_active == True,
                    CustomProvision.created_by == "admin"
                ).all()
            
            test_results['active_user_provisions'] = self.time_query_execution(active_user_provisions)
            
            # Test 2: Date-based filtering (should use idx_custom_provisions_active_dates)
            def date_filtered_provisions():
                current_date = dt.datetime.now()
                return db.query(CustomProvision).filter(
                    CustomProvision.is_active == True,
                    (CustomProvision.start_date == None) | (CustomProvision.start_date <= current_date),
                    (CustomProvision.end_date == None) | (CustomProvision.end_date >= current_date)
                ).all()
            
            test_results['date_filtering'] = self.time_query_execution(date_filtered_provisions)
            
            # Test 3: Display ordering (should use idx_custom_provisions_display_order_active)
            def ordered_provisions():
                return db.query(CustomProvision).filter(
                    CustomProvision.is_active == True
                ).order_by(CustomProvision.display_order, CustomProvision.name).all()
            
            test_results['display_ordering'] = self.time_query_execution(ordered_provisions)
        
        return test_results
    
    def test_calculation_functions(self) -> Dict:
        """Test high-level calculation function performance"""
        logger.info("Testing calculation function performance...")
        
        test_results = {}
        
        with self.get_db_session() as db:
            # Test monthly trends calculation
            def trends_calculation():
                return calculate_monthly_trends(db, ["2024-08", "2024-07", "2024-06"])
            
            test_results['monthly_trends'] = self.time_query_execution(trends_calculation, iterations=3)
            
            # Test category breakdown
            def category_breakdown_calc():
                return calculate_category_breakdown(db, "2024-08")
            
            test_results['category_breakdown'] = self.time_query_execution(category_breakdown_calc, iterations=3)
            
            # Test fixed lines calculation
            from models.database import ensure_default_config
            config = ensure_default_config(db)
            
            def fixed_lines_calc():
                return calculate_fixed_lines_total(db, config)
            
            test_results['fixed_lines_total'] = self.time_query_execution(fixed_lines_calc, iterations=3)
        
        return test_results
    
    def analyze_query_plans(self) -> Dict:
        """Analyze query execution plans to verify index usage"""
        logger.info("Analyzing query execution plans...")
        
        plans = {}
        
        try:
            with sqlite3.connect(self.database_path) as conn:
                test_queries = [
                    {
                        "name": "monthly_expense_filter",
                        "sql": "SELECT * FROM transactions WHERE month = '2024-08' AND exclude = 0 AND is_expense = 1",
                        "expected_index": "idx_transactions_month_exclude_expense"
                    },
                    {
                        "name": "category_breakdown",
                        "sql": "SELECT * FROM transactions WHERE month = '2024-08' AND category IS NOT NULL",
                        "expected_index": "idx_transactions_month_category"
                    },
                    {
                        "name": "date_range_filter",
                        "sql": "SELECT * FROM transactions WHERE date_op >= '2024-08-01' AND exclude = 0",
                        "expected_index": "idx_transactions_date_exclude"
                    },
                    {
                        "name": "active_fixed_lines",
                        "sql": "SELECT * FROM fixed_lines WHERE active = 1 AND freq = 'mensuelle'",
                        "expected_index": "idx_fixed_lines_active_freq"
                    },
                    {
                        "name": "active_provisions",
                        "sql": "SELECT * FROM custom_provisions WHERE is_active = 1 AND created_by = 'admin'",
                        "expected_index": "idx_custom_provisions_active_created_by"
                    }
                ]
                
                for query_info in test_queries:
                    cursor = conn.cursor()
                    cursor.execute(f"EXPLAIN QUERY PLAN {query_info['sql']}")
                    plan = cursor.fetchall()
                    
                    plan_text = " ".join([str(row) for row in plan])
                    index_used = query_info["expected_index"] in plan_text
                    
                    plans[query_info["name"]] = {
                        "sql": query_info["sql"],
                        "expected_index": query_info["expected_index"],
                        "index_used": index_used,
                        "execution_plan": plan,
                        "plan_text": plan_text
                    }
                    
                    if index_used:
                        logger.info(f"✅ Query '{query_info['name']}' uses expected index: {query_info['expected_index']}")
                    else:
                        logger.warning(f"⚠️  Query '{query_info['name']}' does not use expected index: {query_info['expected_index']}")
        
        except Exception as e:
            logger.error(f"Query plan analysis failed: {e}")
            plans['error'] = str(e)
        
        return plans
    
    def benchmark_with_data_sizes(self) -> Dict:
        """Benchmark performance with different data sizes"""
        logger.info("Benchmarking with different data sizes...")
        
        size_benchmarks = {}
        
        with self.get_db_session() as db:
            # Get current data sizes
            transaction_count = db.query(Transaction).count()
            fixed_lines_count = db.query(FixedLine).count()
            provisions_count = db.query(CustomProvision).count()
            
            size_benchmarks['data_sizes'] = {
                'transactions': transaction_count,
                'fixed_lines': fixed_lines_count,
                'custom_provisions': provisions_count
            }
            
            # Performance expectations based on data size
            if transaction_count > 10000:
                expected_performance = "high_volume"
                max_acceptable_time = 0.5  # 500ms max for large datasets
            elif transaction_count > 1000:
                expected_performance = "medium_volume"
                max_acceptable_time = 0.2  # 200ms max for medium datasets
            else:
                expected_performance = "low_volume"
                max_acceptable_time = 0.1  # 100ms max for small datasets
            
            size_benchmarks['performance_category'] = expected_performance
            size_benchmarks['max_acceptable_time'] = max_acceptable_time
            
            # Test a critical query
            def critical_query():
                return db.query(Transaction).filter(
                    Transaction.month.in_(["2024-08", "2024-07"]),
                    Transaction.exclude == False
                ).all()
            
            performance = self.time_query_execution(critical_query)
            size_benchmarks['critical_query_performance'] = performance
            
            # Performance assessment
            avg_time = performance.get('avg_time', float('inf'))
            if avg_time <= max_acceptable_time:
                size_benchmarks['performance_assessment'] = 'excellent'
            elif avg_time <= max_acceptable_time * 2:
                size_benchmarks['performance_assessment'] = 'good'
            elif avg_time <= max_acceptable_time * 4:
                size_benchmarks['performance_assessment'] = 'acceptable'
            else:
                size_benchmarks['performance_assessment'] = 'poor'
        
        return size_benchmarks
    
    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance validation report"""
        logger.info("Generating comprehensive performance report...")
        
        start_time = time.time()
        
        # Run all performance tests
        report = {
            'test_timestamp': dt.datetime.now().isoformat(),
            'database_path': self.database_path,
            'test_results': {}
        }
        
        try:
            # Transaction queries
            report['test_results']['transaction_queries'] = self.test_transaction_queries()
            
            # Fixed lines queries
            report['test_results']['fixed_lines_queries'] = self.test_fixed_lines_queries()
            
            # Provisions queries
            report['test_results']['provisions_queries'] = self.test_provisions_queries()
            
            # Calculation functions
            report['test_results']['calculation_functions'] = self.test_calculation_functions()
            
            # Query plan analysis
            report['query_plan_analysis'] = self.analyze_query_plans()
            
            # Data size benchmarks
            report['data_size_benchmarks'] = self.benchmark_with_data_sizes()
            
            # Query performance monitoring report
            report['query_monitoring'] = get_query_performance_report()
            
        except Exception as e:
            logger.error(f"Error during performance testing: {e}")
            report['error'] = str(e)
        
        total_test_time = time.time() - start_time
        report['total_test_time'] = total_test_time
        
        # Performance summary
        self.calculate_performance_summary(report)
        
        return report
    
    def calculate_performance_summary(self, report: Dict):
        """Calculate overall performance summary"""
        summary = {
            'total_tests': 0,
            'passed_tests': 0,
            'avg_execution_time': 0.0,
            'performance_rating': 'unknown'
        }
        
        all_times = []
        
        # Collect all execution times
        for test_category, tests in report['test_results'].items():
            for test_name, test_result in tests.items():
                if isinstance(test_result, dict) and 'avg_time' in test_result:
                    summary['total_tests'] += 1
                    avg_time = test_result['avg_time']
                    all_times.append(avg_time)
                    
                    # Consider test passed if avg_time < 1.0 seconds
                    if avg_time < 1.0:
                        summary['passed_tests'] += 1
        
        if all_times:
            summary['avg_execution_time'] = statistics.mean(all_times)
            summary['max_execution_time'] = max(all_times)
            summary['min_execution_time'] = min(all_times)
            
            # Performance rating
            avg_time = summary['avg_execution_time']
            if avg_time < 0.1:
                summary['performance_rating'] = 'excellent'
            elif avg_time < 0.5:
                summary['performance_rating'] = 'good'
            elif avg_time < 1.0:
                summary['performance_rating'] = 'acceptable'
            else:
                summary['performance_rating'] = 'poor'
        
        summary['pass_rate'] = (summary['passed_tests'] / summary['total_tests'] * 100) if summary['total_tests'] > 0 else 0
        
        report['performance_summary'] = summary


def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Index Performance Validation")
    parser.add_argument("--database", default="./budget.db", help="Database file path")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--quick", action="store_true", help="Run quick test suite")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.database):
        logger.error(f"Database file not found: {args.database}")
        sys.exit(1)
    
    validator = IndexPerformanceValidator(args.database)
    
    logger.info("🚀 Starting database index performance validation...")
    
    if args.quick:
        # Quick test - just transaction queries
        report = {
            'test_timestamp': dt.datetime.now().isoformat(),
            'database_path': args.database,
            'test_mode': 'quick',
            'test_results': {
                'transaction_queries': validator.test_transaction_queries()
            }
        }
        validator.calculate_performance_summary(report)
    else:
        # Full comprehensive test
        report = validator.generate_performance_report()
    
    # Output results
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"📋 Performance report saved to: {args.output}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
    
    # Print summary
    if 'performance_summary' in report:
        summary = report['performance_summary']
        logger.info(f"🎯 Performance Summary:")
        logger.info(f"   Tests: {summary['passed_tests']}/{summary['total_tests']} passed ({summary['pass_rate']:.1f}%)")
        logger.info(f"   Average execution time: {summary['avg_execution_time']:.3f}s")
        logger.info(f"   Performance rating: {summary['performance_rating'].upper()}")
        
        if summary['performance_rating'] in ['excellent', 'good']:
            logger.info("✅ Database indexes are performing well!")
        else:
            logger.warning("⚠️  Database performance may need optimization")
    
    # Print some key results
    if 'query_plan_analysis' in report:
        index_usage_count = sum(1 for plan in report['query_plan_analysis'].values() 
                               if isinstance(plan, dict) and plan.get('index_used'))
        total_plans = len([p for p in report['query_plan_analysis'].values() if isinstance(p, dict)])
        if total_plans > 0:
            logger.info(f"📊 Index Usage: {index_usage_count}/{total_plans} queries using expected indexes")


if __name__ == "__main__":
    main()