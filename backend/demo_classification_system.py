#!/usr/bin/env python3
"""
Demo script for Intelligent Expense Classification System
Tests the ML classification endpoints and showcases functionality
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

class ClassificationDemo:
    """Demo class for testing the ML classification system"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.headers = {}
    
    def authenticate(self) -> bool:
        """Authenticate and get access token"""
        try:
            auth_data = {
                "username": USERNAME,
                "password": PASSWORD
            }
            
            response = requests.post(
                f"{self.base_url}/token",
                data=auth_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data["access_token"]
                self.headers = {"Authorization": f"Bearer {self.token}"}
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def test_single_classification(self, tag_name: str, amount: float = 50.0, description: str = "") -> Dict[str, Any]:
        """Test single tag classification"""
        try:
            request_data = {
                "tag_name": tag_name,
                "transaction_amount": amount,
                "transaction_description": description
            }
            
            response = requests.post(
                f"{self.base_url}/classification/suggest",
                json=request_data,
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"🔍 Classification for '{tag_name}':")
                print(f"   Type: {result['expense_type']}")
                print(f"   Confidence: {result['confidence']:.1%}")
                print(f"   Reason: {result['primary_reason']}")
                if result['keyword_matches']:
                    print(f"   Keywords: {', '.join(result['keyword_matches'][:3])}")
                print()
                return result
            else:
                print(f"❌ Classification failed for '{tag_name}': {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Error classifying '{tag_name}': {e}")
            return {}
    
    def test_batch_classification(self, tag_names: list) -> Dict[str, Any]:
        """Test batch classification"""
        try:
            request_data = {"tag_names": tag_names}
            
            response = requests.post(
                f"{self.base_url}/classification/batch",
                json=request_data,
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print("📦 Batch Classification Results:")
                
                for tag_name, classification in result['results'].items():
                    print(f"   {tag_name}: {classification['expense_type']} ({classification['confidence']:.1%})")
                
                print(f"\n📊 Summary:")
                summary = result['summary']
                print(f"   Total: {summary['total_tags']}")
                print(f"   Fixed: {summary['fixed_classified']}")
                print(f"   Variable: {summary['variable_classified']}")
                print(f"   Avg Confidence: {summary['average_confidence']:.1%}")
                print()
                
                return result
            else:
                print(f"❌ Batch classification failed: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Batch classification error: {e}")
            return {}
    
    def test_get_stats(self) -> Dict[str, Any]:
        """Get classification system statistics"""
        try:
            response = requests.get(
                f"{self.base_url}/classification/stats",
                headers=self.headers
            )
            
            if response.status_code == 200:
                stats = response.json()
                print("📈 System Statistics:")
                print(f"   Total classified transactions: {stats['total_classified']}")
                print(f"   Type distribution: {stats['type_distribution']}")
                print(f"   Model version: {stats['ml_model_version']}")
                print(f"   Feature weights: {stats['feature_weights']}")
                print()
                return stats
            else:
                print(f"❌ Stats request failed: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Stats error: {e}")
            return {}
    
    def test_analyze_existing_tags(self, limit: int = 20) -> Dict[str, Any]:
        """Analyze existing tags in the system"""
        try:
            response = requests.get(
                f"{self.base_url}/classification/tags-analysis?limit={limit}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                analysis = response.json()
                print("🔍 Existing Tags Analysis:")
                print(f"   Tags analyzed: {analysis['tags_analyzed']}")
                
                summary = analysis['summary']
                print(f"   High confidence FIXED: {summary['fixed_count']}")
                print(f"   High confidence VARIABLE: {summary['variable_count']}")
                print(f"   Uncertain classifications: {summary['uncertain_count']}")
                print(f"   Average confidence: {summary['average_confidence']:.1%}")
                
                # Show top fixed tags
                if analysis['high_confidence_fixed']:
                    print(f"\n   🔒 Top FIXED tags:")
                    for tag in analysis['high_confidence_fixed'][:5]:
                        print(f"      {tag['tag_name']}: {tag['confidence']:.1%}")
                
                # Show top variable tags  
                if analysis['high_confidence_variable']:
                    print(f"\n   🔄 Top VARIABLE tags:")
                    for tag in analysis['high_confidence_variable'][:5]:
                        print(f"      {tag['tag_name']}: {tag['confidence']:.1%}")
                
                print()
                return analysis
            else:
                print(f"❌ Tag analysis failed: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Tag analysis error: {e}")
            return {}
    
    def test_performance_evaluation(self, sample_size: int = 50) -> Dict[str, Any]:
        """Test system performance evaluation"""
        try:
            response = requests.get(
                f"{self.base_url}/classification/performance?sample_size={sample_size}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                performance = response.json()
                print("🎯 Performance Evaluation:")
                print(f"   Sample size: {performance['sample_size']}")
                print(f"   Accuracy: {performance['accuracy']:.1%}")
                print(f"   Precision: {performance['precision']:.1%}")
                print(f"   Recall: {performance['recall']:.1%}")
                print(f"   F1-Score: {performance['f1_score']:.3f}")
                print(f"   False Positive Rate: {performance['false_positive_rate']:.1%}")
                print(f"   Performance Grade: {performance['performance_grade']}")
                
                targets_met = performance['meets_targets']
                status = "✅ MEETS TARGETS" if targets_met else "⚠️ NEEDS IMPROVEMENT"
                print(f"   Target compliance: {status}")
                print()
                
                return performance
            else:
                print(f"❌ Performance evaluation failed: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Performance evaluation error: {e}")
            return {}
    
    def demo_common_scenarios(self):
        """Demo common classification scenarios"""
        print("🎭 Common Classification Scenarios Demo\n")
        
        # Scenario 1: Obvious fixed expenses
        print("📌 Scenario 1: Obvious Fixed Expenses")
        fixed_examples = [
            ("netflix", 9.99, "NETFLIX PREMIUM"),
            ("edf", 85.50, "EDF FACTURE ELECTRICITE"),
            ("orange", 39.99, "ORANGE INTERNET BOX"),
            ("assurance", 125.00, "MAIF ASSURANCE AUTO")
        ]
        
        for tag, amount, desc in fixed_examples:
            self.test_single_classification(tag, amount, desc)
            time.sleep(0.5)
        
        # Scenario 2: Obvious variable expenses
        print("📌 Scenario 2: Obvious Variable Expenses")
        variable_examples = [
            ("restaurant", 45.80, "RESTAURANT LA BONNE FOURCHETTE"),
            ("courses", 127.35, "CARREFOUR COURSES ALIMENTAIRES"),
            ("carburant", 65.00, "TOTAL STATION SERVICE"),
            ("pharmacie", 22.50, "PHARMACIE CENTRALE MEDICAMENTS")
        ]
        
        for tag, amount, desc in variable_examples:
            self.test_single_classification(tag, amount, desc)
            time.sleep(0.5)
        
        # Scenario 3: Ambiguous cases
        print("📌 Scenario 3: Ambiguous Cases")
        ambiguous_examples = [
            ("transport", 50.00, "TRANSPORT OCCASIONNEL"),
            ("service", 30.00, "SERVICE DIVERS"),
            ("maintenance", 85.00, "MAINTENANCE EQUIPEMENT")
        ]
        
        for tag, amount, desc in ambiguous_examples:
            self.test_single_classification(tag, amount, desc)
            time.sleep(0.5)
    
    def run_comprehensive_demo(self):
        """Run comprehensive demo of the classification system"""
        print("🚀 Intelligent Expense Classification System Demo")
        print("=" * 60)
        
        # Authenticate
        if not self.authenticate():
            return False
        
        # Test single classifications
        print("\n1. Single Tag Classification Tests")
        print("-" * 40)
        
        test_tags = ["netflix", "courses", "edf", "restaurant", "transport"]
        for tag in test_tags:
            self.test_single_classification(tag)
            time.sleep(0.3)
        
        # Test batch classification
        print("2. Batch Classification Test")
        print("-" * 40)
        
        batch_tags = ["netflix", "spotify", "courses", "restaurant", "edf", "orange", "carburant"]
        self.test_batch_classification(batch_tags)
        
        # Get system statistics
        print("3. System Statistics")
        print("-" * 40)
        self.test_get_stats()
        
        # Analyze existing tags
        print("4. Existing Tags Analysis")
        print("-" * 40)
        self.test_analyze_existing_tags()
        
        # Performance evaluation
        print("5. Performance Evaluation")
        print("-" * 40)
        self.test_performance_evaluation()
        
        # Demo common scenarios
        self.demo_common_scenarios()
        
        print("🎉 Demo completed successfully!")
        return True


def main():
    """Main demo function"""
    demo = ClassificationDemo()
    
    try:
        success = demo.run_comprehensive_demo()
        if success:
            print("\n✅ All demo tests completed successfully!")
            print("🔗 Access full API documentation at: http://localhost:8000/docs")
        else:
            print("\n❌ Demo failed - check server connection and authentication")
            
    except KeyboardInterrupt:
        print("\n⛔ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")


if __name__ == "__main__":
    main()