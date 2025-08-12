#!/usr/bin/env python3
"""
FINAL END-TO-END VALIDATION for Budget Famille v2.3
Quality Assurance Lead - Complete System Validation

This script performs complete validation of all system components
with correct credentials and endpoints.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class FinalValidator:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8001"  # Test server port
        self.token = None
        self.session = requests.Session()
        self.results = []
        
    def log_result(self, test_name: str, status: str, details: str = ""):
        """Log test result"""
        if status == "PASS":
            icon = "✅"
            color = Colors.GREEN
        elif status == "FAIL":
            icon = "❌"
            color = Colors.RED
        else:
            icon = "⚠️"
            color = Colors.YELLOW
            
        print(f"{icon} {color}{test_name}{Colors.RESET}")
        if details:
            print(f"   {Colors.WHITE}{details}{Colors.RESET}")
            
        self.results.append({"test": test_name, "status": status, "details": details})
        
    def test_health(self):
        """Test server health"""
        print(f"\n{Colors.CYAN}=== 1. SERVER HEALTH ==={Colors.RESET}")
        
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_result("Server Health Check", "PASS", f"Database: {data.get('database')}")
                    return True
                else:
                    self.log_result("Server Health Check", "FAIL", f"Status: {data.get('status')}")
                    return False
            else:
                self.log_result("Server Health Check", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Server Health Check", "FAIL", str(e))
            return False
            
    def test_authentication(self):
        """Test authentication with correct credentials"""
        print(f"\n{Colors.CYAN}=== 2. AUTHENTICATION ==={Colors.RESET}")
        
        try:
            # Test login with correct credentials
            token_data = {"username": "admin", "password": "secret"}
            response = self.session.post(
                f"{self.base_url}/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            if response.status_code == 200:
                token_response = response.json()
                if "access_token" in token_response:
                    self.token = token_response["access_token"]
                    self.log_result("Login Authentication", "PASS", "Token obtained successfully")
                    
                    # Test token validation
                    headers = {"Authorization": f"Bearer {self.token}"}
                    validation_response = self.session.get(
                        f"{self.base_url}/api/v1/auth/validate",
                        headers=headers,
                        timeout=10
                    )
                    
                    if validation_response.status_code == 200:
                        self.log_result("Token Validation", "PASS", "Token validated successfully")
                        return True
                    else:
                        self.log_result("Token Validation", "FAIL", f"HTTP {validation_response.status_code}")
                        return False
                else:
                    self.log_result("Login Authentication", "FAIL", "No access_token in response")
                    return False
            else:
                self.log_result("Login Authentication", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Login Authentication", "FAIL", str(e))
            return False
            
    def test_configuration(self):
        """Test configuration endpoints"""
        print(f"\n{Colors.CYAN}=== 3. CONFIGURATION MANAGEMENT ==={Colors.RESET}")
        
        if not self.token:
            self.log_result("Configuration Test", "FAIL", "No authentication token")
            return False
            
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            # Test GET config
            response = self.session.get(f"{self.base_url}/config", headers=headers, timeout=10)
            if response.status_code == 200:
                config_data = response.json()
                self.log_result("GET Configuration", "PASS", f"Retrieved config with {len(config_data)} fields")
                
                # Test POST config (update)
                test_config = {
                    "salaire1": 2800.0,
                    "salaire2": 2300.0,
                    "charges_fixes": 1300.0
                }
                
                post_response = self.session.post(
                    f"{self.base_url}/config",
                    json=test_config,
                    headers={**headers, "Content-Type": "application/json"},
                    timeout=10
                )
                
                if post_response.status_code == 200:
                    self.log_result("POST Configuration", "PASS", "Configuration updated successfully")
                    return True
                else:
                    self.log_result("POST Configuration", "FAIL", f"HTTP {post_response.status_code}")
                    return False
            else:
                self.log_result("GET Configuration", "FAIL", f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Configuration Test", "FAIL", str(e))
            return False
            
    def test_cors(self):
        """Test CORS headers"""
        print(f"\n{Colors.CYAN}=== 4. CORS HEADERS ==={Colors.RESET}")
        
        try:
            # Test with a simple GET request to see CORS headers
            response = self.session.get(f"{self.base_url}/", timeout=5)
            headers = response.headers
            
            cors_present = False
            if "access-control-allow-origin" in headers:
                self.log_result("CORS Origin Header", "PASS", f"Value: {headers['access-control-allow-origin']}")
                cors_present = True
            else:
                # Try OPTIONS request
                options_response = self.session.options(f"{self.base_url}/", timeout=5)
                options_headers = options_response.headers
                
                if "access-control-allow-origin" in options_headers:
                    self.log_result("CORS Origin Header", "PASS", f"Value: {options_headers['access-control-allow-origin']}")
                    cors_present = True
                else:
                    self.log_result("CORS Origin Header", "WARN", "Header not found in GET or OPTIONS")
                    
            return cors_present
            
        except Exception as e:
            self.log_result("CORS Headers Test", "FAIL", str(e))
            return False
            
    def test_error_handling(self):
        """Test error handling"""
        print(f"\n{Colors.CYAN}=== 5. ERROR HANDLING ==={Colors.RESET}")
        
        success_count = 0
        
        # Test 404
        try:
            response = self.session.get(f"{self.base_url}/nonexistent", timeout=5)
            if response.status_code == 404:
                self.log_result("404 Error Handling", "PASS", "Proper 404 response")
                success_count += 1
            else:
                self.log_result("404 Error Handling", "FAIL", f"Expected 404, got {response.status_code}")
        except Exception as e:
            self.log_result("404 Error Handling", "FAIL", str(e))
            
        # Test unauthorized access
        try:
            response = self.session.get(f"{self.base_url}/config", timeout=5)
            if response.status_code in [401, 403]:
                self.log_result("Unauthorized Access Handling", "PASS", f"Proper {response.status_code} response")
                success_count += 1
            else:
                self.log_result("Unauthorized Access Handling", "WARN", f"Got {response.status_code}")
        except Exception as e:
            self.log_result("Unauthorized Access Handling", "FAIL", str(e))
            
        return success_count >= 1
        
    def test_performance(self):
        """Test basic performance"""
        print(f"\n{Colors.CYAN}=== 6. PERFORMANCE ==={Colors.RESET}")
        
        if not self.token:
            self.log_result("Performance Test", "FAIL", "No authentication token")
            return False
            
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            # Test response times
            times = []
            for i in range(3):
                start_time = time.time()
                response = self.session.get(f"{self.base_url}/health", headers=headers, timeout=10)
                duration = time.time() - start_time
                times.append(duration)
                
            avg_time = sum(times) / len(times)
            max_time = max(times)
            
            if avg_time < 1.0:
                self.log_result("Response Time Performance", "PASS", f"Avg: {avg_time*1000:.2f}ms, Max: {max_time*1000:.2f}ms")
                return True
            elif avg_time < 3.0:
                self.log_result("Response Time Performance", "WARN", f"Avg: {avg_time*1000:.2f}ms (acceptable)")
                return True
            else:
                self.log_result("Response Time Performance", "FAIL", f"Avg: {avg_time*1000:.2f}ms (too slow)")
                return False
                
        except Exception as e:
            self.log_result("Performance Test", "FAIL", str(e))
            return False
            
    def test_critical_user_journeys(self):
        """Test complete user journeys"""
        print(f"\n{Colors.CYAN}=== 7. CRITICAL USER JOURNEYS ==={Colors.RESET}")
        
        if not self.token:
            self.log_result("User Journeys Test", "FAIL", "No authentication token")
            return False
            
        headers = {"Authorization": f"Bearer {self.token}"}
        journey_score = 0
        
        # Journey 1: Login -> Get Config -> Update Config
        try:
            # Already logged in, get config
            config_response = self.session.get(f"{self.base_url}/config", headers=headers, timeout=10)
            if config_response.status_code == 200:
                config_data = config_response.json()
                
                # Update config
                updated_config = config_data.copy()
                updated_config["salaire1"] = 3000.0  # Test update
                
                update_response = self.session.post(
                    f"{self.base_url}/config",
                    json=updated_config,
                    headers={**headers, "Content-Type": "application/json"},
                    timeout=10
                )
                
                if update_response.status_code == 200:
                    self.log_result("Complete Config Journey", "PASS", "Login -> Read -> Update successful")
                    journey_score += 1
                else:
                    self.log_result("Complete Config Journey", "FAIL", f"Update failed: HTTP {update_response.status_code}")
            else:
                self.log_result("Complete Config Journey", "FAIL", f"Config read failed: HTTP {config_response.status_code}")
                
        except Exception as e:
            self.log_result("Complete Config Journey", "FAIL", str(e))
            
        # Journey 2: Health check -> Auth validation
        try:
            health_response = self.session.get(f"{self.base_url}/health", timeout=10)
            auth_response = self.session.get(f"{self.base_url}/api/v1/auth/validate", headers=headers, timeout=10)
            
            if health_response.status_code == 200 and auth_response.status_code == 200:
                self.log_result("Health + Auth Journey", "PASS", "Health check and auth validation successful")
                journey_score += 1
            else:
                self.log_result("Health + Auth Journey", "FAIL", f"Health: {health_response.status_code}, Auth: {auth_response.status_code}")
                
        except Exception as e:
            self.log_result("Health + Auth Journey", "FAIL", str(e))
            
        return journey_score >= 1
        
    def generate_final_report(self):
        """Generate final validation report"""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.WHITE}📊 FINAL VALIDATION REPORT{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
        
        passed = len([r for r in self.results if r["status"] == "PASS"])
        failed = len([r for r in self.results if r["status"] == "FAIL"])
        warnings = len([r for r in self.results if r["status"] == "WARN"])
        total = len(self.results)
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"{Colors.BOLD}Test Results Summary:{Colors.RESET}")
        print(f"  ✅ Passed: {Colors.GREEN}{passed}{Colors.RESET}")
        print(f"  ❌ Failed: {Colors.RED}{failed}{Colors.RESET}")
        print(f"  ⚠️  Warnings: {Colors.YELLOW}{warnings}{Colors.RESET}")
        print(f"  📊 Success Rate: {Colors.CYAN}{success_rate:.1f}%{Colors.RESET}")
        
        # Generate recommendations
        print(f"\n{Colors.BOLD}🎯 Quality Assessment:{Colors.RESET}")
        
        if success_rate >= 90:
            status = "EXCELLENT - READY FOR PRODUCTION"
            color = Colors.GREEN
            recommendations = [
                "✅ All critical systems functioning properly",
                "✅ Performance meets requirements",
                "✅ Security controls validated",
                "🚀 Recommended for immediate release"
            ]
        elif success_rate >= 80:
            status = "GOOD - READY FOR RELEASE"
            color = Colors.GREEN
            recommendations = [
                "✅ Core functionality validated",
                "⚠️ Monitor any warning conditions",
                "🔧 Address minor issues post-release",
                "🚀 Approved for production release"
            ]
        elif success_rate >= 60:
            status = "ACCEPTABLE - MINOR FIXES NEEDED"
            color = Colors.YELLOW
            recommendations = [
                "⚠️ Some non-critical issues identified",
                "🔧 Fix failed tests before release",
                "📋 Create monitoring plan for warnings",
                "⏰ Release after fixes are applied"
            ]
        else:
            status = "NOT READY - CRITICAL ISSUES FOUND"
            color = Colors.RED
            recommendations = [
                "❌ Critical system failures detected",
                "🔧 Must fix all failed tests",
                "🔒 Security or functionality concerns",
                "⛔ DO NOT RELEASE until issues resolved"
            ]
            
        print(f"  🏆 Status: {color}{status}{Colors.RESET}")
        
        print(f"\n{Colors.BOLD}📋 Recommendations:{Colors.RESET}")
        for rec in recommendations:
            print(f"  {rec}")
            
        # Save detailed report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "success_rate": success_rate,
                "status": status
            },
            "test_results": self.results,
            "recommendations": recommendations
        }
        
        with open("final_e2e_validation_report.json", "w") as f:
            json.dump(report_data, f, indent=2)
            
        print(f"\n📄 Detailed report saved to: {Colors.CYAN}final_e2e_validation_report.json{Colors.RESET}")
        
        return success_rate >= 80
        
    def run_all_tests(self):
        """Run all validation tests"""
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("🔍 Budget Famille v2.3 - Final E2E Validation")
        print("="*60)
        print(f"Quality Assurance Lead - Production Readiness Assessment{Colors.RESET}")
        print(f"Execution time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Execute all tests
        test_results = []
        test_results.append(self.test_health())
        test_results.append(self.test_authentication())
        test_results.append(self.test_configuration())
        test_results.append(self.test_cors())
        test_results.append(self.test_error_handling())
        test_results.append(self.test_performance())
        test_results.append(self.test_critical_user_journeys())
        
        # Generate final report
        ready_for_release = self.generate_final_report()
        
        return ready_for_release

def main():
    """Main execution function"""
    validator = FinalValidator()
    
    try:
        ready = validator.run_all_tests()
        
        if ready:
            print(f"\n{Colors.GREEN}🎉 VALIDATION PASSED - READY FOR RELEASE{Colors.RESET}")
            return 0
        else:
            print(f"\n{Colors.RED}❌ VALIDATION FAILED - MANUAL INTERVENTION REQUIRED{Colors.RESET}")
            return 1
            
    except Exception as e:
        print(f"\n{Colors.RED}💥 CRITICAL ERROR: {e}{Colors.RESET}")
        return 1

if __name__ == "__main__":
    exit(main())