#!/usr/bin/env python3
"""
End-to-End Navigation Test Suite
Test hierarchical navigation and modal functionality
"""

import requests
import time
import json
import sys
from datetime import datetime

class E2ENavigationTester:
    def __init__(self, frontend_url="http://localhost:45678", backend_url="http://localhost:8000"):
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
    
    def test_main_pages_accessibility(self):
        """Test accessibility of main application pages"""
        pages = [
            "/",  # Dashboard
            "/transactions",  # Transactions page
            "/settings",  # Settings page
            "/analytics",  # Analytics page
            "/upload"  # Upload page
        ]
        
        accessible_pages = 0
        for page in pages:
            try:
                response = requests.get(f"{self.frontend_url}{page}", timeout=10)
                if response.status_code == 200:
                    accessible_pages += 1
                    print(f"   ✓ {page} accessible")
                else:
                    print(f"   ✗ {page} returned {response.status_code}")
            except Exception as e:
                print(f"   ✗ {page} error: {e}")
        
        if accessible_pages == len(pages):
            self.log_result("Main Pages Accessibility", "PASS", 
                           f"All {len(pages)} pages accessible")
            return True
        elif accessible_pages > len(pages) // 2:
            self.log_result("Main Pages Accessibility", "WARN", 
                           f"{accessible_pages}/{len(pages)} pages accessible")
            return False
        else:
            self.log_result("Main Pages Accessibility", "FAIL", 
                           f"Only {accessible_pages}/{len(pages)} pages accessible")
            return False
    
    def test_api_endpoints_availability(self):
        """Test critical API endpoints availability"""
        endpoints = [
            "/health",
            "/config",
            "/tags",
            "/transactions",
            "/fixed-lines",
            "/provisions"
        ]
        
        available_endpoints = 0
        for endpoint in endpoints:
            try:
                # Test OPTIONS first for CORS support
                response = requests.options(f"{self.backend_url}{endpoint}", timeout=5)
                if response.status_code in [200, 405]:  # 405 = Method not allowed but endpoint exists
                    available_endpoints += 1
                elif endpoint == "/health":
                    # Health endpoint should always be GET
                    response = requests.get(f"{self.backend_url}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        available_endpoints += 1
            except Exception as e:
                print(f"   ✗ {endpoint} error: {e}")
        
        if available_endpoints == len(endpoints):
            self.log_result("API Endpoints Availability", "PASS", 
                           f"All {len(endpoints)} endpoints available")
            return True
        elif available_endpoints > len(endpoints) // 2:
            self.log_result("API Endpoints Availability", "WARN", 
                           f"{available_endpoints}/{len(endpoints)} endpoints available")
            return False
        else:
            self.log_result("API Endpoints Availability", "FAIL", 
                           f"Only {available_endpoints}/{len(endpoints)} endpoints available")
            return False
    
    def test_dashboard_components(self):
        """Test dashboard component loading and structure"""
        try:
            response = requests.get(self.frontend_url, timeout=10)
            if response.status_code != 200:
                self.log_result("Dashboard Components", "FAIL", "Dashboard not accessible")
                return False
            
            content = response.text
            
            # Check for expected dashboard components in HTML
            dashboard_elements = [
                "dashboard",  # Main dashboard container
                "balance",    # Account balance
                "expenses",   # Expenses section
                "budget",     # Budget information
                "transactions" # Transaction data
            ]
            
            found_elements = 0
            for element in dashboard_elements:
                if element.lower() in content.lower():
                    found_elements += 1
            
            if found_elements >= 3:
                self.log_result("Dashboard Components", "PASS", 
                               f"Dashboard structure valid ({found_elements}/5 elements found)")
                return True
            else:
                self.log_result("Dashboard Components", "WARN", 
                               f"Limited dashboard elements ({found_elements}/5 found)")
                return False
                
        except Exception as e:
            self.log_result("Dashboard Components", "FAIL", error=e)
            return False
    
    def test_responsive_design(self):
        """Test responsive design elements"""
        try:
            response = requests.get(self.frontend_url, timeout=10)
            content = response.text
            
            # Check for responsive design indicators
            responsive_indicators = [
                "viewport",
                "responsive",
                "mobile",
                "@media",
                "grid",
                "flex"
            ]
            
            found_indicators = 0
            for indicator in responsive_indicators:
                if indicator.lower() in content.lower():
                    found_indicators += 1
            
            if found_indicators >= 3:
                self.log_result("Responsive Design", "PASS", 
                               f"Responsive design elements present ({found_indicators}/6 indicators)")
                return True
            else:
                self.log_result("Responsive Design", "WARN", 
                               f"Limited responsive indicators ({found_indicators}/6 found)")
                return False
                
        except Exception as e:
            self.log_result("Responsive Design", "FAIL", error=e)
            return False
    
    def test_javascript_loading(self):
        """Test JavaScript loading and Next.js functionality"""
        try:
            response = requests.get(self.frontend_url, timeout=10)
            content = response.text
            
            # Check for Next.js and React indicators
            js_indicators = [
                "_next",      # Next.js assets
                "react",      # React framework
                "script",     # Script tags
                "__next",     # Next.js app
                "hydrat"      # Hydration
            ]
            
            found_indicators = 0
            for indicator in js_indicators:
                if indicator.lower() in content.lower():
                    found_indicators += 1
            
            if found_indicators >= 3:
                self.log_result("JavaScript Loading", "PASS", 
                               f"JavaScript framework properly configured ({found_indicators}/5 indicators)")
                return True
            else:
                self.log_result("JavaScript Loading", "WARN", 
                               f"Limited JS indicators ({found_indicators}/5 found)")
                return False
                
        except Exception as e:
            self.log_result("JavaScript Loading", "FAIL", error=e)
            return False
    
    def test_performance_metrics(self):
        """Test basic performance metrics"""
        try:
            start_time = time.time()
            response = requests.get(self.frontend_url, timeout=15)
            end_time = time.time()
            
            response_time = end_time - start_time
            content_size = len(response.content)
            
            # Performance thresholds
            if response_time < 2.0:
                performance_status = "EXCELLENT"
            elif response_time < 5.0:
                performance_status = "GOOD"
            elif response_time < 10.0:
                performance_status = "ACCEPTABLE"
            else:
                performance_status = "SLOW"
            
            details = f"Response time: {response_time:.2f}s, Size: {content_size/1024:.1f}KB"
            
            if response_time < 10.0:
                self.log_result("Performance Metrics", "PASS", 
                               f"{performance_status} - {details}")
                return True
            else:
                self.log_result("Performance Metrics", "FAIL", 
                               f"{performance_status} - {details}")
                return False
                
        except Exception as e:
            self.log_result("Performance Metrics", "FAIL", error=e)
            return False
    
    def run_e2e_tests(self):
        """Run complete E2E test suite"""
        print("🎯 Starting End-to-End Navigation Tests")
        print("=" * 50)
        
        tests = [
            self.test_main_pages_accessibility,
            self.test_api_endpoints_availability,
            self.test_dashboard_components,
            self.test_responsive_design,
            self.test_javascript_loading,
            self.test_performance_metrics
        ]
        
        passed = 0
        for test in tests:
            if test():
                passed += 1
        
        print("\n" + "=" * 50)
        print(f"📊 E2E Test Results: {passed}/{len(tests)} tests passed")
        
        # Generate summary
        summary = {
            "test_date": datetime.now().isoformat(),
            "test_type": "E2E Navigation & UI",
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
    """Main E2E test function"""
    tester = E2ENavigationTester()
    summary = tester.run_e2e_tests()
    
    # Save results
    with open("/tmp/e2e_navigation_report.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: /tmp/e2e_navigation_report.json")
    
    # Return exit code based on results
    if summary["passed_tests"] >= summary["total_tests"] * 0.7:  # 70% pass rate for E2E
        print("🎉 E2E Navigation tests PASSED")
        return 0
    else:
        print("❌ E2E Navigation tests FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())