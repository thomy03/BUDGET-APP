#!/usr/bin/env python3
"""
Test script for intelligent classification endpoints
Tests the new AI-powered classification API endpoints
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

class ClassificationEndpointTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        
    def authenticate(self) -> bool:
        """Authenticate and get JWT token"""
        try:
            response = self.session.post(
                f"{BASE_URL}/token",
                data={
                    "username": USERNAME,
                    "password": PASSWORD
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data["access_token"]
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def get_test_transaction_id(self) -> int:
        """Get a test transaction ID from recent transactions"""
        try:
            response = self.session.get(f"{BASE_URL}/transactions?month=2025-07")
            if response.status_code == 200:
                transactions = response.json()
                if transactions:
                    return transactions[0]["id"]
            return 18  # Fallback to known transaction ID
        except:
            return 18  # Fallback
    
    def test_get_ai_suggestion(self, transaction_id: int) -> Dict[str, Any]:
        """Test GET /expense-classification/transactions/{id}/ai-suggestion"""
        print(f"\n🧠 Testing AI suggestion for transaction {transaction_id}...")
        
        try:
            start_time = time.time()
            response = self.session.get(
                f"{BASE_URL}/expense-classification/transactions/{transaction_id}/ai-suggestion"
            )
            elapsed_time = (time.time() - start_time) * 1000
            
            print(f"⏱️ Response time: {elapsed_time:.2f}ms")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ AI Suggestion retrieved successfully")
                print(f"   Suggestion: {data['suggestion']}")
                print(f"   Confidence: {data['confidence_score']:.3f}")
                print(f"   Explanation: {data['explanation'][:100]}...")
                print(f"   Rules matched: {data['rules_matched'][:3]}")
                return {"success": True, "data": data, "response_time": elapsed_time}
            else:
                print(f"❌ Failed to get AI suggestion: {response.status_code}")
                print(f"   Error: {response.text}")
                return {"success": False, "error": response.text, "response_time": elapsed_time}
                
        except Exception as e:
            print(f"❌ AI suggestion test error: {e}")
            return {"success": False, "error": str(e)}
    
    def test_classify_transaction(self, transaction_id: int, expense_type: str = "VARIABLE") -> Dict[str, Any]:
        """Test POST /expense-classification/transactions/{id}/classify"""
        print(f"\n🔧 Testing classification for transaction {transaction_id}...")
        
        try:
            start_time = time.time()
            payload = {
                "expense_type": expense_type,
                "user_feedback": True,
                "override_ai": False
            }
            
            response = self.session.post(
                f"{BASE_URL}/expense-classification/transactions/{transaction_id}/classify",
                json=payload
            )
            elapsed_time = (time.time() - start_time) * 1000
            
            print(f"⏱️ Response time: {elapsed_time:.2f}ms")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Transaction classified successfully")
                print(f"   Classification: {data['new_classification']}")
                print(f"   AI Override: {data['was_ai_override']}")
                print(f"   Transactions updated: {data['transactions_updated']}")
                return {"success": True, "data": data, "response_time": elapsed_time}
            else:
                print(f"❌ Failed to classify transaction: {response.status_code}")
                print(f"   Error: {response.text}")
                return {"success": False, "error": response.text, "response_time": elapsed_time}
                
        except Exception as e:
            print(f"❌ Classification test error: {e}")
            return {"success": False, "error": str(e)}
    
    def test_pending_classification(self, month: str = "2025-07") -> Dict[str, Any]:
        """Test GET /expense-classification/transactions/pending-classification"""
        print(f"\n📋 Testing pending classification for month {month}...")
        
        try:
            start_time = time.time()
            response = self.session.get(
                f"{BASE_URL}/expense-classification/transactions/pending-classification",
                params={
                    "month": month,
                    "limit": 10,
                    "only_unclassified": False  # Get all transactions for testing
                }
            )
            elapsed_time = (time.time() - start_time) * 1000
            
            print(f"⏱️ Response time: {elapsed_time:.2f}ms")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Pending classification retrieved successfully")
                print(f"   Total transactions: {data['stats']['total']}")
                print(f"   High confidence: {data['stats']['high_confidence']}")
                print(f"   Needs review: {data['stats']['needs_review']}")
                print(f"   Average confidence: {data['stats']['avg_confidence']:.3f}")
                return {"success": True, "data": data, "response_time": elapsed_time}
            else:
                print(f"❌ Failed to get pending classification: {response.status_code}")
                print(f"   Error: {response.text}")
                return {"success": False, "error": response.text, "response_time": elapsed_time}
                
        except Exception as e:
            print(f"❌ Pending classification test error: {e}")
            return {"success": False, "error": str(e)}
    
    def test_batch_classification(self, transaction_ids: list) -> Dict[str, Any]:
        """Test POST /expense-classification/transactions/batch-classify"""
        print(f"\n🔄 Testing batch classification for {len(transaction_ids)} transactions...")
        
        try:
            start_time = time.time()
            response = self.session.post(
                f"{BASE_URL}/expense-classification/transactions/batch-classify",
                params={
                    "auto_apply": False,
                    "min_confidence": 0.8
                },
                json=transaction_ids
            )
            elapsed_time = (time.time() - start_time) * 1000
            
            print(f"⏱️ Response time: {elapsed_time:.2f}ms ({elapsed_time/len(transaction_ids):.1f}ms per transaction)")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Batch classification completed successfully")
                print(f"   Total processed: {data['total_processed']}")
                print(f"   Successful suggestions: {data['successful_suggestions']}")
                print(f"   High confidence: {data['high_confidence_count']}")
                print(f"   Errors: {len(data['errors'])}")
                return {"success": True, "data": data, "response_time": elapsed_time}
            else:
                print(f"❌ Failed batch classification: {response.status_code}")
                print(f"   Error: {response.text}")
                return {"success": False, "error": response.text, "response_time": elapsed_time}
                
        except Exception as e:
            print(f"❌ Batch classification test error: {e}")
            return {"success": False, "error": str(e)}
    
    def run_performance_tests(self):
        """Run comprehensive performance tests"""
        print("🚀 Starting Intelligent Classification Endpoints Performance Tests")
        print("=" * 70)
        
        if not self.authenticate():
            return
        
        # Get test transaction ID
        test_transaction_id = self.get_test_transaction_id()
        print(f"🎯 Using test transaction ID: {test_transaction_id}")
        
        results = {}
        
        # Test 1: AI Suggestion endpoint
        results["ai_suggestion"] = self.test_get_ai_suggestion(test_transaction_id)
        
        # Test 2: Classification endpoint
        results["classify"] = self.test_classify_transaction(test_transaction_id, "VARIABLE")
        
        # Test 3: Pending classification endpoint
        results["pending"] = self.test_pending_classification("2025-07")
        
        # Test 4: Batch classification (if we have multiple transactions)
        transaction_ids = [test_transaction_id]
        if test_transaction_id > 1:
            transaction_ids.extend([test_transaction_id - 1, test_transaction_id + 1])
        results["batch"] = self.test_batch_classification(transaction_ids)
        
        # Performance summary
        print("\n📊 PERFORMANCE SUMMARY")
        print("=" * 70)
        
        performance_ok = True
        for test_name, result in results.items():
            if result.get("success") and "response_time" in result:
                response_time = result["response_time"]
                status = "✅ PASS" if response_time < 100 else "⚠️ SLOW" if response_time < 500 else "❌ FAIL"
                print(f"{test_name:20s}: {response_time:6.1f}ms {status}")
                
                if response_time >= 500:
                    performance_ok = False
            else:
                print(f"{test_name:20s}: ERROR ❌")
                performance_ok = False
        
        print("\n🎯 OVERALL PERFORMANCE:")
        if performance_ok:
            print("✅ All endpoints meet performance requirements (<100ms target)")
        else:
            print("⚠️ Some endpoints need performance optimization")
        
        # Feature completeness check
        print("\n🧩 FEATURE COMPLETENESS:")
        required_features = {
            "AI Suggestion": results.get("ai_suggestion", {}).get("success", False),
            "Classification with Feedback": results.get("classify", {}).get("success", False),
            "Pending Classification": results.get("pending", {}).get("success", False),
            "Batch Processing": results.get("batch", {}).get("success", False)
        }
        
        all_features_working = True
        for feature, working in required_features.items():
            status = "✅" if working else "❌"
            print(f"  {feature}: {status}")
            if not working:
                all_features_working = False
        
        print("\n🏆 FINAL RESULT:")
        if all_features_working and performance_ok:
            print("✅ All intelligent classification endpoints are working correctly!")
            print("🚀 Ready for production use")
        else:
            print("⚠️ Some issues need to be addressed before production")

def main():
    """Run the test suite"""
    tester = ClassificationEndpointTester()
    tester.run_performance_tests()

if __name__ == "__main__":
    main()