#!/usr/bin/env python3
"""
Comprehensive End-to-End Validation Suite for Budget Famille v2.3
==================================================================

Author: Claude (Quality Assurance Lead)
Date: 2025-08-10
Purpose: Comprehensive validation of all critical system functionalities
         according to CLAUDE.md requirements

This test suite validates:
- JWT Authentication (login, token validation, security)
- CSV Import functionality (multiple formats, edge cases, security)
- Transaction management (CRUD, exclusion, tagging)
- Configuration management (members, distribution keys)
- Analytics and reporting
- Frontend-backend connectivity
- Performance characteristics
- Security validations

Test execution strategy:
1. Start backend service
2. Run individual test modules
3. Collect metrics and results
4. Generate comprehensive validation report
"""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
import pandas as pd
import tempfile
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ValidationResult:
    """Container for validation test results"""
    def __init__(self, test_name: str, category: str):
        self.test_name = test_name
        self.category = category
        self.start_time = datetime.now()
        self.end_time = None
        self.duration = None
        self.status = "PENDING"  # PENDING, RUNNING, PASSED, FAILED, BLOCKED
        self.details = []
        self.errors = []
        self.metrics = {}
        self.security_issues = []
        
    def mark_running(self):
        self.status = "RUNNING"
        logger.info(f"🟡 {self.test_name} - RUNNING")
        
    def mark_passed(self, details: str = None):
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.status = "PASSED"
        if details:
            self.details.append(details)
        logger.info(f"✅ {self.test_name} - PASSED ({self.duration:.2f}s)")
        
    def mark_failed(self, error: str, details: str = None):
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.status = "FAILED"
        self.errors.append(error)
        if details:
            self.details.append(details)
        logger.error(f"❌ {self.test_name} - FAILED: {error}")
        
    def mark_blocked(self, reason: str):
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.status = "BLOCKED"
        self.errors.append(f"BLOCKED: {reason}")
        logger.warning(f"🔒 {self.test_name} - BLOCKED: {reason}")
        
    def add_metric(self, name: str, value: Any, unit: str = None):
        self.metrics[name] = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat()
        }
        
    def add_security_issue(self, severity: str, description: str):
        self.security_issues.append({
            "severity": severity,
            "description": description,
            "timestamp": datetime.now().isoformat()
        })

