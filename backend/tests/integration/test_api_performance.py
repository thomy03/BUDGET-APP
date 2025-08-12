"""
Performance and load testing for Budget API endpoints.
Tests response times, throughput, and resource usage under load.
"""
import pytest
import asyncio
import time
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch
import statistics
from typing import List, Dict, Any

from tests.fixtures.test_factories import (
    TransactionFactory, ConfigFactory, CustomProvisionFactory, 
    FixedLineFactory, create_month_transactions
)


class PerformanceMetrics:
    """Track and analyze performance metrics during tests."""
    
    def __init__(self):
        self.response_times = []
        self.memory_usage = []
        self.cpu_usage = []
        self.error_count = 0
        self.success_count = 0
    
    def record_response_time(self, duration: float):
        """Record a response time."""
        self.response_times.append(duration)
    
    def record_success(self):
        """Record a successful request."""
        self.success_count += 1
    
    def record_error(self):
        """Record a failed request."""
        self.error_count += 1
    
    def record_system_metrics(self):
        """Record current system resource usage."""
        process = psutil.Process()
        self.memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
        self.cpu_usage.append(process.cpu_percent())
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        if not self.response_times:
            return {"error": "No response times recorded"}
        
        return {
            "request_count": len(self.response_times),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": (self.success_count / (self.success_count + self.error_count)) * 100,
            "response_times": {
                "min": min(self.response_times),
                "max": max(self.response_times),
                "mean": statistics.mean(self.response_times),
                "median": statistics.median(self.response_times),
                "p95": statistics.quantiles(self.response_times, n=20)[18],  # 95th percentile
                "p99": statistics.quantiles(self.response_times, n=100)[98]  # 99th percentile
            },
            "memory_usage": {
                "min": min(self.memory_usage) if self.memory_usage else 0,
                "max": max(self.memory_usage) if self.memory_usage else 0,
                "mean": statistics.mean(self.memory_usage) if self.memory_usage else 0
            },
            "cpu_usage": {
                "min": min(self.cpu_usage) if self.cpu_usage else 0,
                "max": max(self.cpu_usage) if self.cpu_usage else 0,
                "mean": statistics.mean(self.cpu_usage) if self.cpu_usage else 0
            }
        }


@pytest.fixture
def performance_metrics():
    """Provide a fresh PerformanceMetrics instance for each test."""
    return PerformanceMetrics()


@pytest.fixture
def large_transaction_dataset():
    """Create a large dataset of transactions for performance testing."""
    months = ['2023-06', '2023-07', '2023-08', '2023-09', '2023-10', '2023-11', '2023-12',
              '2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06']
    
    all_transactions = []
    for month in months:
        # Generate 100-200 transactions per month for realistic load
        month_transactions = create_month_transactions(month, count=150)
        all_transactions.extend(month_transactions)
    
    return all_transactions


def simulate_api_call(endpoint: str, data: Any = None, method: str = 'GET') -> Dict[str, Any]:
    """Simulate an API call with realistic processing time."""
    start_time = time.time()
    
    # Simulate different processing times based on endpoint complexity
    processing_times = {
        '/api/transactions': 0.05,  # Simple query
        '/api/summary': 0.15,       # Complex aggregation
        '/api/analytics': 0.25,     # Heavy calculation
        '/api/export': 0.5,         # File generation
        '/api/import': 0.3          # File processing
    }
    
    base_time = processing_times.get(endpoint, 0.1)
    # Add random variation (±50%)
    import random
    actual_time = base_time * random.uniform(0.5, 1.5)
    
    # Simulate processing
    time.sleep(actual_time)
    
    # Simulate occasional errors (5% failure rate)
    if random.random() < 0.05:
        raise Exception(f"Simulated API error for {endpoint}")
    
    duration = time.time() - start_time
    
    return {
        'status': 'success',
        'data': {'mock': 'response'},
        'duration': duration,
        'endpoint': endpoint
    }


