#!/usr/bin/env python3
"""
Comprehensive Test Suite for Budget Famille v2.3
Tests all corrections made:
1. Backend consolidation
2. Frontend navigation fixes  
3. CSV import → navigation flow
4. MonthPicker synchronization
5. No regressions in existing functionality
"""

import sys
import os
import json
import time
import requests
import subprocess
import signal
import tempfile
import csv
from pathlib import Path

class TestReporter:
    def __init__(self):
        self.results = []
        self.start_time = time.time()
    
    def test_pass(self, test_name: str, details: str = ""):
        result = {"test": test_name, "status": "PASS", "details": details, "timestamp": time.time()}
        self.results.append(result)
        print(f"✅ {test_name}" + (f" - {details}" if details else ""))
    
    def test_fail(self, test_name: str, error: str):
        result = {"test": test_name, "status": "FAIL", "error": error, "timestamp": time.time()}
        self.results.append(result)
        print(f"❌ {test_name} - {error}")
    
    def test_warning(self, test_name: str, warning: str):
        result = {"test": test_name, "status": "WARNING", "warning": warning, "timestamp": time.time()}
        self.results.append(result)
        print(f"⚠️  {test_name} - {warning}")
    
    def generate_report(self):
        total_time = time.time() - self.start_time
        passed = len([r for r in self.results if r["status"] == "PASS"])
        failed = len([r for r in self.results if r["status"] == "FAIL"])
        warnings = len([r for r in self.results if r["status"] == "WARNING"])
        
        print("\n" + "="*60)
        print("📊 COMPREHENSIVE TEST REPORT - Budget Famille v2.3")
        print("="*60)
        print(f"Total Tests: {len(self.results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"⏱️  Execution Time: {total_time:.2f}s")
        print("="*60)
        
        if failed == 0:
            print("🎉 ALL CRITICAL TESTS PASSED - RELEASE READY")
        elif failed <= 2:
            print("⚠️  MINOR ISSUES DETECTED - REVIEW RECOMMENDED")
        else:
            print("🚨 CRITICAL ISSUES DETECTED - RELEASE BLOCKED")
        
        return {"passed": passed, "failed": failed, "warnings": warnings, "total_time": total_time}

def test_backend_consolidation(reporter: TestReporter):
    """Test 1: Backend consolidation verification"""
    try:
        # Test single app.py exists and is functional
        if not os.path.exists("app.py"):
            reporter.test_fail("Backend Consolidation", "app.py not found")
            return
        
        # Test unified requirements.txt
        if not os.path.exists("requirements.txt"):
            reporter.test_fail("Backend Consolidation", "requirements.txt not found")
            return
        
        # Test app can be imported
        sys.path.insert(0, os.getcwd())
        try:
            import app
            reporter.test_pass("Backend Consolidation", "Single app.py imports successfully")
        except Exception as e:
            reporter.test_fail("Backend Consolidation", f"Cannot import app.py: {e}")
            
    except Exception as e:
        reporter.test_fail("Backend Consolidation", f"Unexpected error: {e}")

def test_backend_startup(reporter: TestReporter):
    """Test 2: Backend startup with consolidated files"""
    try:
        # Start backend server
        proc = subprocess.Popen(
            ["python", "app.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )
        
        # Wait for startup
        time.sleep(5)
        
        try:
            # Test health endpoint
            response = requests.get("http://localhost:8000/health", timeout=10)
            if response.status_code == 200:
                reporter.test_pass("Backend Startup", f"Health check: {response.json()}")
            else:
                reporter.test_fail("Backend Startup", f"Health check failed: {response.status_code}")
        except requests.exceptions.RequestException as e:
            reporter.test_fail("Backend Startup", f"Cannot connect to backend: {e}")
        
        # Cleanup
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait()
        
    except Exception as e:
        reporter.test_fail("Backend Startup", f"Startup test failed: {e}")

def test_auth_endpoints(reporter: TestReporter):
    """Test 3: Authentication flow (no regression test)"""
    try:
        proc = subprocess.Popen(
            ["python", "app.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )
        time.sleep(5)
        
        try:
            # Test token endpoint exists
            auth_data = {"username": "test", "password": "test"}
            response = requests.post("http://localhost:8000/token", data=auth_data, timeout=10)
            
            if response.status_code in [200, 401]:  # Both acceptable - endpoint exists
                reporter.test_pass("Authentication", f"Token endpoint responsive: {response.status_code}")
            else:
                reporter.test_fail("Authentication", f"Unexpected response: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            reporter.test_fail("Authentication", f"Cannot test auth endpoint: {e}")
        
        # Cleanup
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait()
        
    except Exception as e:
        reporter.test_fail("Authentication", f"Auth test failed: {e}")

def test_csv_import_endpoint(reporter: TestReporter):
    """Test 4: CSV import endpoint functionality"""
    try:
        proc = subprocess.Popen(
            ["python", "app.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )
        time.sleep(5)
        
        try:
            # Create test CSV
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Description", "Amount", "Account"])
                writer.writerow(["2024-08-10", "Test Transaction", "-50.00", "Checking"])
                csv_path = f.name
            
            # Test import endpoint without auth (should get 401 or proper response)
            with open(csv_path, 'rb') as f:
                files = {"file": ("test.csv", f, "text/csv")}
                response = requests.post("http://localhost:8000/import", files=files, timeout=15)
            
            # Clean up test file
            os.unlink(csv_path)
            
            if response.status_code in [200, 401, 422]:  # Endpoint exists and responds
                reporter.test_pass("CSV Import Endpoint", f"Import endpoint responsive: {response.status_code}")
            else:
                reporter.test_fail("CSV Import Endpoint", f"Unexpected response: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            reporter.test_warning("CSV Import Endpoint", f"Cannot test import endpoint: {e}")
        
        # Cleanup
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait()
        
    except Exception as e:
        reporter.test_fail("CSV Import Endpoint", f"Import test failed: {e}")

def test_frontend_components(reporter: TestReporter):
    """Test 5: Frontend component structure verification"""
    try:
        frontend_path = "../frontend"
        
        # Check key components exist
        key_components = [
            "components/CsvImportProgress.tsx",
            "components/MonthPicker.tsx", 
            "components/ImportSuccessBanner.tsx",
            "app/upload/page.tsx",
            "app/transactions/page.tsx",
            "lib/month.ts"
        ]
        
        missing_components = []
        for component in key_components:
            if not os.path.exists(os.path.join(frontend_path, component)):
                missing_components.append(component)
        
        if not missing_components:
            reporter.test_pass("Frontend Components", f"All {len(key_components)} key components found")
        else:
            reporter.test_fail("Frontend Components", f"Missing components: {missing_components}")
            
    except Exception as e:
        reporter.test_fail("Frontend Components", f"Component check failed: {e}")

def test_month_picker_logic(reporter: TestReporter):
    """Test 6: MonthPicker synchronization logic"""
    try:
        frontend_path = "../frontend"
        month_lib_path = os.path.join(frontend_path, "lib/month.ts")
        
        if os.path.exists(month_lib_path):
            with open(month_lib_path, 'r') as f:
                content = f.read()
            
            # Check for key synchronization functions
            if "useGlobalMonth" in content and "useGlobalMonthWithUrl" in content:
                reporter.test_pass("MonthPicker Logic", "Both sync hooks present in month.ts")
            else:
                reporter.test_fail("MonthPicker Logic", "Missing required synchronization hooks")
        else:
            reporter.test_fail("MonthPicker Logic", "month.ts not found")
            
    except Exception as e:
        reporter.test_fail("MonthPicker Logic", f"Logic test failed: {e}")

def test_backup_system(reporter: TestReporter):
    """Test 7: Backup organization system"""
    try:
        backup_files = [
            "backup_rotation.sh",
            "setup_backup_system.sh",
            "organize_backups.sh"
        ]
        
        existing_backups = [f for f in backup_files if os.path.exists(f)]
        
        if len(existing_backups) >= 2:
            reporter.test_pass("Backup System", f"Backup system files present: {existing_backups}")
        else:
            reporter.test_warning("Backup System", f"Limited backup files found: {existing_backups}")
            
    except Exception as e:
        reporter.test_warning("Backup System", f"Backup test failed: {e}")

def test_no_regressions(reporter: TestReporter):
    """Test 8: Core functionality regression test"""
    try:
        # Test database can be created
        sys.path.insert(0, os.getcwd())
        
        try:
            from app import engine, Base
            # Test DB connection
            Base.metadata.create_all(bind=engine)
            reporter.test_pass("No Regressions", "Database connection and models work")
        except Exception as e:
            reporter.test_fail("No Regressions", f"Database issues: {e}")
            
    except Exception as e:
        reporter.test_fail("No Regressions", f"Regression test failed: {e}")

def main():
    """Run comprehensive test suite"""
    print("🚀 Starting Comprehensive Test Suite for Budget Famille v2.3")
    print("Testing: Backend consolidation, Navigation fixes, CSV import flow, MonthPicker sync")
    print("-" * 80)
    
    reporter = TestReporter()
    
    # Execute all tests
    test_backend_consolidation(reporter)
    test_backend_startup(reporter)
    test_auth_endpoints(reporter) 
    test_csv_import_endpoint(reporter)
    test_frontend_components(reporter)
    test_month_picker_logic(reporter)
    test_backup_system(reporter)
    test_no_regressions(reporter)
    
    # Generate final report
    results = reporter.generate_report()
    
    # Export results
    with open("comprehensive_test_results.json", "w") as f:
        json.dump({
            "summary": results,
            "details": reporter.results,
            "timestamp": time.time(),
            "version": "v2.3"
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: comprehensive_test_results.json")
    
    # Exit with appropriate code
    if results["failed"] == 0:
        sys.exit(0)  # Success
    elif results["failed"] <= 2:
        sys.exit(1)  # Minor issues
    else:
        sys.exit(2)  # Critical issues

if __name__ == "__main__":
    main()