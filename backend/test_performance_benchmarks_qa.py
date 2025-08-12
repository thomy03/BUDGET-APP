"""
Performance Benchmarks QA Suite
===============================

Dedicated performance testing for the intelligent classification system.
Validates performance targets: 1000 transactions in <5s with >85% precision.

PERFORMANCE TARGETS:
- Batch processing: 1000 transactions < 5 seconds
- Individual classification: < 10ms per transaction
- Memory usage: < 500MB for large datasets
- Accuracy maintenance: >85% precision under load
- Cache efficiency: >60% hit rate

AUTHOR: Claude Code - Performance QA Specialist
"""

import pytest
import time
import psutil
import statistics
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass

from models.database import SessionLocal, Transaction
from services.expense_classification import (
    ExpenseClassificationService,
    evaluate_classification_performance
)

logger = logging.getLogger(__name__)


@dataclass
class PerformanceBenchmark:
    """Container for performance benchmark results"""
    operation_name: str
    total_operations: int
    total_time_seconds: float
    average_time_ms: float
    throughput_ops_per_second: float
    memory_usage_mb: float
    accuracy_rate: float = 0.0
    
    def meets_targets(self) -> bool:
        """Check if benchmark meets performance targets"""
        if "batch_1000" in self.operation_name.lower():
            return self.total_time_seconds < 5.0 and self.accuracy_rate > 0.85
        elif "individual" in self.operation_name.lower():
            return self.average_time_ms < 10.0
        return True


class PerformanceProfiler:
    """Profile system performance during tests"""
    
    def __init__(self):
        self.start_memory = 0
        self.start_time = 0
        self.process = psutil.Process()
    
    def start_profiling(self):
        """Start performance profiling"""
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.start_time = time.time()
    
    def stop_profiling(self, operation_count: int) -> Tuple[float, float, float, float]:
        """Stop profiling and return metrics"""
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        total_time = end_time - self.start_time
        memory_used = end_memory - self.start_memory
        avg_time_ms = (total_time * 1000) / operation_count
        throughput = operation_count / total_time
        
        return total_time, memory_used, avg_time_ms, throughput