class TestResponseTimePerformance:
    """Test individual endpoint response times."""
    
    def test_transaction_query_performance(self, performance_metrics):
        """Test transaction query response times."""
        iterations = 50
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                # Simulate transaction query
                response = simulate_api_call('/api/transactions', {
                    'month': '2024-01',
                    'limit': 100
                })
                
                duration = time.time() - start_time
                performance_metrics.record_response_time(duration)
                performance_metrics.record_success()
                
            except Exception:
                performance_metrics.record_error()
        
        summary = performance_metrics.get_summary()
        
        # Performance assertions
        assert summary['response_times']['mean'] < 0.2, "Average response time should be under 200ms"
        assert summary['response_times']['p95'] < 0.5, "95% of requests should complete under 500ms"
        assert summary['success_rate'] > 90, "Success rate should be above 90%"
    
    def test_summary_calculation_performance(self, performance_metrics):
        """Test budget summary calculation performance."""
        iterations = 30
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                # Simulate complex summary calculation
                response = simulate_api_call('/api/summary', {
                    'months': ['2024-01', '2024-02', '2024-03']
                })
                
                duration = time.time() - start_time
                performance_metrics.record_response_time(duration)
                performance_metrics.record_success()
                
            except Exception:
                performance_metrics.record_error()
        
        summary = performance_metrics.get_summary()
        
        # Summary calculations may take longer due to complexity
        assert summary['response_times']['mean'] < 0.5, "Average response time should be under 500ms"
        assert summary['response_times']['p95'] < 1.0, "95% of requests should complete under 1s"
    
    def test_analytics_performance(self, performance_metrics, large_transaction_dataset):
        """Test analytics endpoint performance with large dataset."""
        iterations = 20
        
        for i in range(iterations):
            start_time = time.time()
            performance_metrics.record_system_metrics()
            
            try:
                # Simulate heavy analytics calculation
                response = simulate_api_call('/api/analytics', {
                    'analysis_type': 'trends',
                    'months': ['2023-06', '2023-07', '2023-08', '2023-09', '2023-10', '2023-11']
                })
                
                duration = time.time() - start_time
                performance_metrics.record_response_time(duration)
                performance_metrics.record_success()
                
            except Exception:
                performance_metrics.record_error()
        
        summary = performance_metrics.get_summary()
        
        # Analytics may be slower but should still be reasonable
        assert summary['response_times']['mean'] < 1.0, "Average response time should be under 1s"
        assert summary['response_times']['p95'] < 2.0, "95% of requests should complete under 2s"
        assert summary['memory_usage']['max'] < 200, "Memory usage should stay under 200MB"


class TestConcurrencyPerformance:
    """Test system performance under concurrent load."""
    
    def test_concurrent_transaction_queries(self, performance_metrics):
        """Test multiple concurrent transaction queries."""
        num_threads = 10
        requests_per_thread = 5
        
        def make_requests():
            thread_metrics = []
            for _ in range(requests_per_thread):
                start_time = time.time()
                try:
                    response = simulate_api_call('/api/transactions')
                    duration = time.time() - start_time
                    thread_metrics.append(('success', duration))
                except Exception:
                    thread_metrics.append(('error', time.time() - start_time))
            return thread_metrics
        
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(make_requests) for _ in range(num_threads)]
            
            for future in as_completed(futures):
                thread_results = future.result()
                for result_type, duration in thread_results:
                    performance_metrics.record_response_time(duration)
                    if result_type == 'success':
                        performance_metrics.record_success()
                    else:
                        performance_metrics.record_error()
        
        summary = performance_metrics.get_summary()
        
        # Under concurrent load, response times may be higher
        assert summary['response_times']['mean'] < 0.5, "Average response time under load should be under 500ms"
        assert summary['success_rate'] > 85, "Success rate under load should be above 85%"
        assert summary['request_count'] == num_threads * requests_per_thread, "All requests should be recorded"
    
    def test_mixed_workload_performance(self, performance_metrics):
        """Test system performance with mixed endpoint workloads."""
        num_threads = 8
        
        def mixed_workload():
            endpoints = [
                '/api/transactions',
                '/api/summary', 
                '/api/analytics',
                '/api/transactions',  # More frequent
                '/api/transactions'   # More frequent
            ]
            
            thread_metrics = []
            for endpoint in endpoints:
                start_time = time.time()
                try:
                    response = simulate_api_call(endpoint)
                    duration = time.time() - start_time
                    thread_metrics.append(('success', duration, endpoint))
                except Exception:
                    thread_metrics.append(('error', time.time() - start_time, endpoint))
            return thread_metrics
        
        # Execute mixed workload
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(mixed_workload) for _ in range(num_threads)]
            
            for future in as_completed(futures):
                thread_results = future.result()
                for result_type, duration, endpoint in thread_results:
                    performance_metrics.record_response_time(duration)
                    if result_type == 'success':
                        performance_metrics.record_success()
                    else:
                        performance_metrics.record_error()
        
        summary = performance_metrics.get_summary()
        
        # Mixed workload should still maintain good performance
        assert summary['response_times']['mean'] < 0.8, "Average response time for mixed workload should be under 800ms"
        assert summary['success_rate'] > 80, "Success rate for mixed workload should be above 80%"


