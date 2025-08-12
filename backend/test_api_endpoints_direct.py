#!/usr/bin/env python3
"""
Direct API endpoint testing without authentication
Tests the AI classification endpoints directly to validate functionality
"""

import requests
import json
import time
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

def test_classification_endpoints():
    """Test classification endpoints that don't require authentication"""
    
    print("🚀 TESTING AI CLASSIFICATION ENDPOINTS (NO AUTH)")
    print("=" * 60)
    
    session = requests.Session()
    
    # Test cases with response time tracking
    test_cases = []
    
    # Test 1: Classification stats (if it exists without auth)
    try:
        start_time = time.time()
        response = session.get(f"{BASE_URL}/expense-classification/stats")
        response_time = (time.time() - start_time) * 1000
        
        test_cases.append({
            'name': 'Classification Stats',
            'endpoint': '/expense-classification/stats',
            'status_code': response.status_code,
            'response_time_ms': round(response_time, 1),
            'success': response.status_code == 200,
            'data': response.json() if response.status_code == 200 else None,
            'error': response.text if response.status_code != 200 else None
        })
        
    except Exception as e:
        test_cases.append({
            'name': 'Classification Stats',
            'endpoint': '/expense-classification/stats',
            'success': False,
            'error': str(e)
        })
    
    # Test 2: Test single tag classification via GET endpoint (if available)
    try:
        start_time = time.time()
        response = session.get(f"{BASE_URL}/expense-classification/suggest/netflix?amount=-15.99")
        response_time = (time.time() - start_time) * 1000
        
        test_cases.append({
            'name': 'Single Tag GET Classification',
            'endpoint': '/expense-classification/suggest/netflix',
            'status_code': response.status_code,
            'response_time_ms': round(response_time, 1),
            'success': response.status_code == 200,
            'data': response.json() if response.status_code == 200 else None,
            'error': response.text if response.status_code != 200 else None
        })
        
    except Exception as e:
        test_cases.append({
            'name': 'Single Tag GET Classification',
            'endpoint': '/expense-classification/suggest/netflix',
            'success': False,
            'error': str(e)
        })
    
    # Test 3: Check available endpoints via docs
    try:
        start_time = time.time()
        response = session.get(f"{BASE_URL}/openapi.json")
        response_time = (time.time() - start_time) * 1000
        
        success = response.status_code == 200
        openapi_data = response.json() if success else None
        
        test_cases.append({
            'name': 'OpenAPI Schema',
            'endpoint': '/openapi.json',
            'status_code': response.status_code,
            'response_time_ms': round(response_time, 1),
            'success': success,
            'data': {'paths_count': len(openapi_data.get('paths', {}))} if openapi_data else None,
            'error': response.text if response.status_code != 200 else None
        })
        
        # List available classification endpoints
        if success and openapi_data:
            classification_paths = [path for path in openapi_data.get('paths', {}).keys() 
                                  if 'classification' in path.lower()]
            print(f"\n📋 Available Classification Endpoints ({len(classification_paths)}):")
            for path in classification_paths:
                methods = list(openapi_data['paths'][path].keys())
                print(f"   {path} [{', '.join(methods).upper()}]")
        
    except Exception as e:
        test_cases.append({
            'name': 'OpenAPI Schema',
            'endpoint': '/openapi.json',
            'success': False,
            'error': str(e)
        })
    
    # Test 4: Direct database query test (check if we can access classification service)
    try:
        print(f"\n🗄️ TESTING DATABASE ACCESS")
        
        # Test database connection
        import sqlite3
        conn = sqlite3.connect('budget.db')
        cursor = conn.cursor()
        
        # Count transactions with classifications
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE expense_type IS NOT NULL")
        classified_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE expense_type IS NULL")
        unclassified_count = cursor.fetchone()[0]
        
        # Sample some classified transactions
        cursor.execute("""
            SELECT id, label, tags, expense_type, amount 
            FROM transactions 
            WHERE tags IS NOT NULL AND tags != '' 
            LIMIT 5
        """)
        sample_transactions = cursor.fetchall()
        
        conn.close()
        
        print(f"✅ Database Connection: SUCCESS")
        print(f"   Classified transactions: {classified_count}")
        print(f"   Unclassified transactions: {unclassified_count}")
        print(f"   Sample transactions with tags: {len(sample_transactions)}")
        
        for tx in sample_transactions:
            print(f"     ID {tx[0]}: {tx[1][:30]:<30} | Tags: {tx[2]:<15} | Type: {tx[3]:<8}")
            
        test_cases.append({
            'name': 'Database Access',
            'endpoint': 'direct_database',
            'success': True,
            'data': {
                'classified_count': classified_count,
                'unclassified_count': unclassified_count,
                'sample_transactions': len(sample_transactions)
            }
        })
        
    except Exception as e:
        print(f"❌ Database Connection: FAILED - {e}")
        test_cases.append({
            'name': 'Database Access',
            'endpoint': 'direct_database',
            'success': False,
            'error': str(e)
        })
    
    # Test 5: Test classification service directly (Python import)
    try:
        print(f"\n🧠 TESTING CLASSIFICATION SERVICE IMPORT")
        
        # Import the classification service
        from services.expense_classification import get_expense_classification_service
        from models.database import get_db
        
        # Get a database session
        db_session = next(get_db())
        
        # Get the classification service
        classification_service = get_expense_classification_service(db_session)
        
        # Test basic classification functionality
        test_tags = ["netflix", "courses", "loyer", "restaurant"]
        results = {}
        
        for tag in test_tags:
            start_time = time.time()
            result = classification_service.classify_expense(
                tag_name=tag,
                transaction_amount=-20.0,
                transaction_description=f"Test {tag}",
                transaction_history=[]
            )
            response_time = (time.time() - start_time) * 1000
            
            results[tag] = {
                'expense_type': result.expense_type,
                'confidence': result.confidence,
                'response_time_ms': round(response_time, 1)
            }
        
        db_session.close()
        
        print(f"✅ Classification Service: SUCCESS")
        for tag, result in results.items():
            print(f"   {tag:<12}: {result['expense_type']:<8} (confidence: {result['confidence']:.2f}, {result['response_time_ms']}ms)")
        
        # Calculate performance metrics
        avg_confidence = sum(r['confidence'] for r in results.values()) / len(results)
        avg_response_time = sum(r['response_time_ms'] for r in results.values()) / len(results)
        
        test_cases.append({
            'name': 'Direct Classification Service',
            'endpoint': 'python_import',
            'success': True,
            'data': {
                'test_results': results,
                'avg_confidence': round(avg_confidence, 2),
                'avg_response_time_ms': round(avg_response_time, 1)
            }
        })
        
    except Exception as e:
        print(f"❌ Classification Service Import: FAILED - {e}")
        test_cases.append({
            'name': 'Direct Classification Service',
            'endpoint': 'python_import',
            'success': False,
            'error': str(e)
        })
    
    # Print summary report
    print(f"\n" + "=" * 60)
    print(f"📊 TEST SUMMARY REPORT")
    print(f"=" * 60)
    
    total_tests = len(test_cases)
    successful_tests = len([t for t in test_cases if t['success']])
    failed_tests = total_tests - successful_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Successful: {successful_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success Rate: {successful_tests/total_tests:.1%}")
    
    print(f"\n📋 DETAILED RESULTS:")
    for test in test_cases:
        status = "✅ PASS" if test['success'] else "❌ FAIL"
        response_time = f" ({test.get('response_time_ms', 0)}ms)" if test.get('response_time_ms') else ""
        print(f"   {status} {test['name']}{response_time}")
        
        if not test['success'] and test.get('error'):
            print(f"      Error: {test['error'][:100]}...")
        elif test['success'] and test.get('data'):
            # Show key metrics for successful tests
            data = test['data']
            if isinstance(data, dict):
                if 'avg_confidence' in data:
                    print(f"      Avg Confidence: {data['avg_confidence']}")
                if 'classified_count' in data:
                    print(f"      Classified: {data['classified_count']}, Unclassified: {data['unclassified_count']}")
                if 'paths_count' in data:
                    print(f"      API Endpoints: {data['paths_count']}")
    
    # Assessment and recommendations
    print(f"\n🎯 QUALITY ASSESSMENT:")
    
    if successful_tests >= total_tests * 0.8:
        if successful_tests == total_tests:
            print("   Grade: A+ EXCELLENT - All tests passing")
            print("   Status: ✅ READY FOR PRODUCTION")
        else:
            print("   Grade: A GOOD - Most functionality working")
            print("   Status: ✅ READY FOR PRODUCTION (minor issues)")
    elif successful_tests >= total_tests * 0.6:
        print("   Grade: B ACCEPTABLE - Core functionality working")
        print("   Status: ⚠️ NEEDS IMPROVEMENTS")
    else:
        print("   Grade: C POOR - Significant issues detected")
        print("   Status: ❌ NOT READY FOR PRODUCTION")
    
    print(f"\n🔍 RECOMMENDATIONS:")
    
    if failed_tests == 0:
        print("   • All systems operational")
        print("   • Consider load testing for production readiness")
        print("   • Monitor performance metrics in production")
    else:
        if any('auth' in str(t.get('error', '')).lower() for t in test_cases if not t['success']):
            print("   • Fix authentication issues for full API access")
        if any('database' in str(t.get('error', '')).lower() for t in test_cases if not t['success']):
            print("   • Resolve database connectivity issues")
        print("   • Address failed test cases before production deployment")
    
    # Save results to file
    with open('api_validation_report.json', 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'success_rate': successful_tests/total_tests
            },
            'test_results': test_cases
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: api_validation_report.json")
    
    return successful_tests == total_tests

if __name__ == "__main__":
    success = test_classification_endpoints()
    exit(0 if success else 1)