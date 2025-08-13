#!/usr/bin/env python3
"""
Frontend validation test suite
Validate frontend interface corrections and functionality
"""

import requests
import time
import json
import sys
from datetime import datetime

class FrontendValidator:
    def __init__(self, frontend_url="http://localhost:45679", backend_url="http://localhost:8000"):
        self.frontend_url = frontend_url
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
    
    def test_frontend_accessibility(self):
        """Test if frontend is accessible"""
        try:
            response = requests.get(self.frontend_url, timeout=10)
            if response.status_code == 200:
                self.log_result("Frontend Accessibility", "PASS", f"Frontend accessible on {self.frontend_url}")
                return True
            else:
                self.log_result("Frontend Accessibility", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Frontend Accessibility", "FAIL", error=e)
            return False
    
    def test_cors_configuration(self):
        """Test CORS configuration between frontend and backend"""
        try:
            # Test preflight request
            headers = {
                'Origin': self.frontend_url,
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'Authorization,Content-Type'
            }
            response = requests.options(f"{self.backend_url}/health", headers=headers, timeout=5)
            
            if response.status_code == 200:
                cors_headers = response.headers
                if 'Access-Control-Allow-Origin' in cors_headers:
                    self.log_result("CORS Configuration", "PASS", 
                                   f"CORS properly configured - Origin: {cors_headers.get('Access-Control-Allow-Origin')}")
                    return True
                else:
                    self.log_result("CORS Configuration", "FAIL", "Missing CORS headers")
                    return False
            else:
                self.log_result("CORS Configuration", "FAIL", f"Preflight failed - HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("CORS Configuration", "FAIL", error=e)
            return False
    
    def test_backend_health(self):
        """Test backend health endpoint"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                self.log_result("Backend Health", "PASS", 
                               f"Version: {health_data.get('version')}, Status: {health_data.get('status')}")
                return True
            else:
                self.log_result("Backend Health", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Backend Health", "FAIL", error=e)
            return False
    
    def test_api_documentation(self):
        """Test API documentation accessibility"""
        try:
            response = requests.get(f"{self.backend_url}/docs", timeout=5)
            if response.status_code == 200:
                self.log_result("API Documentation", "PASS", "Swagger UI accessible")
                return True
            else:
                self.log_result("API Documentation", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("API Documentation", "FAIL", error=e)
            return False
    
    def test_frontend_static_resources(self):
        """Test frontend static resources"""
        static_files = [
            "/_next/static/css/app/layout.css",  # Next.js CSS
            "/favicon.ico",  # Favicon
        ]
        
        passed = 0
        total = len(static_files)
        
        for static_file in static_files:
            try:
                response = requests.get(f"{self.frontend_url}{static_file}", timeout=5)
                if response.status_code in [200, 304]:
                    passed += 1
            except:
                pass
        
        if passed > 0:
            self.log_result("Static Resources", "PASS", f"{passed}/{total} static resources accessible")
            return True
        else:
            self.log_result("Static Resources", "WARN", "No static resources found - possibly server-side rendered")
            return False
    
    def test_no_error_loops(self):
        """Test for absence of infinite error loops"""
        try:
            # Make multiple rapid requests to detect error loops
            error_responses = 0
            for i in range(5):
                response = requests.get(self.frontend_url, timeout=3)
                if response.status_code >= 500:
                    error_responses += 1
                time.sleep(0.1)
            
            if error_responses == 0:
                self.log_result("Error Loop Detection", "PASS", "No server errors in rapid requests")
                return True
            elif error_responses < 3:
                self.log_result("Error Loop Detection", "WARN", f"{error_responses}/5 requests had server errors")
                return False
            else:
                self.log_result("Error Loop Detection", "FAIL", f"{error_responses}/5 requests had server errors")
                return False
        except Exception as e:
            self.log_result("Error Loop Detection", "FAIL", error=e)
            return False
    
    def run_validation(self):
        """Run complete frontend validation"""
        print("🚀 Starting Frontend Validation Suite")
        print("=" * 50)
        
        tests = [
            self.test_frontend_accessibility,
            self.test_cors_configuration,
            self.test_backend_health,
            self.test_api_documentation,
            self.test_frontend_static_resources,
            self.test_no_error_loops
        ]
        
        passed = 0
        for test in tests:
            if test():
                passed += 1
        
        print("\n" + "=" * 50)
        print(f"📊 Validation Results: {passed}/{len(tests)} tests passed")
        
        # Generate summary
        summary = {
            "validation_date": datetime.now().isoformat(),
            "frontend_url": self.frontend_url,
            "backend_url": self.backend_url,
            "total_tests": len(tests),
            "passed_tests": passed,
            "failed_tests": len(tests) - passed,
            "success_rate": f"{(passed/len(tests)*100):.1f}%",
            "detailed_results": self.results
        }
        
        return summary

def main():
    """Main validation function"""
    validator = FrontendValidator()
    summary = validator.run_validation()
    
    # Save results
    with open("/tmp/frontend_validation_report.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: /tmp/frontend_validation_report.json")
    
    # Return exit code based on results
    if summary["passed_tests"] >= summary["total_tests"] * 0.8:  # 80% pass rate
        print("🎉 Frontend validation PASSED")
        return 0
    else:
        print("❌ Frontend validation FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())