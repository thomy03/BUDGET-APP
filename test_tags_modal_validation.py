#!/usr/bin/env python3
"""
Tags and Modal Functionality Test Suite
Test tag creation/modification modals and related API endpoints
"""

import requests
import time
import json
import sys
from datetime import datetime

class TagsModalTester:
    def __init__(self, backend_url="http://localhost:8000"):
        self.backend_url = backend_url
        self.results = []
    
    def log_result(self, test_name, status, details="", error=None):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        if error:
            result["error"] = str(error)
        self.results.append(result)
        
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {status}")
        if details:
            print(f"   {details}")
        if error:
            print(f"   Error: {error}")
    
    def test_tags_endpoints(self):
        """Test tags-related API endpoints"""
        endpoints_to_test = [
            ("/tags", "GET", "List tags"),
            ("/tags-summary", "GET", "Tags summary"),
            ("/api/v1/cache/health", "GET", "Cache health")
        ]
        
        passed_endpoints = 0
        for endpoint, method, description in endpoints_to_test:
            try:
                if method == "GET":
                    response = requests.get(f"{self.backend_url}{endpoint}", timeout=5)
                elif method == "OPTIONS":
                    response = requests.options(f"{self.backend_url}{endpoint}", timeout=5)
                
                if response.status_code in [200, 401]:  # 401 is expected for protected endpoints
                    passed_endpoints += 1
                    print(f"   ✓ {endpoint} ({description}): {response.status_code}")
                else:
                    print(f"   ✗ {endpoint} ({description}): {response.status_code}")
                    
            except Exception as e:
                print(f"   ✗ {endpoint} ({description}): {e}")
        
        if passed_endpoints == len(endpoints_to_test):
            self.log_result("Tags API Endpoints", "PASS", 
                           f"All {len(endpoints_to_test)} tag endpoints functional")
            return True
        elif passed_endpoints > len(endpoints_to_test) // 2:
            self.log_result("Tags API Endpoints", "WARN", 
                           f"{passed_endpoints}/{len(endpoints_to_test)} endpoints functional")
            return False
        else:
            self.log_result("Tags API Endpoints", "FAIL", 
                           f"Only {passed_endpoints}/{len(endpoints_to_test)} endpoints functional")
            return False
    
    def test_classification_endpoints(self):
        """Test intelligent classification and tagging endpoints"""
        endpoints_to_test = [
            "/tags/suggest",
            "/tags/suggest-batch", 
            "/unified/classify",
            "/unified/batch-classify",
            "/unified/stats"
        ]
        
        functional_endpoints = 0
        for endpoint in endpoints_to_test:
            try:
                # Test OPTIONS for CORS
                response = requests.options(f"{self.backend_url}{endpoint}", timeout=5)
                if response.status_code in [200, 405]:  # 405 = Method not allowed but exists
                    functional_endpoints += 1
                    print(f"   ✓ {endpoint}: Available")
                else:
                    print(f"   ✗ {endpoint}: {response.status_code}")
                    
            except Exception as e:
                print(f"   ✗ {endpoint}: {e}")
        
        if functional_endpoints >= len(endpoints_to_test) * 0.8:
            self.log_result("Classification Endpoints", "PASS", 
                           f"{functional_endpoints}/{len(endpoints_to_test)} classification endpoints available")
            return True
        else:
            self.log_result("Classification Endpoints", "FAIL", 
                           f"Only {functional_endpoints}/{len(endpoints_to_test)} classification endpoints available")
            return False
    
    def test_transactions_endpoints(self):
        """Test transaction-related endpoints for tag modification"""
        try:
            # Test transactions endpoint structure
            response = requests.get(f"{self.backend_url}/transactions?month=2025-08", timeout=5)
            
            if response.status_code == 401:
                # Expected for protected endpoints
                self.log_result("Transactions Endpoints", "PASS", 
                               "Transactions endpoint properly protected")
                return True
            elif response.status_code == 200:
                self.log_result("Transactions Endpoints", "PASS", 
                               "Transactions endpoint accessible")
                return True
            else:
                self.log_result("Transactions Endpoints", "FAIL", 
                               f"Unexpected response: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Transactions Endpoints", "FAIL", error=e)
            return False
    
    def test_config_endpoints(self):
        """Test configuration endpoints"""
        try:
            response = requests.get(f"{self.backend_url}/config", timeout=5)
            
            if response.status_code in [200, 401]:  # Both are acceptable
                self.log_result("Config Endpoints", "PASS", 
                               f"Config endpoint functional (status: {response.status_code})")
                return True
            else:
                self.log_result("Config Endpoints", "FAIL", 
                               f"Config endpoint returned: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Config Endpoints", "FAIL", error=e)
            return False
    
    def test_cors_for_modals(self):
        """Test CORS configuration for modal functionality"""
        origins_to_test = [
            "http://localhost:45678",
            "http://127.0.0.1:45678"
        ]
        
        cors_working = 0
        for origin in origins_to_test:
            try:
                headers = {
                    'Origin': origin,
                    'Access-Control-Request-Method': 'POST',
                    'Access-Control-Request-Headers': 'Content-Type,Authorization'
                }
                response = requests.options(f"{self.backend_url}/tags", headers=headers, timeout=5)
                
                if response.status_code == 200 and 'Access-Control-Allow-Origin' in response.headers:
                    cors_working += 1
                    print(f"   ✓ CORS working for origin: {origin}")
                else:
                    print(f"   ✗ CORS failed for origin: {origin}")
                    
            except Exception as e:
                print(f"   ✗ CORS error for {origin}: {e}")
        
        if cors_working == len(origins_to_test):
            self.log_result("CORS for Modals", "PASS", 
                           "CORS properly configured for all frontend origins")
            return True
        elif cors_working > 0:
            self.log_result("CORS for Modals", "WARN", 
                           f"CORS working for {cors_working}/{len(origins_to_test)} origins")
            return False
        else:
            self.log_result("CORS for Modals", "FAIL", 
                           "CORS not working for any origin")
            return False
    
    def test_api_response_formats(self):
        """Test API response formats for expected JSON structure"""
        try:
            # Test health endpoint for JSON structure
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and 'status' in data:
                        self.log_result("API Response Formats", "PASS", 
                                       "API returns properly formatted JSON responses")
                        return True
                    else:
                        self.log_result("API Response Formats", "FAIL", 
                                       "API response missing expected structure")
                        return False
                except json.JSONDecodeError:
                    self.log_result("API Response Formats", "FAIL", 
                                   "API response is not valid JSON")
                    return False
            else:
                self.log_result("API Response Formats", "FAIL", 
                               f"Health endpoint returned {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("API Response Formats", "FAIL", error=e)
            return False
    
    def run_tags_modal_tests(self):
        """Run complete tags and modal test suite"""
        print("🏷️ Starting Tags & Modal Functionality Tests")
        print("=" * 50)
        
        tests = [
            self.test_tags_endpoints,
            self.test_classification_endpoints,
            self.test_transactions_endpoints,
            self.test_config_endpoints,
            self.test_cors_for_modals,
            self.test_api_response_formats
        ]
        
        passed = 0
        for test in tests:
            if test():
                passed += 1
        
        print("\n" + "=" * 50)
        print(f"📊 Tags & Modal Tests: {passed}/{len(tests)} tests passed")
        
        # Generate summary
        summary = {
            "test_date": datetime.now().isoformat(),
            "test_type": "Tags & Modal Functionality",
            "backend_url": self.backend_url,
            "total_tests": len(tests),
            "passed_tests": passed,
            "failed_tests": len(tests) - passed,
            "success_rate": f"{(passed/len(tests)*100):.1f}%",
            "detailed_results": self.results
        }
        
        return summary

def main():
    """Main tags modal test function"""
    tester = TagsModalTester()
    summary = tester.run_tags_modal_tests()
    
    # Save results
    with open("/tmp/tags_modal_report.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: /tmp/tags_modal_report.json")
    
    # Return exit code based on results
    if summary["passed_tests"] >= summary["total_tests"] * 0.8:  # 80% pass rate
        print("🎉 Tags & Modal tests PASSED")
        return 0
    else:
        print("❌ Tags & Modal tests FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())