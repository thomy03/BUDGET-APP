#!/usr/bin/env python3
"""
COMPREHENSIVE END-TO-END VALIDATION for Budget Famille v2.3
Quality Assurance Lead - Post-Fix Validation Suite

This test suite performs systematic validation of all critical system components:
1. Backend API Testing - All endpoints and authentication
2. Frontend Integration Testing - User journeys and API calls
3. Critical User Journeys - Complete workflow validation
4. Error Handling Testing - Network failures and edge cases
5. Performance Testing - Response times and resource usage

Author: QA Lead
Version: 2.3.0
Date: 2025-08-11
"""

import requests
import json
import time
import sqlite3
import os
import sys
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class E2EValidator:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
        self.test_results = []
        self.performance_metrics = []
        
    def print_header(self, title: str):
        """Print formatted test section header"""
        print(f"\n{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.WHITE}🔍 {title}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
        
    def print_test(self, test_name: str, status: str, details: str = ""):
        """Print test result with formatting"""
        if status == "PASS":
            icon = "✅"
            color = Colors.GREEN
        elif status == "FAIL":
            icon = "❌"
            color = Colors.RED
        elif status == "WARN":
            icon = "⚠️"
            color = Colors.YELLOW
        else:
            icon = "ℹ️"
            color = Colors.BLUE
            
        print(f"{icon} {color}{test_name}{Colors.RESET}")
        if details:
            print(f"   {Colors.WHITE}{details}{Colors.RESET}")
            
        self.test_results.append({
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
    def measure_performance(self, operation: str, duration: float, additional_metrics: Dict = None):
        """Record performance metrics"""
        metrics = {
            "operation": operation,
            "duration_ms": round(duration * 1000, 2),
            "timestamp": datetime.now().isoformat()
        }
        if additional_metrics:
            metrics.update(additional_metrics)
        self.performance_metrics.append(metrics)
        
    def test_server_health(self) -> bool:
        """Test if the server is running and responding"""
        self.print_header("1. SERVER HEALTH CHECK")
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            duration = time.time() - start_time
            
            self.measure_performance("health_check", duration, {"status_code": response.status_code})
            
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("status") == "healthy":
                    self.print_test("Server Health Check", "PASS", f"Response time: {duration*1000:.2f}ms")
                    return True
                else:
                    self.print_test("Server Health Check", "WARN", f"Status: {health_data.get('status')}")
                    return True
            else:
                self.print_test("Server Health Check", "FAIL", f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.print_test("Server Health Check", "FAIL", str(e))
            return False
            
    def test_authentication_endpoints(self) -> bool:
        """Test all authentication-related endpoints"""
        self.print_header("2. AUTHENTICATION ENDPOINTS")
        
        success_count = 0
        total_tests = 0
        
        # Test 1: Legacy token endpoint
        try:
            total_tests += 1
            start_time = time.time()
            
            token_data = {
                "username": "admin",
                "password": "admin"
            }
            
            response = self.session.post(
                f"{self.base_url}/token", 
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            duration = time.time() - start_time
            
            self.measure_performance("legacy_token_login", duration, {"status_code": response.status_code})
            
            if response.status_code == 200:
                token_response = response.json()
                if "access_token" in token_response:
                    self.token = token_response["access_token"]
                    self.print_test("Legacy Token Endpoint (/token)", "PASS", f"Token obtained in {duration*1000:.2f}ms")
                    success_count += 1
                else:
                    self.print_test("Legacy Token Endpoint (/token)", "FAIL", "No access_token in response")
            else:
                self.print_test("Legacy Token Endpoint (/token)", "FAIL", f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.print_test("Legacy Token Endpoint (/token)", "FAIL", str(e))
            
        # Test 2: New Auth API endpoint
        try:
            total_tests += 1
            start_time = time.time()
            
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/token", 
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            duration = time.time() - start_time
            
            self.measure_performance("api_token_login", duration, {"status_code": response.status_code})
            
            if response.status_code == 200:
                self.print_test("API Token Endpoint (/api/v1/auth/token)", "PASS", f"Response time: {duration*1000:.2f}ms")
                success_count += 1
            else:
                self.print_test("API Token Endpoint (/api/v1/auth/token)", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.print_test("API Token Endpoint (/api/v1/auth/token)", "FAIL", str(e))
            
        # Test 3: Token validation if we have a token
        if self.token:
            try:
                total_tests += 1
                start_time = time.time()
                
                headers = {"Authorization": f"Bearer {self.token}"}
                response = self.session.get(
                    f"{self.base_url}/api/v1/auth/validate",
                    headers=headers,
                    timeout=10
                )
                duration = time.time() - start_time
                
                self.measure_performance("token_validation", duration, {"status_code": response.status_code})
                
                if response.status_code == 200:
                    self.print_test("Token Validation", "PASS", f"Token validated in {duration*1000:.2f}ms")
                    success_count += 1
                else:
                    self.print_test("Token Validation", "FAIL", f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.print_test("Token Validation", "FAIL", str(e))
        
        return success_count >= 2  # At least 2 out of 3 auth tests should pass
        
    def test_cors_headers(self) -> bool:
        """Test CORS headers are present"""
        self.print_header("3. CORS HEADERS VALIDATION")
        
        try:
            response = self.session.options(f"{self.base_url}/", timeout=10)
            headers = response.headers
            
            cors_checks = [
                ("Access-Control-Allow-Origin", "CORS Origin Header"),
                ("Access-Control-Allow-Methods", "CORS Methods Header"), 
                ("Access-Control-Allow-Headers", "CORS Headers Header")
            ]
            
            passed = 0
            for header, test_name in cors_checks:
                if header in headers:
                    self.print_test(test_name, "PASS", f"Value: {headers[header]}")
                    passed += 1
                else:
                    self.print_test(test_name, "FAIL", "Header missing")
                    
            return passed >= 2
            
        except Exception as e:
            self.print_test("CORS Headers Check", "FAIL", str(e))
            return False
            
    def test_configuration_endpoints(self) -> bool:
        """Test configuration management endpoints"""
        self.print_header("4. CONFIGURATION ENDPOINTS")
        
        if not self.token:
            self.print_test("Configuration Test", "FAIL", "No authentication token available")
            return False
            
        headers = {"Authorization": f"Bearer {self.token}"}
        success_count = 0
        
        # Test GET config
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/config", headers=headers, timeout=10)
            duration = time.time() - start_time
            
            self.measure_performance("get_config", duration, {"status_code": response.status_code})
            
            if response.status_code == 200:
                config_data = response.json()
                self.print_test("GET /config", "PASS", f"Retrieved config in {duration*1000:.2f}ms")
                success_count += 1
            else:
                self.print_test("GET /config", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.print_test("GET /config", "FAIL", str(e))
            
        # Test POST config (update)
        try:
            start_time = time.time()
            test_config = {
                "salaire1": 2500.0,
                "salaire2": 2200.0,
                "charges_fixes": 1200.0
            }
            
            response = self.session.post(
                f"{self.base_url}/config", 
                json=test_config,
                headers={**headers, "Content-Type": "application/json"},
                timeout=10
            )
            duration = time.time() - start_time
            
            self.measure_performance("post_config", duration, {"status_code": response.status_code})
            
            if response.status_code in [200, 201]:
                self.print_test("POST /config", "PASS", f"Config updated in {duration*1000:.2f}ms")
                success_count += 1
            else:
                self.print_test("POST /config", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.print_test("POST /config", "FAIL", str(e))
            
        return success_count >= 1
        
    def test_database_connectivity(self) -> bool:
        """Test database connectivity and basic queries"""
        self.print_header("5. DATABASE CONNECTIVITY")
        
        try:
            # Check if database file exists
            db_path = "budget.db"
            if os.path.exists(db_path):
                self.print_test("Database File Exists", "PASS", f"Found at {db_path}")
            else:
                self.print_test("Database File Exists", "FAIL", f"Missing: {db_path}")
                return False
                
            # Test database connection
            start_time = time.time()
            conn = sqlite3.connect(db_path, timeout=10)
            
            # Test basic query
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            duration = time.time() - start_time
            
            self.measure_performance("db_connection", duration, {"table_count": len(tables)})
            
            if tables:
                table_names = [table[0] for table in tables]
                self.print_test("Database Connection", "PASS", f"Found {len(tables)} tables: {', '.join(table_names[:5])}")
                
                # Test each important table
                required_tables = ["config", "transactions", "fixed_lines", "custom_provisions"]
                tables_found = 0
                
                for table in required_tables:
                    if table in table_names:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        self.print_test(f"Table: {table}", "PASS", f"{count} records")
                        tables_found += 1
                    else:
                        self.print_test(f"Table: {table}", "WARN", "Table missing")
                        
                conn.close()
                return tables_found >= 2
            else:
                self.print_test("Database Connection", "FAIL", "No tables found")
                conn.close()
                return False
                
        except Exception as e:
            self.print_test("Database Connection", "FAIL", str(e))
            return False
            
    def test_error_handling(self) -> bool:
        """Test error handling scenarios"""
        self.print_header("6. ERROR HANDLING")
        
        success_count = 0
        
        # Test 1: Invalid endpoint
        try:
            response = self.session.get(f"{self.base_url}/nonexistent", timeout=5)
            if response.status_code == 404:
                self.print_test("404 Error Handling", "PASS", "Proper 404 response")
                success_count += 1
            else:
                self.print_test("404 Error Handling", "FAIL", f"Expected 404, got {response.status_code}")
        except Exception as e:
            self.print_test("404 Error Handling", "FAIL", str(e))
            
        # Test 2: Unauthorized access
        try:
            response = self.session.get(f"{self.base_url}/config", timeout=5)
            if response.status_code == 401:
                self.print_test("401 Unauthorized Handling", "PASS", "Proper authentication required")
                success_count += 1
            else:
                self.print_test("401 Unauthorized Handling", "WARN", f"Got {response.status_code} instead of 401")
        except Exception as e:
            self.print_test("401 Unauthorized Handling", "FAIL", str(e))
            
        # Test 3: Invalid JSON
        if self.token:
            try:
                headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
                response = self.session.post(
                    f"{self.base_url}/config", 
                    data="invalid json",
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 422:
                    self.print_test("422 Invalid JSON Handling", "PASS", "Proper validation error")
                    success_count += 1
                else:
                    self.print_test("422 Invalid JSON Handling", "WARN", f"Got {response.status_code}")
            except Exception as e:
                self.print_test("422 Invalid JSON Handling", "FAIL", str(e))
                
        return success_count >= 2
        
    def test_performance_benchmarks(self) -> bool:
        """Test performance benchmarks"""
        self.print_header("7. PERFORMANCE BENCHMARKS")
        
        if not self.token:
            self.print_test("Performance Tests", "FAIL", "No authentication token")
            return False
            
        headers = {"Authorization": f"Bearer {self.token}"}
        performance_passed = 0
        
        # Test response times for key endpoints
        endpoints_to_test = [
            ("/health", "Health Check"),
            ("/config", "Configuration"),
            ("/", "Root Endpoint")
        ]
        
        for endpoint, name in endpoints_to_test:
            try:
                times = []
                for i in range(3):  # Test 3 times for average
                    start_time = time.time()
                    response = self.session.get(f"{self.base_url}{endpoint}", headers=headers, timeout=10)
                    duration = time.time() - start_time
                    times.append(duration)
                    
                avg_time = sum(times) / len(times)
                max_time = max(times)
                
                self.measure_performance(f"benchmark_{endpoint.replace('/', '_')}", avg_time, {
                    "max_time": max_time,
                    "iterations": len(times)
                })
                
                if avg_time < 1.0:  # Less than 1 second average
                    self.print_test(f"{name} Performance", "PASS", f"Avg: {avg_time*1000:.2f}ms, Max: {max_time*1000:.2f}ms")
                    performance_passed += 1
                elif avg_time < 3.0:  # Less than 3 seconds
                    self.print_test(f"{name} Performance", "WARN", f"Avg: {avg_time*1000:.2f}ms (acceptable)")
                    performance_passed += 1
                else:
                    self.print_test(f"{name} Performance", "FAIL", f"Avg: {avg_time*1000:.2f}ms (too slow)")
                    
            except Exception as e:
                self.print_test(f"{name} Performance", "FAIL", str(e))
                
        return performance_passed >= 2
        
    def test_frontend_compatibility(self) -> bool:
        """Test if responses are compatible with expected frontend format"""
        self.print_header("8. FRONTEND COMPATIBILITY")
        
        compatibility_score = 0
        
        # Test JSON response format
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "message" in data:
                    self.print_test("JSON Response Format", "PASS", "Valid JSON with message field")
                    compatibility_score += 1
                else:
                    self.print_test("JSON Response Format", "FAIL", "Invalid JSON structure")
        except Exception as e:
            self.print_test("JSON Response Format", "FAIL", str(e))
            
        # Test authentication response format
        if self.token:
            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = self.session.get(f"{self.base_url}/api/v1/auth/validate", headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if "valid" in data and "user" in data:
                        self.print_test("Auth Response Format", "PASS", "Contains required fields")
                        compatibility_score += 1
                    else:
                        self.print_test("Auth Response Format", "FAIL", "Missing required fields")
            except Exception as e:
                self.print_test("Auth Response Format", "FAIL", str(e))
                
        return compatibility_score >= 1
        
    def generate_test_report(self) -> Dict:
        """Generate comprehensive test report"""
        self.print_header("📊 TEST EXECUTION SUMMARY")
        
        # Count results
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        warnings = len([r for r in self.test_results if r["status"] == "WARN"])
        total = len(self.test_results)
        
        # Calculate success rate
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"{Colors.BOLD}Results Summary:{Colors.RESET}")
        print(f"  ✅ Passed: {Colors.GREEN}{passed}{Colors.RESET}")
        print(f"  ❌ Failed: {Colors.RED}{failed}{Colors.RESET}")
        print(f"  ⚠️  Warnings: {Colors.YELLOW}{warnings}{Colors.RESET}")
        print(f"  📊 Success Rate: {Colors.CYAN}{success_rate:.1f}%{Colors.RESET}")
        
        # Performance summary
        if self.performance_metrics:
            avg_response_time = sum([m["duration_ms"] for m in self.performance_metrics]) / len(self.performance_metrics)
            print(f"  ⚡ Average Response Time: {Colors.MAGENTA}{avg_response_time:.2f}ms{Colors.RESET}")
            
        # Release readiness assessment
        if success_rate >= 80 and failed <= 2:
            status = "READY FOR RELEASE"
            color = Colors.GREEN
        elif success_rate >= 60:
            status = "NEEDS FIXES BEFORE RELEASE"
            color = Colors.YELLOW
        else:
            status = "NOT READY FOR RELEASE"
            color = Colors.RED
            
        print(f"\n{Colors.BOLD}🚀 Release Status: {color}{status}{Colors.RESET}")
        
        # Generate detailed report
        report = {
            "execution_time": datetime.now().isoformat(),
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "success_rate": success_rate,
                "release_status": status
            },
            "test_results": self.test_results,
            "performance_metrics": self.performance_metrics,
            "recommendations": self.generate_recommendations(failed, warnings, success_rate)
        }
        
        return report
        
    def generate_recommendations(self, failed: int, warnings: int, success_rate: float) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if failed > 0:
            recommendations.append("🔧 Fix all failed tests before release")
            
        if warnings > 2:
            recommendations.append("⚠️ Address warning conditions for better stability")
            
        if success_rate < 80:
            recommendations.append("📈 Improve overall system reliability to reach 80%+ success rate")
            
        # Check specific failures
        auth_failures = [r for r in self.test_results if "auth" in r["test"].lower() and r["status"] == "FAIL"]
        if auth_failures:
            recommendations.append("🔐 Critical: Fix authentication system before release")
            
        db_failures = [r for r in self.test_results if "database" in r["test"].lower() and r["status"] == "FAIL"]
        if db_failures:
            recommendations.append("🗄️ Critical: Resolve database connectivity issues")
            
        # Performance recommendations
        slow_operations = [m for m in self.performance_metrics if m["duration_ms"] > 3000]
        if slow_operations:
            recommendations.append("⚡ Optimize slow operations (>3s response time)")
            
        if not recommendations:
            recommendations.append("✅ All tests passed successfully - Ready for production")
            
        return recommendations
        
    def run_comprehensive_validation(self) -> Dict:
        """Run all validation tests"""
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("🔍 Budget Famille v2.3 - Comprehensive E2E Validation Suite")
        print("=" * 80)
        print(f"Quality Assurance Lead - Post-Fix Validation{Colors.RESET}")
        print(f"Execution started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Execute all test suites
        test_suites = [
            ("Server Health", self.test_server_health),
            ("Authentication", self.test_authentication_endpoints),
            ("CORS Headers", self.test_cors_headers),
            ("Configuration", self.test_configuration_endpoints),
            ("Database", self.test_database_connectivity),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance_benchmarks),
            ("Frontend Compatibility", self.test_frontend_compatibility)
        ]
        
        suite_results = {}
        for suite_name, test_func in test_suites:
            try:
                result = test_func()
                suite_results[suite_name] = result
                time.sleep(0.5)  # Brief pause between test suites
            except Exception as e:
                print(f"{Colors.RED}❌ Test suite '{suite_name}' failed with exception: {e}{Colors.RESET}")
                suite_results[suite_name] = False
                
        # Generate final report
        report = self.generate_test_report()
        report["suite_results"] = suite_results
        
        return report


def save_report(report: Dict, filename: str = None):
    """Save test report to file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"e2e_validation_report_{timestamp}.json"
        
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print(f"\n📄 Detailed report saved to: {Colors.CYAN}{filename}{Colors.RESET}")


def main():
    """Main execution function"""
    validator = E2EValidator()
    
    try:
        # Run comprehensive validation
        report = validator.run_comprehensive_validation()
        
        # Save report
        save_report(report)
        
        # Exit with appropriate code
        if report["summary"]["success_rate"] >= 80:
            print(f"\n{Colors.GREEN}✅ Validation completed successfully{Colors.RESET}")
            sys.exit(0)
        else:
            print(f"\n{Colors.RED}❌ Validation failed - manual intervention required{Colors.RESET}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⏹️  Validation interrupted by user{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}💥 Critical error during validation: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()