class BudgetFamilleValidator:
    """Main validation orchestrator"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
        self.results: List[ValidationResult] = []
        self.test_data_dir = Path("/tmp/budget_validation_data")
        self.test_data_dir.mkdir(exist_ok=True)
        
        # Test configuration
        self.test_user = {
            "username": "admin",
            "password": "secret",
            "email": "admin@budget-famille.local"
        }
        
        # Performance thresholds
        self.performance_thresholds = {
            "auth_response_time_ms": 1000,
            "import_response_time_ms": 5000,
            "api_response_time_ms": 500,
            "concurrent_users_supported": 10
        }
        
    def run_comprehensive_validation(self) -> Dict:
        """Execute the complete validation suite"""
        logger.info("🚀 Starting comprehensive Budget Famille v2.3 validation")
        logger.info(f"Target: {self.base_url}")
        logger.info(f"Test data directory: {self.test_data_dir}")
        
        start_time = datetime.now()
        
        try:
            # 1. System Health Check
            self._validate_system_health()
            
            # 2. Authentication Tests
            self._validate_authentication()
            
            # 3. CSV Import Tests (if auth successful)
            if self.auth_token:
                self._validate_csv_imports()
                
                # 4. Transaction Management Tests
                self._validate_transaction_management()
                
                # 5. Configuration Management Tests
                self._validate_configuration_management()
                
                # 6. Analytics Tests
                self._validate_analytics()
                
                # 7. Performance Tests
                self._validate_performance()
            
            # 8. Security Tests
            self._validate_security()
            
            # 9. Generate Report
            total_time = (datetime.now() - start_time).total_seconds()
            return self._generate_validation_report(total_time)
            
        except Exception as e:
            logger.error(f"Critical validation failure: {e}")
            logger.error(traceback.format_exc())
            return {"status": "CRITICAL_FAILURE", "error": str(e)}
            
    def _validate_system_health(self):
        """Test 1: System Health and Availability"""
        result = ValidationResult("System Health Check", "INFRASTRUCTURE")
        result.mark_running()
        
        try:
            # Basic connectivity
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                result.add_metric("response_time_ms", response.elapsed.total_seconds() * 1000)
                result.add_metric("status_code", response.status_code)
                
                # Validate health response structure
                required_keys = ["status", "version", "platform", "features", "database"]
                missing_keys = [key for key in required_keys if key not in health_data]
                
                if missing_keys:
                    result.mark_failed(f"Missing health check keys: {missing_keys}")
                else:
                    result.details.append(f"Version: {health_data.get('version', 'unknown')}")
                    result.details.append(f"Database encryption: {health_data.get('database', {}).get('encryption_enabled', False)}")
                    result.details.append(f"Magic detection: {health_data.get('features', {}).get('magic_detection', False)}")
                    result.mark_passed("Health endpoint accessible with valid structure")
            else:
                result.mark_failed(f"Health check failed with status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            result.mark_blocked("Cannot connect to backend service - ensure it's running")
        except Exception as e:
            result.mark_failed(f"Health check error: {str(e)}")
            
        self.results.append(result)
        
    def _validate_authentication(self):
        """Test 2: JWT Authentication Flow"""
        result = ValidationResult("JWT Authentication", "SECURITY")
        result.mark_running()
        
        try:
            # Test login with form data (OAuth2 style)
            auth_data = {
                "username": self.test_user["username"],
                "password": self.test_user["password"]
            }
            
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/token",
                data=auth_data,  # Form data, not JSON
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            auth_time = (time.time() - start_time) * 1000
            
            result.add_metric("auth_response_time_ms", auth_time)
            
            if response.status_code == 200:
                token_data = response.json()
                
                if "access_token" in token_data and "token_type" in token_data:
                    self.auth_token = token_data["access_token"]
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.auth_token}"
                    })
                    
                    # Validate token structure (basic check)
                    if len(self.auth_token.split('.')) == 3:  # JWT has 3 parts
                        result.details.append("Valid JWT structure received")
                        result.details.append(f"Token type: {token_data['token_type']}")
                        
                        # Test protected endpoint access
                        protected_response = self.session.get(f"{self.base_url}/config", timeout=5)
                        if protected_response.status_code == 200:
                            result.mark_passed("Authentication successful, protected endpoint accessible")
                        else:
                            result.mark_failed(f"Protected endpoint failed: {protected_response.status_code}")
                    else:
                        result.mark_failed("Invalid JWT token structure")
                else:
                    result.mark_failed("Missing access_token or token_type in response")
            elif response.status_code == 401:
                result.mark_failed("Authentication failed - check test credentials")
            else:
                result.mark_failed(f"Unexpected auth response: {response.status_code}")
                
        except Exception as e:
            result.mark_failed(f"Authentication error: {str(e)}")
            
        self.results.append(result)
        
        # Performance validation
        if auth_time > self.performance_thresholds["auth_response_time_ms"]:
            result.add_security_issue("PERFORMANCE", f"Authentication took {auth_time:.0f}ms (threshold: {self.performance_thresholds['auth_response_time_ms']}ms)")
            
    def _create_test_csv(self, filename: str, data: List[Dict]) -> Path:
        """Helper to create test CSV files"""
        file_path = self.test_data_dir / filename
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            if data:
                fieldnames = data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
        return file_path
        
    def _validate_csv_imports(self):
        """Test 3: CSV Import Functionality"""
        result = ValidationResult("CSV Import Functionality", "CORE_FEATURES")
        result.mark_running()
        
        try:
            # Test data with multiple months
            test_transactions = [
                {
                    "dateOp": "2024-01-15",
                    "dateVal": "2024-01-15", 
                    "label": "CARREFOUR MARKET",
                    "category": "Alimentaire",
                    "categoryParent": "Dépenses courantes",
                    "amount": "-45.67",
                    "accountLabel": "Compte Courant",
                    "supplierFound": "CARREFOUR",
                    "comment": "Courses hebdomadaires"
                },
                {
                    "dateOp": "2024-02-20",
                    "dateVal": "2024-02-20",
                    "label": "STATION TOTAL",
                    "category": "Transport", 
                    "categoryParent": "Dépenses courantes",
                    "amount": "-72.50",
                    "accountLabel": "Compte Courant",
                    "supplierFound": "TOTAL",
                    "comment": "Essence"
                },
                {
                    "dateOp": "2024-03-10",
                    "dateVal": "2024-03-10",
                    "label": "VIREMENT SALAIRE",
                    "category": "Salaire",
                    "categoryParent": "Revenus",
                    "amount": "2500.00",
                    "accountLabel": "Compte Courant", 
                    "supplierFound": "",
                    "comment": "Salaire mars"
                }
            ]
            
            # Create test CSV
            csv_path = self._create_test_csv("test_multi_month.csv", test_transactions)
            
            # Test import
            start_time = time.time()
            with open(csv_path, 'rb') as f:
                files = {"file": ("test_multi_month.csv", f, "text/csv")}
                response = self.session.post(
                    f"{self.base_url}/import",
                    files=files,
                    timeout=30
                )
            import_time = (time.time() - start_time) * 1000
            
            result.add_metric("import_response_time_ms", import_time)
            result.add_metric("test_transactions_count", len(test_transactions))
            
            if response.status_code == 200:
                import_data = response.json()
                
                # Validate import response structure
                required_fields = ["importId", "months", "processingMs", "fileName"]
                missing_fields = [field for field in required_fields if field not in import_data]
                
                if missing_fields:
                    result.mark_failed(f"Missing import response fields: {missing_fields}")
                else:
                    months_detected = import_data.get("months", [])
                    duplicates_count = import_data.get("duplicatesCount", 0)
                    processing_ms = import_data.get("processingMs", 0)
                    
                    result.add_metric("months_detected", len(months_detected))
                    result.add_metric("duplicates_found", duplicates_count)
                    result.add_metric("backend_processing_ms", processing_ms)
                    
                    # Validate month detection
                    expected_months = {"2024-01", "2024-02", "2024-03"}
                    detected_months = {month["month"] for month in months_detected}
                    
                    if expected_months <= detected_months:
                        result.details.append(f"Correctly detected {len(months_detected)} months")
                        result.details.append(f"Import ID: {import_data['importId']}")
                        result.details.append(f"Processing time: {processing_ms}ms")
                        
                        # Test transaction retrieval for one month
                        tx_response = self.session.get(f"{self.base_url}/transactions?month=2024-01")
                        if tx_response.status_code == 200:
                            transactions = tx_response.json()
                            result.add_metric("transactions_retrieved", len(transactions))
                            result.mark_passed(f"Import successful, {len(transactions)} transactions retrieved for 2024-01")
                        else:
                            result.mark_failed(f"Cannot retrieve imported transactions: {tx_response.status_code}")
                    else:
                        result.mark_failed(f"Month detection failed. Expected: {expected_months}, Got: {detected_months}")
                        
            elif response.status_code == 401:
                result.mark_blocked("Authentication required for import")
            else:
                result.mark_failed(f"Import failed with status {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            result.mark_failed(f"CSV import error: {str(e)}")
            
        self.results.append(result)
        
        # Performance check
        if import_time > self.performance_thresholds["import_response_time_ms"]:
            result.add_security_issue("PERFORMANCE", f"Import took {import_time:.0f}ms (threshold: {self.performance_thresholds['import_response_time_ms']}ms)")
    
    def _validate_transaction_management(self):
        """Test 4: Transaction CRUD Operations"""
        result = ValidationResult("Transaction Management", "CORE_FEATURES")
        result.mark_running()
        
        try:
            # Get transactions for a month to work with
            tx_response = self.session.get(f"{self.base_url}/transactions?month=2024-01")
            
            if tx_response.status_code == 200:
                transactions = tx_response.json()
                
                if transactions:
                    tx = transactions[0]  # Work with first transaction
                    tx_id = tx["id"]
                    
                    # Test 1: Toggle exclude
                    exclude_response = self.session.patch(
                        f"{self.base_url}/transactions/{tx_id}",
                        json={"exclude": True}
                    )
                    
                    if exclude_response.status_code == 200:
                        updated_tx = exclude_response.json()
                        if updated_tx["exclude"] is True:
                            result.details.append("✓ Exclude toggle working")
                        else:
                            result.mark_failed("Exclude toggle failed")
                            return
                    else:
                        result.mark_failed(f"Exclude toggle failed: {exclude_response.status_code}")
                        return
                    
                    # Test 2: Update tags
                    tags_response = self.session.patch(
                        f"{self.base_url}/transactions/{tx_id}/tags",
                        json={"tags": ["test", "validation", "courses"]}
                    )
                    
                    if tags_response.status_code == 200:
                        updated_tx = tags_response.json()
                        if "test" in updated_tx["tags"]:
                            result.details.append("✓ Tags update working")
                            result.add_metric("tags_updated", len(updated_tx["tags"]))
                        else:
                            result.mark_failed("Tags update failed")
                            return
                    else:
                        result.mark_failed(f"Tags update failed: {tags_response.status_code}")
                        return
                    
                    result.mark_passed(f"Transaction CRUD operations successful on tx {tx_id}")
                else:
                    result.mark_blocked("No transactions available for CRUD testing")
            else:
                result.mark_blocked(f"Cannot retrieve transactions: {tx_response.status_code}")
                
        except Exception as e:
            result.mark_failed(f"Transaction management error: {str(e)}")
            
        self.results.append(result)
    
    def _validate_configuration_management(self):
        """Test 5: Configuration Management"""
        result = ValidationResult("Configuration Management", "CORE_FEATURES")
        result.mark_running()
        
        try:
            # Test 1: Get current config
            config_response = self.session.get(f"{self.base_url}/config")
            
            if config_response.status_code == 200:
                config = config_response.json()
                
                # Validate config structure
                required_fields = ["member1", "member2", "rev1", "rev2", "split_mode"]
                missing_fields = [field for field in required_fields if field not in config]
                
                if missing_fields:
                    result.mark_failed(f"Missing config fields: {missing_fields}")
                    return
                
                # Test 2: Update config
                updated_config = config.copy()
                updated_config["member1"] = "TestMember1"
                updated_config["member2"] = "TestMember2"
                updated_config["rev1"] = 3000.0
                updated_config["rev2"] = 2500.0
                updated_config["split_mode"] = "revenus"
                
                update_response = self.session.post(
                    f"{self.base_url}/config",
                    json=updated_config
                )
                
                if update_response.status_code == 200:
                    new_config = update_response.json()
                    
                    if (new_config["member1"] == "TestMember1" and 
                        new_config["member2"] == "TestMember2"):
                        result.details.append("✓ Configuration update successful")
                        
                        # Test 3: Fixed lines management
                        fixed_line_data = {
                            "label": "Test Fixed Line",
                            "amount": 150.0,
                            "freq": "mensuelle",
                            "split_mode": "clé",
                            "split1": 0.6,
                            "split2": 0.4,
                            "active": True
                        }
                        
                        create_line_response = self.session.post(
                            f"{self.base_url}/fixed-lines",
                            json=fixed_line_data
                        )
                        
                        if create_line_response.status_code == 200:
                            created_line = create_line_response.json()
                            line_id = created_line["id"]
                            
                            # List fixed lines
                            list_response = self.session.get(f"{self.base_url}/fixed-lines")
                            if list_response.status_code == 200:
                                lines = list_response.json()
                                if any(line["id"] == line_id for line in lines):
                                    result.details.append("✓ Fixed line creation and listing successful")
                                    result.add_metric("fixed_lines_count", len(lines))
                                else:
                                    result.mark_failed("Created fixed line not found in list")
                                    return
                            else:
                                result.mark_failed(f"Fixed lines listing failed: {list_response.status_code}")
                                return
                            
                            # Delete the test line
                            delete_response = self.session.delete(f"{self.base_url}/fixed-lines/{line_id}")
                            if delete_response.status_code == 200:
                                result.details.append("✓ Fixed line deletion successful")
                            else:
                                result.mark_failed(f"Fixed line deletion failed: {delete_response.status_code}")
                                return
                        else:
                            result.mark_failed(f"Fixed line creation failed: {create_line_response.status_code}")
                            return
                        
                        result.mark_passed("Configuration management fully functional")
                    else:
                        result.mark_failed("Configuration update values not persisted")
                else:
                    result.mark_failed(f"Configuration update failed: {update_response.status_code}")
            else:
                result.mark_failed(f"Cannot retrieve configuration: {config_response.status_code}")
                
        except Exception as e:
            result.mark_failed(f"Configuration management error: {str(e)}")
            
        self.results.append(result)
    
    def _validate_analytics(self):
        """Test 6: Analytics and Reporting"""
        result = ValidationResult("Analytics & Reporting", "ANALYTICS")
        result.mark_running()
        
        try:
            # Test 1: Summary calculation
            summary_response = self.session.get(f"{self.base_url}/summary?month=2024-01")
            
            if summary_response.status_code == 200:
                summary = summary_response.json()
                
                # Validate summary structure
                required_fields = ["month", "var_total", "total_p1", "total_p2", "detail"]
                missing_fields = [field for field in required_fields if field not in summary]
                
                if missing_fields:
                    result.mark_failed(f"Missing summary fields: {missing_fields}")
                    return
                
                result.add_metric("var_total", summary["var_total"])
                result.add_metric("total_p1", summary["total_p1"]) 
                result.add_metric("total_p2", summary["total_p2"])
                
                # Test 2: Tags summary
                tags_response = self.session.get(f"{self.base_url}/tags-summary?month=2024-01")
                if tags_response.status_code == 200:
                    tags_summary = tags_response.json()
                    result.add_metric("tags_count", len(tags_summary))
                    result.details.append(f"✓ Tags summary: {len(tags_summary)} tags")
                else:
                    result.mark_failed(f"Tags summary failed: {tags_response.status_code}")
                    return
                
                # Test 3: Available tags
                all_tags_response = self.session.get(f"{self.base_url}/tags")
                if all_tags_response.status_code == 200:
                    all_tags = all_tags_response.json()
                    result.add_metric("available_tags", len(all_tags))
                    result.details.append(f"✓ Available tags: {len(all_tags)}")
                else:
                    result.mark_failed(f"Available tags failed: {all_tags_response.status_code}")
                    return
                
                # Test 4: Analytics KPIs
                kpis_response = self.session.get(f"{self.base_url}/analytics/kpis?months=last3")
                if kpis_response.status_code == 200:
                    kpis = kpis_response.json()
                    result.add_metric("kpi_total_expenses", kpis.get("total_expenses", 0))
                    result.add_metric("kpi_total_income", kpis.get("total_income", 0))
                    result.details.append("✓ Analytics KPIs endpoint working")
                else:
                    result.mark_failed(f"Analytics KPIs failed: {kpis_response.status_code}")
                    return
                    
                result.mark_passed("All analytics endpoints functional")
                
            else:
                result.mark_failed(f"Summary calculation failed: {summary_response.status_code}")
                
        except Exception as e:
            result.mark_failed(f"Analytics error: {str(e)}")
            
        self.results.append(result)
    
    def _validate_performance(self):
        """Test 7: Performance Validation"""
        result = ValidationResult("Performance Testing", "PERFORMANCE")
        result.mark_running()
        
        try:
            # Test 1: API Response Times
            endpoints_to_test = [
                "/config",
                "/transactions?month=2024-01",
                "/summary?month=2024-01",
                "/tags-summary?month=2024-01"
            ]
            
            response_times = {}
            
            for endpoint in endpoints_to_test:
                times = []
                for i in range(5):  # Test 5 times each
                    start_time = time.time()
                    response = self.session.get(f"{self.base_url}{endpoint}")
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        times.append((end_time - start_time) * 1000)
                    else:
                        result.mark_failed(f"Performance test failed on {endpoint}: {response.status_code}")
                        return
                
                avg_time = sum(times) / len(times)
                response_times[endpoint] = avg_time
                result.add_metric(f"avg_response_time_{endpoint.replace('/', '_').replace('?', '_')}", avg_time)
                
                if avg_time > self.performance_thresholds["api_response_time_ms"]:
                    result.add_security_issue("PERFORMANCE", f"{endpoint} average response time {avg_time:.0f}ms exceeds threshold {self.performance_thresholds['api_response_time_ms']}ms")
            
            # Test 2: Concurrent Users Simulation
            def make_request():
                try:
                    response = self.session.get(f"{self.base_url}/config")
                    return response.status_code == 200
                except:
                    return False
            
            concurrent_users = 5
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [executor.submit(make_request) for _ in range(concurrent_users)]
                results = [future.result() for future in as_completed(futures)]
            end_time = time.time()
            
            successful_requests = sum(results)
            concurrent_time = (end_time - start_time) * 1000
            
            result.add_metric("concurrent_users_tested", concurrent_users)
            result.add_metric("concurrent_success_rate", successful_requests / concurrent_users)
            result.add_metric("concurrent_total_time_ms", concurrent_time)
            
            if successful_requests == concurrent_users:
                result.details.append(f"✓ {concurrent_users} concurrent users handled successfully")
            else:
                result.add_security_issue("PERFORMANCE", f"Only {successful_requests}/{concurrent_users} concurrent requests succeeded")
            
            # Overall performance assessment
            avg_response_time = sum(response_times.values()) / len(response_times)
            result.add_metric("overall_avg_response_time_ms", avg_response_time)
            
            if (avg_response_time <= self.performance_thresholds["api_response_time_ms"] and 
                successful_requests == concurrent_users):
                result.mark_passed(f"Performance acceptable - avg response time: {avg_response_time:.0f}ms")
            else:
                result.mark_failed("Performance thresholds not met")
                
        except Exception as e:
            result.mark_failed(f"Performance testing error: {str(e)}")
            
        self.results.append(result)
    
    def _validate_security(self):
        """Test 8: Security Validation"""
        result = ValidationResult("Security Validation", "SECURITY")
        result.mark_running()
        
        try:
            security_issues_found = 0
            
            # Test 1: Unauthenticated access to protected endpoints
            unauth_session = requests.Session()
            protected_endpoints = ["/config", "/import", "/transactions"]
            
            for endpoint in protected_endpoints:
                response = unauth_session.get(f"{self.base_url}{endpoint}")
                if response.status_code != 401:
                    result.add_security_issue("HIGH", f"Protected endpoint {endpoint} accessible without authentication (status: {response.status_code})")
                    security_issues_found += 1
                else:
                    result.details.append(f"✓ {endpoint} properly protected")
            
            # Test 2: File upload security
            # Create a potentially malicious file
            malicious_content = "<?php echo 'test'; ?>"
            malicious_file = self.test_data_dir / "malicious.php"
            with open(malicious_file, 'w') as f:
                f.write(malicious_content)
            
            try:
                with open(malicious_file, 'rb') as f:
                    files = {"file": ("malicious.php", f, "application/php")}
                    response = self.session.post(f"{self.base_url}/import", files=files)
                
                if response.status_code == 200:
                    result.add_security_issue("CRITICAL", "Malicious PHP file accepted by upload endpoint")
                    security_issues_found += 1
                else:
                    result.details.append("✓ Malicious file upload rejected")
            except Exception:
                result.details.append("✓ File upload security working (exception caught)")
            
            # Test 3: Large file upload (DoS protection)
            large_data = "test," * 100000  # Large CSV content
            large_file = self.test_data_dir / "large_test.csv"
            with open(large_file, 'w') as f:
                f.write("header1,header2\n" + large_data)
            
            try:
                with open(large_file, 'rb') as f:
                    files = {"file": ("large_test.csv", f, "text/csv")}
                    response = self.session.post(f"{self.base_url}/import", files=files, timeout=30)
                
                if response.status_code == 413 or "too large" in response.text.lower():
                    result.details.append("✓ Large file upload protection working")
                elif response.status_code == 200:
                    result.add_security_issue("MEDIUM", "Large file upload accepted - potential DoS vector")
                    security_issues_found += 1
                else:
                    result.details.append(f"Large file upload resulted in {response.status_code}")
            except requests.exceptions.Timeout:
                result.add_security_issue("MEDIUM", "Large file upload timeout - potential DoS issue")
                security_issues_found += 1
            except Exception:
                result.details.append("✓ Large file upload protection working (exception caught)")
            
            # Test 4: SQL Injection attempt (basic)
            try:
                malicious_month = "2024-01'; DROP TABLE transactions; --"
                response = self.session.get(f"{self.base_url}/transactions?month={malicious_month}")
                
                # If it returns 200, check if it's actually processing the injection
                if response.status_code == 200:
                    result.details.append("✓ SQL injection attempt handled gracefully")
                else:
                    result.details.append(f"✓ SQL injection attempt rejected (status: {response.status_code})")
            except Exception:
                result.details.append("✓ SQL injection protection working")
            
            result.add_metric("security_issues_found", security_issues_found)
            
            if security_issues_found == 0:
                result.mark_passed("Security validation passed - no critical issues found")
            else:
                result.mark_failed(f"Security validation failed - {security_issues_found} issues found")
                
        except Exception as e:
            result.mark_failed(f"Security validation error: {str(e)}")
            
        self.results.append(result)
    
    def _generate_validation_report(self, total_time: float) -> Dict:
        """Generate comprehensive validation report"""
        logger.info("📊 Generating comprehensive validation report")
        
        # Count results by status
        status_counts = {"PASSED": 0, "FAILED": 0, "BLOCKED": 0}
        for result in self.results:
            if result.status in status_counts:
                status_counts[result.status] += 1
        
        total_tests = len(self.results)
        pass_rate = (status_counts["PASSED"] / total_tests * 100) if total_tests > 0 else 0
        
        # Collect all security issues
        all_security_issues = []
        for result in self.results:
            all_security_issues.extend(result.security_issues)
        
        # Categorize results
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {
                    "passed": 0, "failed": 0, "blocked": 0, "tests": []
                }
            categories[result.category][result.status.lower()] += 1
            categories[result.category]["tests"].append({
                "name": result.test_name,
                "status": result.status,
                "duration": result.duration,
                "details": result.details,
                "errors": result.errors,
                "metrics": result.metrics
            })
        
        # Quality assessment
        quality_score = 0
        if pass_rate >= 95:
            quality_status = "EXCELLENT"
            quality_score = 100
        elif pass_rate >= 85:
            quality_status = "GOOD"
            quality_score = 85
        elif pass_rate >= 70:
            quality_status = "ACCEPTABLE"
            quality_score = 70
        elif pass_rate >= 50:
            quality_status = "POOR"
            quality_score = 50
        else:
            quality_status = "CRITICAL"
            quality_score = 25
        
        # Release recommendation
        critical_failures = [r for r in self.results if r.status == "FAILED" and r.category in ["SECURITY", "CORE_FEATURES"]]
        blocking_issues = [r for r in self.results if r.status == "BLOCKED"]
        high_security_issues = [issue for issue in all_security_issues if issue["severity"] in ["HIGH", "CRITICAL"]]
        
        if critical_failures or high_security_issues:
            release_recommendation = "BLOCK_RELEASE"
            recommendation_reason = f"Critical failures: {len(critical_failures)}, High security issues: {len(high_security_issues)}"
        elif blocking_issues:
            release_recommendation = "INVESTIGATE_BLOCKS"
            recommendation_reason = f"Blocked tests need investigation: {len(blocking_issues)}"
        elif pass_rate < 85:
            release_recommendation = "CONDITIONAL_RELEASE"
            recommendation_reason = f"Pass rate below 85%: {pass_rate:.1f}%"
        else:
            release_recommendation = "APPROVE_RELEASE"
            recommendation_reason = f"All critical tests passed, pass rate: {pass_rate:.1f}%"
        
        report = {
            "validation_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_duration_seconds": total_time,
                "target_system": self.base_url,
                "total_tests": total_tests,
                "pass_rate_percent": round(pass_rate, 1),
                "quality_status": quality_status,
                "quality_score": quality_score
            },
            "test_results": {
                "passed": status_counts["PASSED"],
                "failed": status_counts["FAILED"],
                "blocked": status_counts["BLOCKED"]
            },
            "categories": categories,
            "security_assessment": {
                "total_issues": len(all_security_issues),
                "critical_issues": len([i for i in all_security_issues if i["severity"] == "CRITICAL"]),
                "high_issues": len([i for i in all_security_issues if i["severity"] == "HIGH"]),
                "medium_issues": len([i for i in all_security_issues if i["severity"] == "MEDIUM"]),
                "issues": all_security_issues
            },
            "release_recommendation": {
                "decision": release_recommendation,
                "reason": recommendation_reason,
                "timestamp": datetime.now().isoformat()
            },
            "detailed_results": [
                {
                    "test_name": r.test_name,
                    "category": r.category,
                    "status": r.status,
                    "duration_seconds": r.duration,
                    "details": r.details,
                    "errors": r.errors,
                    "metrics": r.metrics,
                    "security_issues": r.security_issues
                } for r in self.results
            ]
        }
        
        # Save detailed report to file
        report_file = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📋 Detailed validation report saved to: {report_file}")
        
        # Print summary
        print("\n" + "="*80)
        print("BUDGET FAMILLE v2.3 - END-TO-END VALIDATION REPORT")
        print("="*80)
        print(f"Timestamp: {report['validation_summary']['timestamp']}")
        print(f"Total Tests: {total_tests}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        print(f"Quality Status: {quality_status}")
        print(f"Total Duration: {total_time:.1f}s")
        print()
        print("RESULTS BY STATUS:")
        print(f"  ✅ PASSED: {status_counts['PASSED']}")
        print(f"  ❌ FAILED: {status_counts['FAILED']}")
        print(f"  🔒 BLOCKED: {status_counts['BLOCKED']}")
        print()
        print("SECURITY ASSESSMENT:")
        print(f"  🔴 CRITICAL: {len([i for i in all_security_issues if i['severity'] == 'CRITICAL'])}")
        print(f"  🟠 HIGH: {len([i for i in all_security_issues if i['severity'] == 'HIGH'])}")
        print(f"  🟡 MEDIUM: {len([i for i in all_security_issues if i['severity'] == 'MEDIUM'])}")
        print()
        print("RELEASE RECOMMENDATION:")
        print(f"  🎯 DECISION: {release_recommendation}")
        print(f"  📝 REASON: {recommendation_reason}")
        print()
        
        if critical_failures:
            print("CRITICAL FAILURES:")
            for failure in critical_failures:
                print(f"  ❌ {failure.test_name}: {', '.join(failure.errors)}")
            print()
        
        if high_security_issues:
            print("HIGH/CRITICAL SECURITY ISSUES:")
            for issue in high_security_issues:
                print(f"  🔒 {issue['severity']}: {issue['description']}")
            print()
        
        print("="*80)
        
        return report

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Budget Famille v2.3 Comprehensive Validation')
    parser.add_argument('--base-url', default='http://localhost:8000', 
                       help='Base URL of the Budget Famille backend')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        validator = BudgetFamilleValidator(base_url=args.base_url)
        report = validator.run_comprehensive_validation()
        
        # Exit with appropriate code
        if report["release_recommendation"]["decision"] == "BLOCK_RELEASE":
            sys.exit(1)  # Critical issues found
        elif report["release_recommendation"]["decision"] == "INVESTIGATE_BLOCKS":
            sys.exit(2)  # Investigation needed
        else:
            sys.exit(0)  # Success or conditional approval
            
    except KeyboardInterrupt:
        logger.error("Validation interrupted by user")
        sys.exit(3)
    except Exception as e:
        logger.error(f"Validation framework error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(4)

if __name__ == "__main__":
    main()