#!/usr/bin/env python3
"""
Test suite for batch classification endpoints
Tests all 4 new endpoints with real data and performance validation
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

# API Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/expense-classification"

# Test credentials (using demo user)
TEST_CREDENTIALS = {
    "username": "demo",
    "password": "demo"
}

def get_auth_token() -> str:
    """Get authentication token for API testing"""
    try:
        response = requests.post(f"{BASE_URL}/auth/token", data=TEST_CREDENTIALS)
        response.raise_for_status()
        token_data = response.json()
        return token_data.get("access_token", "")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return ""

def make_authenticated_request(method: str, endpoint: str, token: str, **kwargs) -> requests.Response:
    """Make authenticated request to API"""
    headers = kwargs.get('headers', {})
    headers['Authorization'] = f"Bearer {token}"
    kwargs['headers'] = headers
    
    url = f"{API_BASE}{endpoint}"
    return getattr(requests, method.lower())(url, **kwargs)

def test_classification_system_health(token: str) -> bool:
    """Test system health endpoint"""
    print("\n🏥 Testing system health...")
    
    try:
        response = make_authenticated_request('get', '/system/health', token)
        response.raise_for_status()
        
        health_data = response.json()
        print(f"✅ System health: {health_data.get('status', 'unknown')}")
        print(f"   DB response time: {health_data.get('database_response_time_ms', 0)}ms")
        print(f"   Recent classifications: {health_data.get('recent_classifications', 0)}")
        print(f"   Avg confidence: {health_data.get('avg_classification_confidence', 0)}")
        
        return health_data.get('status') == 'healthy'
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_classification_summary(token: str) -> bool:
    """Test GET /transactions/{month}/classification-summary"""
    print("\n📊 Testing classification summary...")
    
    try:
        # Test with current month data
        target_month = "2025-07"
        
        start_time = time.time()
        response = make_authenticated_request('get', f'/transactions/{target_month}/classification-summary', token)
        response.raise_for_status()
        response_time = (time.time() - start_time) * 1000
        
        summary_data = response.json()
        
        print(f"✅ Classification summary for {target_month}:")
        print(f"   Total transactions: {summary_data.get('total_transactions', 0)}")
        print(f"   Classified: {summary_data.get('classified_transactions', 0)}")
        print(f"   FIXED: {summary_data.get('fixed_count', 0)}")
        print(f"   VARIABLE: {summary_data.get('variable_count', 0)}")
        print(f"   Avg confidence: {summary_data.get('avg_confidence_score', 0)}")
        print(f"   High confidence: {summary_data.get('high_confidence_count', 0)}")
        print(f"   Response time: {response_time:.2f}ms")
        
        # Performance validation
        performance_ok = response_time < 100  # <100ms target
        if not performance_ok:
            print(f"⚠️  Performance warning: {response_time:.2f}ms > 100ms target")
        
        return response.status_code == 200 and summary_data.get('total_transactions', 0) > 0
        
    except Exception as e:
        print(f"❌ Classification summary test failed: {e}")
        return False

def test_batch_classify(token: str) -> bool:
    """Test POST /transactions/batch-classify"""
    print("\n🔄 Testing batch classification...")
    
    try:
        # Test batch classification for July 2025
        request_data = {
            "month": "2025-07",
            "force_reclassify": False,
            "auto_apply_threshold": 0.8,
            "max_transactions": 100
        }
        
        start_time = time.time()
        response = make_authenticated_request(
            'post', 
            '/transactions/batch-classify', 
            token, 
            json=request_data
        )
        response.raise_for_status()
        processing_time = (time.time() - start_time) * 1000
        
        batch_data = response.json()
        
        print(f"✅ Batch classification results:")
        print(f"   Processed: {batch_data.get('processed', 0)}")
        print(f"   Auto-applied: {batch_data.get('auto_applied', 0)}")
        print(f"   Pending review: {batch_data.get('pending_review', 0)}")
        print(f"   Skipped: {batch_data.get('skipped', 0)}")
        print(f"   Processing time: {batch_data.get('processing_time_ms', 0)}ms")
        
        # Performance validation
        performance_metrics = batch_data.get('performance_metrics', {})
        transactions_per_second = performance_metrics.get('transactions_per_second', 0)
        avg_confidence = performance_metrics.get('avg_confidence', 0)
        
        print(f"   Performance: {transactions_per_second} tx/s")
        print(f"   Avg confidence: {avg_confidence:.3f}")
        
        # Validate performance target: <2 seconds for large batches
        performance_ok = batch_data.get('processing_time_ms', 0) < 2000
        if not performance_ok:
            print(f"⚠️  Performance warning: {batch_data.get('processing_time_ms', 0)}ms > 2000ms target")
        
        return response.status_code == 200 and batch_data.get('processed', 0) > 0
        
    except Exception as e:
        print(f"❌ Batch classification test failed: {e}")
        return False

def test_auto_classify_on_load(token: str) -> bool:
    """Test POST /transactions/auto-classify-on-load"""
    print("\n🚀 Testing auto-classify on load...")
    
    try:
        # Test immediate processing for small batches
        request_data = {
            "month": "2025-07",
            "background_processing": False,
            "priority_threshold": 0.7
        }
        
        start_time = time.time()
        response = make_authenticated_request(
            'post', 
            '/transactions/auto-classify-on-load', 
            token, 
            json=request_data
        )
        response.raise_for_status()
        response_time = (time.time() - start_time) * 1000
        
        auto_classify_data = response.json()
        
        print(f"✅ Auto-classify on load results:")
        print(f"   Job ID: {auto_classify_data.get('job_id', 'N/A')}")
        print(f"   Status: {auto_classify_data.get('status', 'unknown')}")
        print(f"   Transactions queued: {auto_classify_data.get('transactions_queued', 0)}")
        print(f"   Background processing: {auto_classify_data.get('background_processing', False)}")
        print(f"   Response time: {response_time:.2f}ms")
        
        # Test background processing mode
        request_data['background_processing'] = True
        
        response2 = make_authenticated_request(
            'post', 
            '/transactions/auto-classify-on-load', 
            token, 
            json=request_data
        )
        response2.raise_for_status()
        bg_data = response2.json()
        
        print(f"   Background job ID: {bg_data.get('job_id', 'N/A')}")
        print(f"   Estimated completion: {bg_data.get('estimated_completion_ms', 0)}ms")
        
        return response.status_code == 200 and response2.status_code == 200
        
    except Exception as e:
        print(f"❌ Auto-classify on load test failed: {e}")
        return False

def test_confidence_score_update(token: str) -> bool:
    """Test PATCH /transactions/{id}/confidence-score"""
    print("\n🎯 Testing confidence score update...")
    
    try:
        # First, get a transaction ID from recent data
        # We'll use the transactions endpoint to find one
        transactions_response = make_authenticated_request(
            'get', 
            '/../transactions?month=2025-07&limit=1', 
            token
        )
        
        if transactions_response.status_code != 200:
            print("❌ Could not fetch transactions for confidence test")
            return False
            
        transactions = transactions_response.json()
        if not transactions or len(transactions) == 0:
            print("❌ No transactions available for confidence test")
            return False
        
        transaction_id = transactions[0]['id']
        
        # Test confidence score update
        update_data = {
            "confidence_score": 0.95,
            "classification_source": "USER_OVERRIDE",
            "notes": "Manual validation - high confidence classification"
        }
        
        start_time = time.time()
        response = make_authenticated_request(
            'patch', 
            f'/transactions/{transaction_id}/confidence-score', 
            token, 
            json=update_data
        )
        response.raise_for_status()
        response_time = (time.time() - start_time) * 1000
        
        confidence_data = response.json()
        
        print(f"✅ Confidence score update results:")
        print(f"   Transaction ID: {confidence_data.get('transaction_id', 'N/A')}")
        print(f"   Previous confidence: {confidence_data.get('previous_confidence', 0)}")
        print(f"   New confidence: {confidence_data.get('new_confidence', 0)}")
        print(f"   Previous source: {confidence_data.get('previous_source', 'unknown')}")
        print(f"   New source: {confidence_data.get('new_source', 'unknown')}")
        print(f"   Response time: {response_time:.2f}ms")
        
        # Performance validation
        performance_ok = response_time < 50  # <50ms target
        if not performance_ok:
            print(f"⚠️  Performance warning: {response_time:.2f}ms > 50ms target")
        
        return response.status_code == 200 and confidence_data.get('success', False)
        
    except Exception as e:
        print(f"❌ Confidence score update test failed: {e}")
        return False

def run_performance_benchmark(token: str) -> Dict[str, Any]:
    """Run comprehensive performance benchmark"""
    print("\n⚡ Running performance benchmark...")
    
    benchmark_results = {
        "timestamp": datetime.now().isoformat(),
        "endpoints_tested": 0,
        "endpoints_passed": 0,
        "total_response_time": 0.0,
        "classification_accuracy": 0.0,
        "throughput_transactions_per_second": 0.0
    }
    
    try:
        # Test batch classification performance with different sizes
        batch_sizes = [10, 50, 100]
        
        for batch_size in batch_sizes:
            print(f"   Testing batch size: {batch_size}")
            
            request_data = {
                "month": "2025-07",
                "force_reclassify": True,  # Force reclassify for consistent testing
                "auto_apply_threshold": 0.7,
                "max_transactions": batch_size
            }
            
            start_time = time.time()
            response = make_authenticated_request(
                'post', 
                '/transactions/batch-classify', 
                token, 
                json=request_data
            )
            
            if response.status_code == 200:
                batch_data = response.json()
                processing_time = batch_data.get('processing_time_ms', 0)
                processed_count = batch_data.get('processed', 0)
                
                if processed_count > 0:
                    throughput = (processed_count / (processing_time / 1000)) if processing_time > 0 else 0
                    print(f"     Processed: {processed_count}, Time: {processing_time}ms, Throughput: {throughput:.2f} tx/s")
                    
                    benchmark_results["throughput_transactions_per_second"] = max(
                        benchmark_results["throughput_transactions_per_second"],
                        throughput
                    )
        
        benchmark_results["endpoints_tested"] = 4
        benchmark_results["endpoints_passed"] = 4  # Will be adjusted based on test results
        
        print(f"✅ Performance benchmark completed")
        print(f"   Max throughput: {benchmark_results['throughput_transactions_per_second']:.2f} tx/s")
        
        return benchmark_results
        
    except Exception as e:
        print(f"❌ Performance benchmark failed: {e}")
        return benchmark_results

def main():
    """Run all batch classification endpoint tests"""
    print("🧪 Starting Batch Classification API Tests")
    print("=" * 50)
    
    # Get authentication token
    print("🔐 Authenticating...")
    token = get_auth_token()
    
    if not token:
        print("❌ Authentication failed - cannot proceed with tests")
        return False
    
    print(f"✅ Authentication successful")
    
    # Run all tests
    test_results = []
    
    # 1. System Health
    test_results.append(("System Health", test_classification_system_health(token)))
    
    # 2. Classification Summary
    test_results.append(("Classification Summary", test_classification_summary(token)))
    
    # 3. Batch Classify
    test_results.append(("Batch Classify", test_batch_classify(token)))
    
    # 4. Auto-classify on Load
    test_results.append(("Auto-classify on Load", test_auto_classify_on_load(token)))
    
    # 5. Confidence Score Update
    test_results.append(("Confidence Score Update", test_confidence_score_update(token)))
    
    # 6. Performance Benchmark
    benchmark_results = run_performance_benchmark(token)
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed_tests += 1
    
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"\n🎯 Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    print(f"⚡ Max Throughput: {benchmark_results['throughput_transactions_per_second']:.2f} transactions/second")
    
    # Performance validation
    if benchmark_results['throughput_transactions_per_second'] >= 100:
        print("✅ Performance target achieved (>100 tx/s)")
    else:
        print("⚠️  Performance target not met (<100 tx/s)")
    
    # Final assessment
    overall_success = passed_tests == total_tests and benchmark_results['throughput_transactions_per_second'] > 0
    
    if overall_success:
        print("\n🎉 ALL TESTS PASSED - Batch Classification API is ready for production!")
    else:
        print(f"\n⚠️  Some tests failed - Review issues before deployment")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)