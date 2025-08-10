#!/usr/bin/env python3
"""
Post-deployment smoke test for Budget Famille v2.3 CSV import functionality
This test should be run after each deployment to validate critical import paths
"""

import requests
import tempfile
import os
import logging
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImportSmokeTest:
    def __init__(self, base_url="http://127.0.0.1:8000", username="admin", password="secret"):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
        
    def authenticate(self) -> bool:
        """Authenticate and store token"""
        try:
            response = requests.post(
                f"{self.base_url}/token",
                data={"username": self.username, "password": self.password, "grant_type": "password"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=5
            )
            
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                logger.info("✅ Authentication: PASS")
                return True
            else:
                logger.error(f"❌ Authentication: FAIL - Status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication: FAIL - {e}")
            return False
    
    def test_health_endpoint(self) -> bool:
        """Test health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Health check: PASS")
                logger.info(f"   Version: {data.get('version', 'unknown')}")
                return True
            else:
                logger.error(f"❌ Health check: FAIL - Status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Health check: FAIL - {e}")
            return False
            
    def test_french_csv_import(self) -> bool:
        """Test French CSV format import (critical path)"""
        csv_content = """Date,Description,Montant,Compte,Categorie
2024-01-01,Test smoke,-100.00,CHECKING,Test
2024-01-02,Test income,2000.00,CHECKING,Revenus"""
        
        return self._test_csv_import("french_smoke_test.csv", csv_content, "French CSV import")
    
    def test_english_csv_import(self) -> bool:
        """Test English CSV format import (critical path)"""
        csv_content = """dateOp,label,amount,accountLabel,category
2024-01-01,Test smoke,-100.00,CHECKING,Test
2024-01-02,Test income,2000.00,CHECKING,Income"""
        
        return self._test_csv_import("english_smoke_test.csv", csv_content, "English CSV import")
    
    def _test_csv_import(self, filename: str, content: str, test_name: str) -> bool:
        """Helper to test CSV import"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            try:
                with open(temp_path, 'rb') as f:
                    files = {'file': (filename, f, 'text/csv')}
                    headers = {'Authorization': f'Bearer {self.token}'}
                    response = requests.post(
                        f"{self.base_url}/import", 
                        files=files, 
                        headers=headers,
                        timeout=10
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    months_count = len(data.get("months", []))
                    logger.info(f"✅ {test_name}: PASS")
                    logger.info(f"   Import ID: {data.get('importId', 'N/A')[:8]}...")
                    logger.info(f"   Months detected: {months_count}")
                    return True
                else:
                    logger.error(f"❌ {test_name}: FAIL - Status {response.status_code}")
                    try:
                        error_data = response.json()
                        logger.error(f"   Error: {error_data.get('detail', 'Unknown')}")
                    except:
                        logger.error(f"   Raw response: {response.text[:100]}")
                    return False
                    
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"❌ {test_name}: FAIL - {e}")
            return False
    
    def test_edge_cases(self) -> dict:
        """Test edge cases (non-critical but important for monitoring)"""
        results = {}
        
        # Test empty CSV (should fail gracefully)
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write("")
                temp_path = f.name
            
            try:
                with open(temp_path, 'rb') as f:
                    files = {'file': ('empty.csv', f, 'text/csv')}
                    headers = {'Authorization': f'Bearer {self.token}'}
                    response = requests.post(f"{self.base_url}/import", files=files, headers=headers, timeout=5)
                
                # Should fail with 400 - this is expected
                results["empty_csv"] = response.status_code == 400
                logger.info(f"✅ Empty CSV handling: {'PASS' if results['empty_csv'] else 'FAIL'}")
                
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            results["empty_csv"] = False
            logger.error(f"❌ Empty CSV test: FAIL - {e}")
        
        return results
    
    def run_smoke_test(self) -> bool:
        """Run complete smoke test suite"""
        logger.info("🚀 Starting Post-Deployment Smoke Test")
        logger.info(f"📅 Test run: {datetime.now().isoformat()}")
        logger.info(f"🌐 Target URL: {self.base_url}")
        logger.info("=" * 60)
        
        # Critical tests (all must pass)
        critical_tests = [
            ("Authentication", self.authenticate),
            ("Health Endpoint", self.test_health_endpoint),
            ("French CSV Import", self.test_french_csv_import),
            ("English CSV Import", self.test_english_csv_import),
        ]
        
        failed_critical = []
        
        for test_name, test_func in critical_tests:
            if not test_func():
                failed_critical.append(test_name)
        
        # Edge case tests (non-critical)
        logger.info("\n📊 Testing edge cases...")
        edge_results = self.test_edge_cases()
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📋 SMOKE TEST RESULTS")
        logger.info("=" * 60)
        
        if not failed_critical:
            logger.info("🎉 ALL CRITICAL TESTS PASSED")
            logger.info("✅ CSV Import functionality is working correctly")
            logger.info("✅ Ready for production traffic")
            
            # Edge case summary
            edge_passed = sum(1 for v in edge_results.values() if v)
            logger.info(f"📊 Edge cases: {edge_passed}/{len(edge_results)} passed")
            
            return True
        else:
            logger.error("❌ CRITICAL TEST FAILURES DETECTED")
            logger.error("❌ DO NOT PROCEED WITH DEPLOYMENT")
            logger.error(f"   Failed tests: {', '.join(failed_critical)}")
            return False

def main():
    """Main entry point"""
    # Allow custom URL via environment variable
    base_url = os.getenv("SMOKE_TEST_URL", "http://127.0.0.1:8000")
    
    smoke_test = ImportSmokeTest(base_url=base_url)
    success = smoke_test.run_smoke_test()
    
    # Exit with appropriate code for CI/CD
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()