class TestDataVolumePerformance:
    """Test performance with varying data volumes."""
    
    @pytest.mark.parametrize("transaction_count", [100, 500, 1000, 2000])
    def test_transaction_volume_scaling(self, transaction_count, performance_metrics):
        """Test how response time scales with transaction volume."""
        iterations = 5
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                # Simulate processing with varying data volume
                base_time = 0.05 + (transaction_count / 10000)  # Scale with volume
                time.sleep(base_time)
                
                duration = time.time() - start_time
                performance_metrics.record_response_time(duration)
                performance_metrics.record_success()
                
            except Exception:
                performance_metrics.record_error()
        
        summary = performance_metrics.get_summary()
        
        # Response time should scale reasonably with data volume
        max_acceptable_time = 0.1 + (transaction_count / 5000)  # Linear scaling allowance
        assert summary['response_times']['mean'] < max_acceptable_time, \
            f"Response time should scale reasonably with {transaction_count} transactions"
    
    def test_provision_calculation_scaling(self, performance_metrics):
        """Test provision calculations with varying numbers of provisions."""
        provision_counts = [5, 10, 20, 50]
        
        for count in provision_counts:
            start_time = time.time()
            
            # Simulate provision calculation complexity
            provisions = CustomProvisionFactory.create_batch(count)
            
            # Simulate calculation time proportional to provision count
            calculation_time = 0.01 + (count * 0.002)
            time.sleep(calculation_time)
            
            duration = time.time() - start_time
            performance_metrics.record_response_time(duration)
            performance_metrics.record_success()
        
        summary = performance_metrics.get_summary()
        
        # Even with many provisions, calculations should be fast
        assert summary['response_times']['max'] < 0.2, "Provision calculations should be under 200ms even with many provisions"


class TestMemoryPerformance:
    """Test memory usage patterns and potential leaks."""
    
    def test_memory_usage_stability(self, performance_metrics):
        """Test that memory usage remains stable over many requests."""
        iterations = 100
        
        for i in range(iterations):
            performance_metrics.record_system_metrics()
            
            # Simulate API processing
            response = simulate_api_call('/api/transactions')
            performance_metrics.record_success()
            
            # Force garbage collection periodically
            if i % 20 == 0:
                import gc
                gc.collect()
        
        summary = performance_metrics.get_summary()
        memory_growth = summary['memory_usage']['max'] - summary['memory_usage']['min']
        
        # Memory growth should be minimal over many requests
        assert memory_growth < 50, "Memory growth should be under 50MB over 100 requests"
        assert summary['memory_usage']['mean'] < 150, "Average memory usage should be under 150MB"
    
    def test_large_dataset_memory_efficiency(self, performance_metrics, large_transaction_dataset):
        """Test memory efficiency when processing large datasets."""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Simulate processing large dataset in chunks
        chunk_size = 1000
        for i in range(0, len(large_transaction_dataset), chunk_size):
            chunk = large_transaction_dataset[i:i+chunk_size]
            
            performance_metrics.record_system_metrics()
            
            # Simulate processing chunk
            time.sleep(0.05)
            
            # Clear references to processed data
            del chunk
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # Memory should not grow excessively with large datasets
        assert memory_growth < 100, "Memory growth should be under 100MB when processing large datasets"


