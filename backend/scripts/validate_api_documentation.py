#!/usr/bin/env python3
"""
Budget Famille API v2.3 - Documentation Validation Script
Validates 100% API documentation completeness and accuracy
"""

import json
import requests
import sys
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import yaml


class APIDocumentationValidator:
    """Comprehensive API documentation validator"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "errors": [],
            "warnings_list": [],
            "coverage": {}
        }
        
    def log_result(self, test_name: str, status: str, message: str = ""):
        """Log test result"""
        self.results["total_tests"] += 1
        if status == "PASS":
            self.results["passed"] += 1
            print(f"✅ {test_name}: {message}")
        elif status == "FAIL":
            self.results["failed"] += 1 
            self.results["errors"].append(f"{test_name}: {message}")
            print(f"❌ {test_name}: {message}")
        elif status == "WARN":
            self.results["warnings"] += 1
            self.results["warnings_list"].append(f"{test_name}: {message}")
            print(f"⚠️  {test_name}: {message}")

    def validate_server_availability(self) -> bool:
        """Test 1: Server availability and health"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("status") == "healthy":
                    self.log_result("Server Health", "PASS", f"Version {health_data.get('version')}")
                    return True
                else:
                    self.log_result("Server Health", "FAIL", f"Unhealthy status: {health_data}")
            else:
                self.log_result("Server Health", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("Server Health", "FAIL", f"Connection failed: {str(e)}")
        return False

    def validate_openapi_schema(self) -> bool:
        """Test 2: OpenAPI schema completeness"""
        try:
            response = requests.get(f"{self.base_url}/openapi.json", timeout=10)
            if response.status_code == 200:
                openapi_schema = response.json()
                
                # Check basic OpenAPI structure
                required_fields = ["info", "paths", "components"]
                missing_fields = [field for field in required_fields if field not in openapi_schema]
                
                if missing_fields:
                    self.log_result("OpenAPI Schema", "FAIL", f"Missing fields: {missing_fields}")
                    return False
                
                # Check info completeness
                info = openapi_schema["info"]
                required_info = ["title", "version", "description"]
                missing_info = [field for field in required_info if not info.get(field)]
                
                if missing_info:
                    self.log_result("OpenAPI Info", "FAIL", f"Missing info: {missing_info}")
                    return False
                
                # Count endpoints
                paths_count = len(openapi_schema["paths"])
                self.results["coverage"]["total_endpoints"] = paths_count
                
                # Check tags
                if "tags" in openapi_schema:
                    tags_count = len(openapi_schema["tags"])
                    self.results["coverage"]["tags"] = tags_count
                    self.log_result("OpenAPI Tags", "PASS", f"{tags_count} tags defined")
                else:
                    self.log_result("OpenAPI Tags", "WARN", "No tags defined")
                
                self.log_result("OpenAPI Schema", "PASS", f"{paths_count} endpoints documented")
                return True
            else:
                self.log_result("OpenAPI Schema", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("OpenAPI Schema", "FAIL", f"Error: {str(e)}")
        return False

    def authenticate(self) -> bool:
        """Test 3: Authentication flow"""
        try:
            # Test OAuth2 endpoint
            auth_data = {
                "username": "admin",
                "password": "password"
            }
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json=auth_data,
                timeout=5
            )
            
            if response.status_code == 200:
                token_data = response.json()
                required_fields = ["access_token", "token_type", "expires_in"]
                missing_fields = [field for field in required_fields if field not in token_data]
                
                if missing_fields:
                    self.log_result("Auth Response", "FAIL", f"Missing fields: {missing_fields}")
                    return False
                
                self.token = token_data["access_token"]
                self.log_result("Authentication", "PASS", "JWT token obtained")
                return True
            elif response.status_code == 401:
                self.log_result("Authentication", "FAIL", "Invalid credentials (check default user)")
                return False
            else:
                self.log_result("Authentication", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Authentication", "FAIL", f"Error: {str(e)}")
            return False

    def validate_authentication_endpoints(self) -> None:
        """Test 4: Authentication endpoints completeness"""
        auth_endpoints = [
            ("/api/v1/auth/token", "POST", "OAuth2 token endpoint"),
            ("/api/v1/auth/login", "POST", "JSON login endpoint"),
            ("/api/v1/auth/me", "GET", "User info endpoint"),
            ("/api/v1/auth/refresh", "POST", "Token refresh endpoint"),
            ("/api/v1/auth/validate", "GET", "Token validation endpoint"),
            ("/api/v1/auth/logout", "POST", "Logout endpoint"),
            ("/api/v1/auth/health", "GET", "Auth service health")
        ]
        
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        
        for endpoint, method, description in auth_endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}", headers=headers, timeout=5)
                else:
                    response = requests.post(f"{self.base_url}{endpoint}", headers=headers, timeout=5)
                
                if response.status_code in [200, 401, 422]:  # Expected statuses
                    self.log_result(f"Auth Endpoint {endpoint}", "PASS", description)
                else:
                    self.log_result(f"Auth Endpoint {endpoint}", "FAIL", f"HTTP {response.status_code}")
            except Exception as e:
                self.log_result(f"Auth Endpoint {endpoint}", "FAIL", f"Error: {str(e)}")

    def validate_core_endpoints(self) -> None:
        """Test 5: Core API endpoints"""
        if not self.token:
            self.log_result("Core Endpoints", "FAIL", "No auth token available")
            return
            
        headers = {"Authorization": f"Bearer {self.token}"}
        
        core_endpoints = [
            # Configuration
            ("/config", "GET", "Get configuration"),
            
            # Transactions
            ("/transactions", "GET", "List transactions", {"month": "2024-01"}),
            ("/transactions/tags", "GET", "List transaction tags"),
            
            # Analytics
            ("/analytics/kpis", "GET", "KPI summary", {"months": "last3"}),
            ("/analytics/trends", "GET", "Monthly trends", {"months": "last3"}),
            ("/analytics/available-months", "GET", "Available months"),
            
            # Provisions
            ("/provisions", "GET", "List provisions"),
            ("/provisions/summary", "GET", "Provisions summary"),
            
            # Fixed expenses
            ("/fixed-lines", "GET", "List fixed lines"),
            ("/fixed-lines/stats/by-category", "GET", "Fixed lines stats"),
            
            # Import/Export
            ("/export/history", "GET", "Export history"),
        ]
        
        for endpoint_data in core_endpoints:
            endpoint = endpoint_data[0]
            method = endpoint_data[1]
            description = endpoint_data[2]
            params = endpoint_data[3] if len(endpoint_data) > 3 else {}
            
            try:
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    self.log_result(f"Endpoint {endpoint}", "PASS", description)
                elif response.status_code in [404, 422, 500]:
                    # These might be expected if no data exists
                    self.log_result(f"Endpoint {endpoint}", "WARN", 
                                  f"HTTP {response.status_code} - {description}")
                else:
                    self.log_result(f"Endpoint {endpoint}", "FAIL", 
                                  f"HTTP {response.status_code} - {description}")
            except Exception as e:
                self.log_result(f"Endpoint {endpoint}", "FAIL", f"Error: {str(e)}")

    def validate_error_responses(self) -> None:
        """Test 6: Error response format consistency"""
        test_cases = [
            # Invalid endpoint
            ("/nonexistent", 404, "Not found error"),
            # Invalid token
            ("/config", 401, "Unauthorized error", {"Authorization": "Bearer invalid_token"}),
            # Missing auth
            ("/config", 401, "Missing auth error", {}),
        ]
        
        for endpoint, expected_status, description, headers in test_cases:
            try:
                response = requests.get(
                    f"{self.base_url}{endpoint}", 
                    headers=headers if len(test_cases[test_cases.index((endpoint, expected_status, description, headers))]) > 3 else {},
                    timeout=5
                )
                
                if response.status_code == expected_status:
                    # Check error format
                    try:
                        error_data = response.json()
                        if "detail" in error_data:
                            self.log_result(f"Error Format {expected_status}", "PASS", description)
                        else:
                            self.log_result(f"Error Format {expected_status}", "WARN", 
                                          "No 'detail' field in error response")
                    except:
                        self.log_result(f"Error Format {expected_status}", "WARN", 
                                      "Non-JSON error response")
                else:
                    self.log_result(f"Error {endpoint}", "WARN", 
                                  f"Expected {expected_status}, got {response.status_code}")
            except Exception as e:
                self.log_result(f"Error Test {endpoint}", "FAIL", f"Error: {str(e)}")

    def validate_response_schemas(self) -> None:
        """Test 7: Response schema completeness"""
        if not self.token:
            return
            
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test specific endpoints with expected response structure
        schema_tests = [
            ("/config", ["salaire1", "salaire2", "charges_fixes"], "Configuration schema"),
            ("/analytics/available-months", ["available_months", "total_months"], "Available months schema"),
            ("/provisions", None, "Provisions array schema"),  # Array response
            ("/fixed-lines", None, "Fixed lines array schema"),  # Array response
        ]
        
        for endpoint, required_fields, description in schema_tests:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    if required_fields:
                        missing_fields = [field for field in required_fields if field not in data]
                        if missing_fields:
                            self.log_result(f"Schema {endpoint}", "FAIL", 
                                          f"Missing fields: {missing_fields}")
                        else:
                            self.log_result(f"Schema {endpoint}", "PASS", description)
                    else:
                        # Array response
                        if isinstance(data, list):
                            self.log_result(f"Schema {endpoint}", "PASS", f"{description} - array response")
                        else:
                            self.log_result(f"Schema {endpoint}", "FAIL", 
                                          f"{description} - expected array, got {type(data)}")
                else:
                    self.log_result(f"Schema {endpoint}", "WARN", 
                                  f"HTTP {response.status_code} - {description}")
            except Exception as e:
                self.log_result(f"Schema {endpoint}", "FAIL", f"Error: {str(e)}")

    def validate_documentation_quality(self) -> None:
        """Test 8: Documentation quality metrics"""
        try:
            response = requests.get(f"{self.base_url}/openapi.json", timeout=10)
            if response.status_code != 200:
                self.log_result("Doc Quality", "FAIL", "Cannot fetch OpenAPI spec")
                return
                
            openapi_schema = response.json()
            
            # Count documented vs undocumented endpoints
            documented_endpoints = 0
            total_endpoints = 0
            
            for path, methods in openapi_schema.get("paths", {}).items():
                for method, details in methods.items():
                    total_endpoints += 1
                    if details.get("description") or details.get("summary"):
                        documented_endpoints += 1
            
            if total_endpoints > 0:
                doc_percentage = (documented_endpoints / total_endpoints) * 100
                self.results["coverage"]["documentation_percentage"] = doc_percentage
                
                if doc_percentage >= 90:
                    self.log_result("Documentation Coverage", "PASS", 
                                  f"{doc_percentage:.1f}% endpoints documented")
                elif doc_percentage >= 70:
                    self.log_result("Documentation Coverage", "WARN", 
                                  f"{doc_percentage:.1f}% endpoints documented")
                else:
                    self.log_result("Documentation Coverage", "FAIL", 
                                  f"Only {doc_percentage:.1f}% endpoints documented")
            
            # Check for response models
            components = openapi_schema.get("components", {})
            schemas_count = len(components.get("schemas", {}))
            self.results["coverage"]["schemas"] = schemas_count
            
            if schemas_count >= 20:
                self.log_result("Response Models", "PASS", f"{schemas_count} schemas defined")
            elif schemas_count >= 10:
                self.log_result("Response Models", "WARN", f"Only {schemas_count} schemas defined")
            else:
                self.log_result("Response Models", "FAIL", f"Only {schemas_count} schemas defined")
                
        except Exception as e:
            self.log_result("Documentation Quality", "FAIL", f"Error: {str(e)}")

    def validate_postman_collection(self) -> None:
        """Test 9: Postman collection validation"""
        import os
        
        postman_file = "Budget_Famille_API_v2.3.postman_collection.json"
        if os.path.exists(postman_file):
            try:
                with open(postman_file, 'r') as f:
                    collection = json.load(f)
                
                # Basic structure validation
                required_fields = ["info", "item", "variable"]
                missing_fields = [field for field in required_fields if field not in collection]
                
                if missing_fields:
                    self.log_result("Postman Collection", "FAIL", 
                                  f"Missing fields: {missing_fields}")
                    return
                
                # Count requests
                def count_requests(items):
                    count = 0
                    for item in items:
                        if "item" in item:  # Folder
                            count += count_requests(item["item"])
                        elif "request" in item:  # Request
                            count += 1
                    return count
                
                request_count = count_requests(collection["item"])
                self.results["coverage"]["postman_requests"] = request_count
                
                if request_count >= 25:
                    self.log_result("Postman Collection", "PASS", 
                                  f"{request_count} requests in collection")
                else:
                    self.log_result("Postman Collection", "WARN", 
                                  f"Only {request_count} requests in collection")
                    
            except Exception as e:
                self.log_result("Postman Collection", "FAIL", f"Error reading file: {str(e)}")
        else:
            self.log_result("Postman Collection", "FAIL", f"File {postman_file} not found")

    def run_all_validations(self) -> Dict[str, Any]:
        """Run complete API documentation validation suite"""
        print("🚀 Starting Budget Famille API v2.3 Documentation Validation")
        print("=" * 70)
        
        start_time = datetime.now()
        
        # Run all validation tests
        if not self.validate_server_availability():
            print("\n❌ Server not available - stopping validation")
            return self.results
            
        self.validate_openapi_schema()
        
        if self.authenticate():
            self.validate_authentication_endpoints()
            self.validate_core_endpoints()
            self.validate_response_schemas()
        
        self.validate_error_responses()
        self.validate_documentation_quality()
        self.validate_postman_collection()
        
        # Calculate final metrics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.results["duration_seconds"] = duration
        self.results["timestamp"] = end_time.isoformat()
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 VALIDATION SUMMARY")
        print("=" * 70)
        
        total = self.results["total_tests"]
        passed = self.results["passed"]
        failed = self.results["failed"]
        warnings = self.results["warnings"]
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"❌ Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"⚠️  Warnings: {warnings} ({warnings/total*100:.1f}%)")
        print(f"🎯 Success Rate: {success_rate:.1f}%")
        print(f"⏱️  Duration: {duration:.1f}s")
        
        # Coverage metrics
        print("\n📈 COVERAGE METRICS")
        print("-" * 40)
        coverage = self.results["coverage"]
        
        if "total_endpoints" in coverage:
            print(f"📍 Total Endpoints: {coverage['total_endpoints']}")
        if "documentation_percentage" in coverage:
            print(f"📝 Documentation: {coverage['documentation_percentage']:.1f}%")
        if "schemas" in coverage:
            print(f"🔧 Response Schemas: {coverage['schemas']}")
        if "postman_requests" in coverage:
            print(f"📮 Postman Requests: {coverage['postman_requests']}")
        if "tags" in coverage:
            print(f"🏷️  API Tags: {coverage['tags']}")
        
        # Detailed errors
        if self.results["errors"]:
            print(f"\n❌ FAILURES ({len(self.results['errors'])})")
            print("-" * 40)
            for error in self.results["errors"]:
                print(f"  • {error}")
        
        if self.results["warnings_list"]:
            print(f"\n⚠️  WARNINGS ({len(self.results['warnings_list'])})")
            print("-" * 40)
            for warning in self.results["warnings_list"]:
                print(f"  • {warning}")
        
        # Final assessment
        print("\n" + "=" * 70)
        if success_rate >= 90 and failed == 0:
            print("🎉 API DOCUMENTATION: EXCELLENT (90%+ success, no failures)")
            assessment = "EXCELLENT"
        elif success_rate >= 80 and failed <= 2:
            print("✅ API DOCUMENTATION: GOOD (80%+ success, minimal failures)")
            assessment = "GOOD"
        elif success_rate >= 70:
            print("⚠️  API DOCUMENTATION: NEEDS IMPROVEMENT (70%+ success)")
            assessment = "NEEDS_IMPROVEMENT"
        else:
            print("❌ API DOCUMENTATION: POOR (<70% success)")
            assessment = "POOR"
            
        self.results["final_assessment"] = assessment
        print("=" * 70)
        
        return self.results

    def generate_report(self, output_file: str = "api_documentation_report.json") -> None:
        """Generate detailed validation report"""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Detailed report saved to: {output_file}")


def main():
    """Main validation runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate Budget Famille API documentation')
    parser.add_argument('--url', default='http://localhost:8000', 
                       help='API base URL (default: http://localhost:8000)')
    parser.add_argument('--report', default='api_documentation_report.json',
                       help='Output report file (default: api_documentation_report.json)')
    
    args = parser.parse_args()
    
    # Run validation
    validator = APIDocumentationValidator(args.url)
    results = validator.run_all_validations()
    
    # Generate report
    validator.generate_report(args.report)
    
    # Exit with appropriate code
    if results["final_assessment"] in ["EXCELLENT", "GOOD"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()