@pytest.fixture
def db_session():
    """Create test database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def classification_service(db_session):
    """Create classification service instance"""
    return ExpenseClassificationService(db_session)


class TestBatchProcessingPerformance:
    """Test batch processing performance targets"""
    
    def test_1000_transaction_performance_target(self, classification_service):
        """Test core requirement: 1000 transactions classified in <5 seconds with >85% accuracy"""
        
        # Generate 1000 realistic test transactions
        test_transactions = self._generate_realistic_transactions(1000)
        
        profiler = PerformanceProfiler()
        profiler.start_profiling()
        
        # Batch classification
        correct_classifications = 0
        classification_results = []
        
        logger.info("🚀 Starting 1000-transaction performance test...")
        
        for i, tx in enumerate(test_transactions):
            if i % 100 == 0:
                logger.info(f"Progress: {i}/1000 transactions processed...")
            
            result = classification_service.classify_expense(
                tag_name=tx["tag"],
                transaction_amount=tx["amount"],
                transaction_description=tx["description"]
            )
            
            classification_results.append(result)
            
            # Check accuracy
            if result.expense_type == tx["expected_type"]:
                correct_classifications += 1
        
        # Stop profiling and analyze results
        total_time, memory_used, avg_time_ms, throughput = profiler.stop_profiling(1000)
        accuracy = correct_classifications / 1000
        
        benchmark = PerformanceBenchmark(
            operation_name="batch_1000_transactions",
            total_operations=1000,
            total_time_seconds=total_time,
            average_time_ms=avg_time_ms,
            throughput_ops_per_second=throughput,
            memory_usage_mb=memory_used,
            accuracy_rate=accuracy
        )
        
        # Log comprehensive results
        logger.info("=" * 60)
        logger.info("📊 1000-TRANSACTION PERFORMANCE BENCHMARK")
        logger.info("=" * 60)
        logger.info(f"⏱️  Total Time: {total_time:.2f} seconds")
        logger.info(f"📈 Throughput: {throughput:.0f} transactions/second")
        logger.info(f"⚡ Average Time: {avg_time_ms:.2f} ms/transaction")
        logger.info(f"🧠 Memory Usage: {memory_used:.1f} MB")
        logger.info(f"🎯 Accuracy Rate: {accuracy:.1%}")
        logger.info(f"✅ Target Met: {benchmark.meets_targets()}")
        logger.info("=" * 60)
        
        # Assert performance targets
        assert total_time < 5.0, f"Batch processing took {total_time:.2f}s, target is <5s"
        assert accuracy > 0.85, f"Accuracy {accuracy:.1%} below 85% target"
        assert throughput > 150, f"Throughput {throughput:.0f} ops/sec below expected minimum"
        
        return benchmark
    
    def test_5000_transaction_scalability(self, classification_service):
        """Test scalability with 5000 transactions (stress test)"""
        
        test_transactions = self._generate_realistic_transactions(5000)
        
        profiler = PerformanceProfiler()
        profiler.start_profiling()
        
        logger.info("🔥 Starting 5000-transaction scalability stress test...")
        
        # Process in chunks for memory efficiency
        chunk_size = 1000
        total_correct = 0
        
        for chunk_start in range(0, 5000, chunk_size):
            chunk_end = min(chunk_start + chunk_size, 5000)
            chunk = test_transactions[chunk_start:chunk_end]
            
            logger.info(f"Processing chunk {chunk_start//chunk_size + 1}/5: transactions {chunk_start}-{chunk_end}")
            
            chunk_correct = 0
            for tx in chunk:
                result = classification_service.classify_expense(
                    tag_name=tx["tag"],
                    transaction_amount=tx["amount"],
                    transaction_description=tx["description"]
                )
                
                if result.expense_type == tx["expected_type"]:
                    chunk_correct += 1
            
            total_correct += chunk_correct
        
        total_time, memory_used, avg_time_ms, throughput = profiler.stop_profiling(5000)
        accuracy = total_correct / 5000
        
        benchmark = PerformanceBenchmark(
            operation_name="scalability_5000_transactions",
            total_operations=5000,
            total_time_seconds=total_time,
            average_time_ms=avg_time_ms,
            throughput_ops_per_second=throughput,
            memory_usage_mb=memory_used,
            accuracy_rate=accuracy
        )
        
        logger.info("🔥 SCALABILITY STRESS TEST RESULTS")
        logger.info(f"⏱️  Total Time: {total_time:.2f} seconds")
        logger.info(f"📈 Throughput: {throughput:.0f} transactions/second") 
        logger.info(f"🧠 Memory Usage: {memory_used:.1f} MB")
        logger.info(f"🎯 Accuracy: {accuracy:.1%}")
        
        # Scalability targets (more lenient than core 1000-tx test)
        assert total_time < 30.0, f"Scalability test took {total_time:.2f}s, should complete within 30s"
        assert accuracy > 0.80, f"Accuracy degraded to {accuracy:.1%}, should maintain >80%"
        assert memory_used < 500.0, f"Memory usage {memory_used:.1f}MB exceeds 500MB limit"
        
        return benchmark
    
    def _generate_realistic_transactions(self, count: int) -> List[Dict]:
        """Generate realistic test transactions with expected classifications"""
        transactions = []
        
        # Template data for realistic transactions
        templates = {
            "FIXED": [
                {"prefix": "netflix", "amounts": [9.99, 15.99, 19.99], "desc": "Netflix Premium"},
                {"prefix": "spotify", "amounts": [9.99, 14.99], "desc": "Spotify Premium"},
                {"prefix": "edf", "amounts": [85.0, 92.5, 78.3], "desc": "EDF Electricity"},
                {"prefix": "orange", "amounts": [35.99, 49.99, 29.99], "desc": "Orange Mobile"},
                {"prefix": "assurance", "amounts": [125.0, 89.5, 156.7], "desc": "Assurance Auto"},
                {"prefix": "mutuelle", "amounts": [67.5, 45.8, 89.2], "desc": "Mutuelle Santé"},
            ],
            "VARIABLE": [
                {"prefix": "carrefour", "amounts": [25.5, 67.8, 123.4, 45.2], "desc": "Carrefour Courses"},
                {"prefix": "restaurant", "amounts": [15.5, 32.7, 8.9, 45.2], "desc": "Restaurant Meal"},
                {"prefix": "pharmacie", "amounts": [12.5, 8.7, 23.4, 18.9], "desc": "Pharmacie Achat"},
                {"prefix": "carburant", "amounts": [45.0, 67.8, 52.3, 78.9], "desc": "Station Total"},
                {"prefix": "vetements", "amounts": [35.9, 89.5, 125.0, 67.3], "desc": "H&M Shopping"},
                {"prefix": "cinema", "amounts": [12.5, 15.0, 18.5], "desc": "Cinema UGC"},
            ]
        }
        
        for i in range(count):
            # Choose expense type (60% variable, 40% fixed - realistic distribution)
            expense_type = "VARIABLE" if i % 10 < 6 else "FIXED"
            
            template = templates[expense_type][i % len(templates[expense_type])]
            amount = template["amounts"][i % len(template["amounts"])]
            
            transactions.append({
                "tag": f"{template['prefix']}_{i}",
                "amount": amount,
                "description": f"{template['desc']} {i}",
                "expected_type": expense_type
            })
        
        return transactions


class TestIndividualTransactionPerformance:
    """Test individual transaction processing performance"""
    
    def test_single_transaction_speed_target(self, classification_service):
        """Test individual transaction processing speed (<10ms target)"""
        
        test_cases = [
            ("netflix_premium", 15.99, "Netflix Premium Subscription"),
            ("carrefour_courses", 67.45, "Carrefour Weekly Shopping"),
            ("edf_electricite", 89.50, "EDF Electricity Bill"),
            ("restaurant_bistro", 32.75, "Le Petit Bistro Dinner"),
            ("pharmacie_centrale", 18.90, "Pharmacie Centrale Medication")
        ]
        
        response_times = []
        
        for tag, amount, description in test_cases:
            # Warm-up classification (exclude from timing)
            classification_service.classify_expense(tag, amount, description)
            
            # Timed classification
            start_time = time.time()
            result = classification_service.classify_expense(tag, amount, description)
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)
            
            # Individual assertion
            assert response_time_ms < 10.0, f"Transaction '{tag}' took {response_time_ms:.2f}ms, target is <10ms"
            
            logger.debug(f"✅ {tag}: {response_time_ms:.2f}ms → {result.expense_type}")
        
        # Statistical analysis
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0
        
        logger.info(f"📊 Individual Transaction Performance:")
        logger.info(f"   Average: {avg_response_time:.2f}ms")
        logger.info(f"   Maximum: {max_response_time:.2f}ms")
        logger.info(f"   Std Dev: {std_dev:.2f}ms")
        
        # Overall targets
        assert avg_response_time < 5.0, f"Average response time {avg_response_time:.2f}ms exceeds 5ms optimal target"
        assert max_response_time < 10.0, f"Maximum response time {max_response_time:.2f}ms exceeds 10ms limit"
        assert std_dev < 3.0, f"Response time inconsistency too high: {std_dev:.2f}ms"
    
    def test_complex_transaction_performance(self, classification_service):
        """Test performance with complex transactions (with history)"""
        
        # Create transaction history for context
        complex_history = [
            {'amount': 49.99, 'date_op': date(2024, i%12+1, 15), 'label': 'Netflix Standard'}
            for i in range(12)  # 12 months of history
        ]
        
        profiler = PerformanceProfiler()
        profiler.start_profiling()
        
        # Test complex classification 100 times
        for i in range(100):
            result = classification_service.classify_expense(
                tag_name="netflix_with_history",
                transaction_amount=49.99,
                transaction_description="Netflix Standard Plan",
                transaction_history=complex_history
            )
            
            assert result.expense_type == "FIXED", "Should classify Netflix as FIXED"
        
        total_time, memory_used, avg_time_ms, throughput = profiler.stop_profiling(100)
        
        logger.info(f"🧠 Complex Transaction Performance:")
        logger.info(f"   Average Time: {avg_time_ms:.2f}ms (with 12-month history)")
        logger.info(f"   Memory Usage: {memory_used:.1f}MB")
        logger.info(f"   Throughput: {throughput:.0f} complex transactions/second")
        
        # Complex transactions should still be reasonably fast
        assert avg_time_ms < 50.0, f"Complex transactions too slow: {avg_time_ms:.2f}ms"
        assert memory_used < 100.0, f"Memory usage too high: {memory_used:.1f}MB"


class TestMemoryPerformance:
    """Test memory usage and efficiency"""
    
    def test_memory_efficiency_large_dataset(self, classification_service):
        """Test memory efficiency with large datasets"""
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        logger.info(f"🧠 Initial memory usage: {initial_memory:.1f}MB")
        
        # Process large dataset
        large_dataset = []
        for i in range(10000):
            large_dataset.append({
                "tag": f"test_tag_{i}",
                "amount": 50.0 + (i % 100),
                "description": f"Test transaction {i}"
            })
        
        # Process dataset in chunks to test memory management
        chunk_size = 1000
        peak_memory = initial_memory
        
        for chunk_start in range(0, 10000, chunk_size):
            chunk_end = min(chunk_start + chunk_size, 10000)
            chunk = large_dataset[chunk_start:chunk_end]
            
            # Process chunk
            for tx in chunk:
                classification_service.classify_expense(
                    tag_name=tx["tag"],
                    transaction_amount=tx["amount"],
                    transaction_description=tx["description"]
                )
            
            # Check memory usage
            current_memory = process.memory_info().rss / 1024 / 1024
            peak_memory = max(peak_memory, current_memory)
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        logger.info(f"🧠 Memory Performance Analysis:")
        logger.info(f"   Initial: {initial_memory:.1f}MB")
        logger.info(f"   Peak: {peak_memory:.1f}MB")
        logger.info(f"   Final: {final_memory:.1f}MB")
        logger.info(f"   Increase: {memory_increase:.1f}MB")
        
        # Memory efficiency targets
        assert memory_increase < 200.0, f"Memory increase {memory_increase:.1f}MB exceeds 200MB limit"
        assert peak_memory < initial_memory + 300.0, f"Peak memory usage {peak_memory:.1f}MB too high"
    
    def test_memory_leak_detection(self, classification_service):
        """Test for memory leaks during repeated operations"""
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_samples = []
        
        # Perform repeated operations and monitor memory
        for cycle in range(10):
            # Process 100 transactions per cycle
            for i in range(100):
                classification_service.classify_expense(
                    tag_name=f"memory_test_{i}",
                    transaction_amount=50.0,
                    transaction_description=f"Memory test transaction {i}"
                )
            
            # Sample memory usage
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            
            logger.debug(f"Cycle {cycle+1}: Memory = {current_memory:.1f}MB")
        
        # Analyze memory trend
        memory_trend = memory_samples[-1] - memory_samples[0]
        max_memory = max(memory_samples)
        
        logger.info(f"🔍 Memory Leak Analysis:")
        logger.info(f"   Initial: {initial_memory:.1f}MB")
        logger.info(f"   Final: {memory_samples[-1]:.1f}MB")
        logger.info(f"   Trend: {memory_trend:+.1f}MB over 10 cycles")
        logger.info(f"   Peak: {max_memory:.1f}MB")
        
        # Memory leak detection
        assert memory_trend < 50.0, f"Potential memory leak detected: {memory_trend:.1f}MB increase"
        assert max_memory < initial_memory + 150.0, f"Peak memory {max_memory:.1f}MB suggests inefficiency"


class TestConcurrencyPerformance:
    """Test performance under concurrent operations"""
    
    @pytest.mark.asyncio
    async def test_concurrent_classification_performance(self, classification_service):
        """Test performance with concurrent classification requests"""
        
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def classify_transaction(tx_data):
            """Helper function for threaded classification"""
            return classification_service.classify_expense(
                tag_name=tx_data["tag"],
                transaction_amount=tx_data["amount"],
                transaction_description=tx_data["description"]
            )
        
        # Create concurrent test data
        concurrent_transactions = [
            {"tag": f"concurrent_test_{i}", "amount": 50.0 + i, "description": f"Concurrent test {i}"}
            for i in range(50)
        ]
        
        start_time = time.time()
        
        # Execute concurrent classifications
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(classify_transaction, tx)
                for tx in concurrent_transactions
            ]
            
            results = [future.result() for future in futures]
        
        total_time = time.time() - start_time
        throughput = len(concurrent_transactions) / total_time
        
        logger.info(f"🔀 Concurrent Performance:")
        logger.info(f"   Transactions: {len(concurrent_transactions)}")
        logger.info(f"   Total Time: {total_time:.2f}s")
        logger.info(f"   Throughput: {throughput:.0f} concurrent ops/sec")
        
        # Validate results
        assert len(results) == len(concurrent_transactions), "Some concurrent operations failed"
        assert total_time < 10.0, f"Concurrent processing took {total_time:.2f}s, should complete faster"
        assert throughput > 5, f"Concurrent throughput {throughput:.0f} ops/sec too low"
        
        # Ensure all results are valid
        for result in results:
            assert result.expense_type in ["FIXED", "VARIABLE"], "Invalid concurrent result"
            assert 0.0 <= result.confidence <= 1.0, "Invalid confidence in concurrent result"


if __name__ == "__main__":
    # Run performance benchmark tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings",
        "-s"  # Show print statements for performance monitoring
    ])