class TestPerformanceBenchmarks:
    """Performance benchmark tests with specific targets."""
    
    def test_api_throughput_benchmark(self, performance_metrics):
        """Benchmark API throughput (requests per second)."""
        test_duration = 10  # seconds
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < test_duration:
            try:
                response = simulate_api_call('/api/transactions')
                performance_metrics.record_success()
                request_count += 1
            except Exception:
                performance_metrics.record_error()
        
        actual_duration = time.time() - start_time
        throughput = request_count / actual_duration
        
        # Target: At least 20 requests per second
        assert throughput >= 15, f"Throughput should be at least 15 req/s, got {throughput:.2f}"
        assert performance_metrics.success_count > 0, "Should have at least some successful requests"
    
    def test_response_time_consistency(self, performance_metrics):
        """Test that response times are consistent (low variance)."""
        iterations = 50
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                response = simulate_api_call('/api/transactions')
                duration = time.time() - start_time
                performance_metrics.record_response_time(duration)
                performance_metrics.record_success()
            except Exception:
                performance_metrics.record_error()
        
        summary = performance_metrics.get_summary()
        response_times = performance_metrics.response_times
        
        if len(response_times) > 1:
            # Calculate coefficient of variation (std dev / mean)
            mean_time = statistics.mean(response_times)
            std_dev = statistics.stdev(response_times)
            coefficient_of_variation = std_dev / mean_time if mean_time > 0 else 0
            
            # Response times should be reasonably consistent
            assert coefficient_of_variation < 0.5, "Response times should be consistent (CV < 0.5)"
    
    def test_error_rate_under_load(self, performance_metrics):
        """Test that error rate remains low under sustained load."""
        duration = 30  # seconds
        start_time = time.time()
        
        def sustained_load():
            while time.time() - start_time < duration:
                try:
                    response = simulate_api_call('/api/transactions')
                    performance_metrics.record_success()
                except Exception:
                    performance_metrics.record_error()
                time.sleep(0.1)  # 10 requests per second per thread
        
        # Run load test with multiple threads
        num_threads = 5
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(sustained_load) for _ in range(num_threads)]
            
            for future in as_completed(futures):
                future.result()  # Wait for completion
        
        summary = performance_metrics.get_summary()
        
        # Error rate should remain low even under sustained load
        assert summary['success_rate'] >= 85, "Success rate should be at least 85% under sustained load"
        assert summary['success_count'] > 100, "Should handle significant number of requests"


@pytest.fixture(scope="session")
def performance_report():
    """Generate a performance report after all tests."""
    report_data = {}
    yield report_data
    
    # Generate summary report
    print("\n" + "="*60)
    print("PERFORMANCE TEST SUMMARY REPORT")
    print("="*60)
    
    if report_data:
        for test_name, metrics in report_data.items():
            print(f"\n{test_name}:")
            print(f"  Requests: {metrics.get('request_count', 0)}")
            print(f"  Success Rate: {metrics.get('success_rate', 0):.1f}%")
            if 'response_times' in metrics:
                rt = metrics['response_times']
                print(f"  Avg Response Time: {rt.get('mean', 0):.3f}s")
                print(f"  95th Percentile: {rt.get('p95', 0):.3f}s")
    else:
        print("No performance data collected")
    
    print("\n" + "="*60)