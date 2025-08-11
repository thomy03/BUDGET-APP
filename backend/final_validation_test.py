#!/usr/bin/env python3
"""
Final Validation Test for Budget Famille v2.3
==============================================

This test validates all the fixes and provides a final release assessment.
"""

import requests
import json
import time
import csv
import tempfile
import os
from datetime import datetime

def test_core_functionality():
    """Test all core functionality after fixes"""
    base_url = "http://localhost:8000"
    session = requests.Session()
    
    print("=" * 80)
    print("BUDGET FAMILLE v2.3 - FINAL VALIDATION TEST")
    print("=" * 80)
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {base_url}")
    print()
    
    test_results = {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "issues": []
    }
    
    def log_test(name, success, details=""):
        test_results["total_tests"] += 1
        if success:
            test_results["passed"] += 1
            print(f"✅ {name}")
            if details:
                print(f"   📋 {details}")
        else:
            test_results["failed"] += 1
            test_results["issues"].append(f"{name}: {details}")
            print(f"❌ {name}")
            if details:
                print(f"   🚨 {details}")
        print()
    
    # 1. System Health
    try:
        response = session.get(f"{base_url}/health")
        if response.status_code == 200:
            health = response.json()
            log_test("System Health Check", True, 
                    f"Version: {health.get('version', 'N/A')}, Status: {health.get('status', 'N/A')}")
        else:
            log_test("System Health Check", False, f"HTTP {response.status_code}")
    except Exception as e:
        log_test("System Health Check", False, str(e))
    
    # 2. Authentication
    auth_token = None
    try:
        auth_data = {"username": "admin", "password": "secret"}
        response = session.post(f"{base_url}/token", 
                               data=auth_data,
                               headers={"Content-Type": "application/x-www-form-urlencoded"})
        
        if response.status_code == 200:
            token_data = response.json()
            if "access_token" in token_data:
                auth_token = token_data["access_token"]
                session.headers.update({"Authorization": f"Bearer {auth_token}"})
                log_test("Authentication", True, "Token obtained and session configured")
            else:
                log_test("Authentication", False, "Token missing in response")
        else:
            log_test("Authentication", False, f"HTTP {response.status_code}")
    except Exception as e:
        log_test("Authentication", False, str(e))
    
    if not auth_token:
        print("🚨 CRITICAL: Cannot continue without authentication")
        return test_results
    
    # 3. Configuration Management (fixed bug)
    try:
        # Get config
        response = session.get(f"{base_url}/config")
        if response.status_code == 200:
            config = response.json()
            
            # Update config (this was the bug)
            updated_config = config.copy()
            updated_config["member1"] = "TestUser1"
            updated_config["member2"] = "TestUser2"
            
            update_response = session.post(f"{base_url}/config", json=updated_config)
            if update_response.status_code == 200:
                log_test("Configuration Management", True, "Config update working properly")
            else:
                log_test("Configuration Management", False, f"Update failed: {update_response.status_code}")
        else:
            log_test("Configuration Management", False, f"Get config failed: {response.status_code}")
    except Exception as e:
        log_test("Configuration Management", False, str(e))
    
    # 4. CSV Import
    try:
        # Create test CSV
        test_data = [
            {
                "dateOp": "2024-08-01",
                "dateVal": "2024-08-01",
                "label": "TEST TRANSACTION",
                "category": "Test",
                "categoryParent": "Testing",
                "amount": "-25.50",
                "accountLabel": "Test Account",
                "supplierFound": "TEST",
                "comment": "Final validation test"
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=test_data[0].keys())
            writer.writeheader()
            writer.writerows(test_data)
            csv_file = f.name
        
        # Import CSV
        with open(csv_file, 'rb') as f:
            files = {"file": ("test_validation.csv", f, "text/csv")}
            response = session.post(f"{base_url}/import", files=files)
            
        os.unlink(csv_file)  # Clean up
        
        if response.status_code == 200:
            import_result = response.json()
            log_test("CSV Import", True, 
                    f"Import ID: {import_result.get('importId', 'N/A')}, "
                    f"Months: {len(import_result.get('months', []))}")
        else:
            log_test("CSV Import", False, f"HTTP {response.status_code}: {response.text[:100]}")
            
    except Exception as e:
        log_test("CSV Import", False, str(e))
    
    # 5. Transaction Operations
    try:
        # Get transactions
        response = session.get(f"{base_url}/transactions?month=2024-08")
        if response.status_code == 200:
            transactions = response.json()
            if transactions:
                tx = transactions[0]
                tx_id = tx["id"]
                
                # Test exclude toggle
                exclude_response = session.patch(f"{base_url}/transactions/{tx_id}",
                                               json={"exclude": True})
                
                # Test tags update
                tags_response = session.patch(f"{base_url}/transactions/{tx_id}/tags",
                                            json={"tags": ["test", "validation"]})
                
                if exclude_response.status_code == 200 and tags_response.status_code == 200:
                    log_test("Transaction Operations", True, f"CRUD operations on tx {tx_id}")
                else:
                    log_test("Transaction Operations", False, 
                            f"Exclude: {exclude_response.status_code}, Tags: {tags_response.status_code}")
            else:
                log_test("Transaction Operations", True, "No transactions to test (expected for new data)")
        else:
            log_test("Transaction Operations", False, f"Get transactions failed: {response.status_code}")
    except Exception as e:
        log_test("Transaction Operations", False, str(e))
    
    # 6. Analytics
    try:
        # Summary
        summary_response = session.get(f"{base_url}/summary?month=2024-08")
        
        # Tags summary  
        tags_response = session.get(f"{base_url}/tags-summary?month=2024-08")
        
        # KPIs
        kpis_response = session.get(f"{base_url}/analytics/kpis?months=last1")
        
        if (summary_response.status_code == 200 and 
            tags_response.status_code == 200 and 
            kpis_response.status_code == 200):
            log_test("Analytics", True, "All analytics endpoints working")
        else:
            log_test("Analytics", False, 
                    f"Summary: {summary_response.status_code}, "
                    f"Tags: {tags_response.status_code}, "
                    f"KPIs: {kpis_response.status_code}")
    except Exception as e:
        log_test("Analytics", False, str(e))
    
    # 7. Security - Verify fixes
    try:
        unauth_session = requests.Session()  # No auth token
        
        config_response = unauth_session.get(f"{base_url}/config")
        fixed_lines_response = unauth_session.get(f"{base_url}/fixed-lines")
        
        if config_response.status_code == 403 and fixed_lines_response.status_code == 403:
            log_test("Security Fixes", True, "Protected endpoints properly secured")
        else:
            log_test("Security Fixes", False, 
                    f"Config: {config_response.status_code}, Fixed-lines: {fixed_lines_response.status_code}")
    except Exception as e:
        log_test("Security Fixes", False, str(e))
    
    # 8. Performance Test
    try:
        response_times = []
        for i in range(3):
            start_time = time.time()
            response = session.get(f"{base_url}/config")
            end_time = time.time()
            if response.status_code == 200:
                response_times.append(end_time - start_time)
        
        if response_times:
            avg_time = sum(response_times) / len(response_times) * 1000
            if avg_time < 500:  # < 500ms
                log_test("Performance", True, f"Average response time: {avg_time:.0f}ms")
            else:
                log_test("Performance", False, f"Slow response time: {avg_time:.0f}ms")
        else:
            log_test("Performance", False, "No successful requests")
    except Exception as e:
        log_test("Performance", False, str(e))
    
    return test_results

def generate_final_report():
    """Generate the final release validation report"""
    results = test_core_functionality()
    
    pass_rate = (results["passed"] / results["total_tests"] * 100) if results["total_tests"] > 0 else 0
    
    print("=" * 80)
    print("FINAL VALIDATION RESULTS")
    print("=" * 80)
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Pass Rate: {pass_rate:.1f}%")
    print()
    
    if results["failed"] == 0:
        print("🎉 ALL TESTS PASSED!")
        print("✅ RELEASE APPROVED")
        release_status = "APPROVED"
    elif pass_rate >= 85:
        print("⚠️ CONDITIONAL RELEASE")
        print("Some tests failed but core functionality is working")
        release_status = "CONDITIONAL"
    else:
        print("🚨 RELEASE BLOCKED")
        print("Too many critical issues remain")
        release_status = "BLOCKED"
    
    if results["issues"]:
        print()
        print("REMAINING ISSUES:")
        for issue in results["issues"]:
            print(f"  • {issue}")
    
    print()
    print("=" * 80)
    print(f"FINAL RECOMMENDATION: {release_status}")
    print("=" * 80)
    
    return release_status, results

if __name__ == "__main__":
    status, results = generate_final_report()
    
    if status == "APPROVED":
        exit(0)
    elif status == "CONDITIONAL":
        exit(1)
    else:
        exit(2)