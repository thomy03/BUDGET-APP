#!/usr/bin/env python3
"""
E2E Validation Test Suite for Budget App v2.3
Tests critiques pour valider le fonctionnement Dashboard/Settings
"""
import requests
import json
import time
from datetime import datetime
import sys

BASE_URL = "http://localhost:8000"
FRONTEND_ORIGIN = "http://localhost:45678"

class APITester:
    def __init__(self):
        self.token = None
        self.test_results = []
        self.start_time = time.time()
        
    def log_test(self, test_name, success, message, duration=None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL" 
        duration_str = f" ({duration:.3f}s)" if duration else ""
        print(f"{status}: {test_name} - {message}{duration_str}")
        
    def authenticate(self):
        """Get authentication token"""
        test_start = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/token",
                data={"username": "admin", "password": "secret"},
                timeout=10
            )
            duration = time.time() - test_start
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.log_test("Authentication", True, "Token obtained successfully", duration)
                return True
            else:
                self.log_test("Authentication", False, f"Failed with status {response.status_code}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_test("Authentication", False, f"Exception: {str(e)}", duration)
            return False
    
    def get_headers(self):
        """Get headers with authentication"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Origin": FRONTEND_ORIGIN,
            "Content-Type": "application/json"
        }
        return headers
    
    def test_cors_preflight(self, endpoint):
        """Test CORS preflight for an endpoint"""
        test_start = time.time()
        try:
            response = requests.options(
                f"{BASE_URL}{endpoint}",
                headers={"Origin": FRONTEND_ORIGIN},
                timeout=10
            )
            duration = time.time() - test_start
            
            if response.status_code == 200:
                cors_headers = response.headers.get("Access-Control-Allow-Origin", "")
                if cors_headers:
                    self.log_test(f"CORS Preflight {endpoint}", True, 
                                f"CORS enabled: {cors_headers}", duration)
                    return True
                else:
                    self.log_test(f"CORS Preflight {endpoint}", False, 
                                "CORS headers missing", duration)
                    return False
            else:
                # 405 Method Not Allowed is OK for endpoints that don't support OPTIONS
                if response.status_code == 405:
                    self.log_test(f"CORS Preflight {endpoint}", True, 
                                "No OPTIONS support (acceptable)", duration)
                    return True
                else:
                    self.log_test(f"CORS Preflight {endpoint}", False, 
                                f"Status {response.status_code}", duration)
                    return False
                    
        except Exception as e:
            duration = time.time() - test_start
            self.log_test(f"CORS Preflight {endpoint}", False, f"Exception: {str(e)}", duration)
            return False
    
    def test_fixed_lines_endpoint(self):
        """Test fixed-lines endpoint"""
        test_start = time.time()
        try:
            response = requests.get(
                f"{BASE_URL}/fixed-lines",
                headers=self.get_headers(),
                timeout=10
            )
            duration = time.time() - test_start
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Fixed Lines API", True, 
                            f"Retrieved {len(data)} fixed lines", duration)
                return True
            else:
                self.log_test("Fixed Lines API", False, 
                            f"Status {response.status_code}: {response.text}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_test("Fixed Lines API", False, f"Exception: {str(e)}", duration)
            return False
    
    def test_tags_endpoint(self):
        """Test tags-related endpoints"""
        test_start = time.time()
        try:
            # Test GET /tags (assuming this exists)
            response = requests.get(
                f"{BASE_URL}/tags",
                headers=self.get_headers(),
                timeout=10
            )
            duration = time.time() - test_start
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Tags API", True, f"Retrieved tags data", duration)
                return True
            elif response.status_code == 404:
                self.log_test("Tags API", False, "Endpoint not found", duration)
                return False
            else:
                self.log_test("Tags API", False, 
                            f"Status {response.status_code}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_test("Tags API", False, f"Exception: {str(e)}", duration)
            return False
    
    def test_classification_endpoint(self):
        """Test expense classification endpoint"""
        test_start = time.time()
        try:
            response = requests.get(
                f"{BASE_URL}/expense-classification/rules",
                headers=self.get_headers(),
                timeout=10
            )
            duration = time.time() - test_start
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Classification API", True, 
                            f"Retrieved classification rules", duration)
                return True
            elif response.status_code == 404:
                self.log_test("Classification API", False, "Endpoint not found", duration)
                return False
            else:
                self.log_test("Classification API", False, 
                            f"Status {response.status_code}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_test("Classification API", False, f"Exception: {str(e)}", duration)
            return False
    
    def test_dashboard_endpoints(self):
        """Test dashboard-related endpoints"""
        test_start = time.time()
        try:
            # Test summary endpoint
            response = requests.get(
                f"{BASE_URL}/summary?month=2025-08",
                headers=self.get_headers(),
                timeout=10
            )
            duration = time.time() - test_start
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Dashboard Summary API", True, 
                            f"Summary data retrieved", duration)
                return True
            else:
                self.log_test("Dashboard Summary API", False, 
                            f"Status {response.status_code}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_test("Dashboard Summary API", False, f"Exception: {str(e)}", duration)
            return False
    
    def test_config_endpoint(self):
        """Test configuration endpoint"""
        test_start = time.time()
        try:
            response = requests.get(
                f"{BASE_URL}/config",
                headers=self.get_headers(),
                timeout=10
            )
            duration = time.time() - test_start
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Config API", True, f"Config retrieved", duration)
                return True
            else:
                self.log_test("Config API", False, 
                            f"Status {response.status_code}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_test("Config API", False, f"Exception: {str(e)}", duration)
            return False
    
    def test_performance(self):
        """Test performance benchmarks"""
        endpoints_to_test = [
            "/config",
            "/summary?month=2025-08",
            "/custom-provisions",
            "/fixed-lines"
        ]
        
        performance_results = []
        
        for endpoint in endpoints_to_test:
            test_start = time.time()
            try:
                response = requests.get(
                    f"{BASE_URL}{endpoint}",
                    headers=self.get_headers(),
                    timeout=10
                )
                duration = time.time() - test_start
                
                if response.status_code == 200:
                    performance_results.append(duration)
                    if duration < 3.0:
                        self.log_test(f"Performance {endpoint}", True, 
                                    f"Response time: {duration:.3f}s", duration)
                    else:
                        self.log_test(f"Performance {endpoint}", False, 
                                    f"Too slow: {duration:.3f}s", duration)
                else:
                    self.log_test(f"Performance {endpoint}", False, 
                                f"Failed with status {response.status_code}")
                        
            except Exception as e:
                duration = time.time() - test_start
                self.log_test(f"Performance {endpoint}", False, 
                            f"Exception: {str(e)}", duration)
        
        if performance_results:
            avg_time = sum(performance_results) / len(performance_results)
            self.log_test("Overall Performance", avg_time < 2.0, 
                        f"Average response time: {avg_time:.3f}s")
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting E2E Validation Test Suite for Budget App v2.3")
        print("=" * 60)
        
        # Authentication is required for all tests
        if not self.authenticate():
            print("❌ Authentication failed - aborting tests")
            return False
        
        # Core API endpoints
        self.test_fixed_lines_endpoint()
        self.test_config_endpoint()
        self.test_dashboard_endpoints()
        
        # Settings-related endpoints
        self.test_tags_endpoint()
        self.test_classification_endpoint()
        
        # CORS validation
        self.test_cors_preflight("/fixed-lines")
        self.test_cors_preflight("/config")
        self.test_cors_preflight("/summary")
        
        # Performance tests
        self.test_performance()
        
        return True
    
    def generate_report(self):
        """Generate final test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        total_duration = time.time() - self.start_time
        
        print("\n" + "=" * 60)
        print("📊 E2E VALIDATION REPORT")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏱️  Total Duration: {total_duration:.3f}s")
        print(f"📈 Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\n🚨 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['message']}")
        
        # Critical issues that block release
        critical_failures = [
            result for result in self.test_results 
            if not result["success"] and 
            any(critical in result["test"] for critical in ["Authentication", "Fixed Lines", "Dashboard"])
        ]
        
        if critical_failures:
            print("\n🔴 CRITICAL FAILURES (RELEASE BLOCKING):")
            for failure in critical_failures:
                print(f"   - {failure['test']}: {failure['message']}")
            return False
        
        if failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION")
        else:
            print(f"\n⚠️  {failed_tests} NON-CRITICAL TESTS FAILED")
        
        # Save detailed report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": passed_tests/total_tests*100,
                "duration": total_duration
            },
            "tests": self.test_results
        }
        
        with open("e2e_validation_report.json", "w") as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📝 Detailed report saved to: e2e_validation_report.json")
        return True

if __name__ == "__main__":
    tester = APITester()
    success = tester.run_all_tests()
    final_success = tester.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if final_success else 1)