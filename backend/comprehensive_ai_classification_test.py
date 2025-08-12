#!/usr/bin/env python3
"""
COMPREHENSIVE QA VALIDATION FOR AI TRANSACTION CLASSIFICATION
=====================================================

This script performs complete end-to-end validation of the AI classification system
according to our Quality Assurance standards.

Test Coverage:
1. Backend API Endpoints (all critical classification endpoints)
2. ML Engine Performance (confidence scores, response times)
3. Database Integration (transactions, learning feedback)
4. Error Handling and Edge Cases
5. Performance Benchmarks (<100ms target)
"""

import requests
import json
import time
import sys
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

@dataclass
class TestResult:
    """Test result structure for comprehensive reporting"""
    endpoint: str
    test_name: str
    status: str  # PASS, FAIL, WARNING
    response_time_ms: float
    details: Dict[str, Any]
    errors: List[str]

@dataclass
class ValidationReport:
    """Complete validation report"""
    test_results: List[TestResult]
    summary: Dict[str, Any]
    performance_metrics: Dict[str, float]
    recommendations: List[str]

class AIClassificationValidator:
    """Comprehensive validation of AI Classification system"""
    
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.test_results: List[TestResult] = []
        self.performance_metrics: Dict[str, float] = {}
        
    def authenticate(self) -> bool:
        """Authenticate and get JWT token"""
        try:
            print("🔑 Authenticating...")
            response = self.session.post(
                f"{BASE_URL}/token",
                data={"username": USERNAME, "password": PASSWORD},
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
    
    def get_sample_transaction_id(self) -> Optional[int]:
        """Get a sample transaction ID for testing"""
        try:
            response = self.session.get(f"{BASE_URL}/transactions")
            if response.status_code == 200:
                transactions = response.json()
                if transactions and len(transactions) > 0:
                    # Find an expense transaction (negative amount)
                    for tx in transactions[:20]:  # Check first 20
                        if tx.get('amount', 0) < 0:
                            return tx['id']
                    return transactions[0]['id'] if transactions else None
            return None
        except Exception as e:
            print(f"Warning: Could not get sample transaction: {e}")
            return 1  # Fallback to ID 1

    def test_api_endpoint(self, endpoint: str, method: str = "GET", data: Dict = None, 
                         test_name: str = "", expected_fields: List[str] = None) -> TestResult:
        """Generic API endpoint test with performance measurement"""
        
        start_time = time.time()
        errors = []
        details = {}
        status = "FAIL"
        
        try:
            url = f"{BASE_URL}{endpoint}"
            
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response_time = (time.time() - start_time) * 1000
            
            # Basic response validation
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    details['response_data'] = response_data
                    details['status_code'] = response.status_code
                    
                    # Validate expected fields if provided
                    if expected_fields:
                        missing_fields = []
                        if isinstance(response_data, dict):
                            for field in expected_fields:
                                if field not in response_data:
                                    missing_fields.append(field)
                        
                        if missing_fields:
                            errors.append(f"Missing expected fields: {missing_fields}")
                        else:
                            status = "PASS"
                    else:
                        status = "PASS"
                        
                except json.JSONDecodeError:
                    errors.append("Invalid JSON response")
                    details['response_text'] = response.text[:200]
            else:
                errors.append(f"HTTP {response.status_code}: {response.text[:200]}")
                details['status_code'] = response.status_code
                
        except Exception as e:
            errors.append(f"Request failed: {str(e)}")
            response_time = (time.time() - start_time) * 1000
        
        return TestResult(
            endpoint=endpoint,
            test_name=test_name or f"{method} {endpoint}",
            status=status,
            response_time_ms=round(response_time, 1),
            details=details,
            errors=errors
        )

    def validate_backend_endpoints(self) -> None:
        """Test all critical backend AI classification endpoints"""
        
        print("\n🔧 BACKEND API ENDPOINTS VALIDATION")
        print("=" * 50)
        
        # Test 1: Classification stats endpoint
        result = self.test_api_endpoint(
            "/expense-classification/stats",
            test_name="Classification Statistics",
            expected_fields=['total_classified', 'type_distribution', 'classification_confidence']
        )
        self.test_results.append(result)
        print(f"{'✅' if result.status == 'PASS' else '❌'} {result.test_name}: {result.status} ({result.response_time_ms}ms)")
        
        # Test 2: Classification performance metrics
        result = self.test_api_endpoint(
            "/expense-classification/performance?sample_size=50",
            test_name="Performance Metrics",
            expected_fields=['accuracy', 'precision', 'recall', 'f1_score']
        )
        self.test_results.append(result)
        print(f"{'✅' if result.status == 'PASS' else '❌'} {result.test_name}: {result.status} ({result.response_time_ms}ms)")
        
        # Test 3: Tag analysis endpoint
        result = self.test_api_endpoint(
            "/expense-classification/tags-analysis?limit=20",
            test_name="Tag Analysis",
            expected_fields=['tags_analyzed', 'summary']
        )
        self.test_results.append(result)
        print(f"{'✅' if result.status == 'PASS' else '❌'} {result.test_name}: {result.status} ({result.response_time_ms}ms)")
        
        # Test 4: Classification rules
        result = self.test_api_endpoint(
            "/expense-classification/rules",
            test_name="Classification Rules",
            expected_fields=['classification_rules', 'system_stats']
        )
        self.test_results.append(result)
        print(f"{'✅' if result.status == 'PASS' else '❌'} {result.test_name}: {result.status} ({result.response_time_ms}ms)")
        
        # Test 5: Single tag classification
        result = self.test_api_endpoint(
            "/expense-classification/suggest",
            method="POST",
            data={"tag_name": "netflix", "transaction_amount": -15.99},
            test_name="Single Tag Classification",
            expected_fields=['tag_name', 'expense_type', 'confidence']
        )
        self.test_results.append(result)
        print(f"{'✅' if result.status == 'PASS' else '❌'} {result.test_name}: {result.status} ({result.response_time_ms}ms)")
        
        # Test 6: Batch classification
        result = self.test_api_endpoint(
            "/expense-classification/batch",
            method="POST", 
            data={"tag_names": ["netflix", "courses", "resto", "loyer"]},
            test_name="Batch Classification",
            expected_fields=['results', 'summary']
        )
        self.test_results.append(result)
        print(f"{'✅' if result.status == 'PASS' else '❌'} {result.test_name}: {result.status} ({result.response_time_ms}ms)")

    def validate_enhanced_endpoints(self) -> None:
        """Test the new enhanced transaction-specific endpoints"""
        
        print("\n🚀 ENHANCED AI ENDPOINTS VALIDATION")
        print("=" * 50)
        
        sample_tx_id = self.get_sample_transaction_id()
        if not sample_tx_id:
            print("❌ Could not get sample transaction for testing")
            return
        
        print(f"📋 Using sample transaction ID: {sample_tx_id}")
        
        # Test 1: AI suggestion for specific transaction
        result = self.test_api_endpoint(
            f"/expense-classification/transactions/{sample_tx_id}/ai-suggestion",
            test_name="Transaction AI Suggestion",
            expected_fields=['suggestion', 'confidence_score', 'explanation', 'transaction_id']
        )
        self.test_results.append(result)
        print(f"{'✅' if result.status == 'PASS' else '❌'} {result.test_name}: {result.status} ({result.response_time_ms}ms)")
        
        # Test 2: Transaction classification with feedback
        result = self.test_api_endpoint(
            f"/expense-classification/transactions/{sample_tx_id}/classify",
            method="POST",
            data={"expense_type": "VARIABLE", "user_feedback": True, "override_ai": False},
            test_name="Transaction Classification with Feedback",
            expected_fields=['success', 'transaction_id', 'new_classification']
        )
        self.test_results.append(result)
        print(f"{'✅' if result.status == 'PASS' else '❌'} {result.test_name}: {result.status} ({result.response_time_ms}ms)")
        
        # Test 3: Pending classification transactions
        result = self.test_api_endpoint(
            "/expense-classification/transactions/pending-classification?limit=10",
            test_name="Pending Classification Transactions",
            expected_fields=['transactions', 'ai_suggestions', 'stats']
        )
        self.test_results.append(result)
        print(f"{'✅' if result.status == 'PASS' else '❌'} {result.test_name}: {result.status} ({result.response_time_ms}ms)")
        
        # Test 4: Auto-suggestions endpoint
        result = self.test_api_endpoint(
            "/expense-classification/auto-suggestions",
            method="POST",
            data={"confidence_threshold": 0.7, "max_suggestions": 20},
            test_name="Auto-suggestions Generation",
        )
        self.test_results.append(result)
        print(f"{'✅' if result.status == 'PASS' else '❌'} {result.test_name}: {result.status} ({result.response_time_ms}ms)")
        
        # Test 5: Suggestions summary
        result = self.test_api_endpoint(
            "/expense-classification/suggestions/summary?confidence_threshold=0.7",
            test_name="Suggestions Summary",
            expected_fields=['total_suggestions', 'avg_confidence', 'processing_time_ms']
        )
        self.test_results.append(result)
        print(f"{'✅' if result.status == 'PASS' else '❌'} {result.test_name}: {result.status} ({result.response_time_ms}ms)")

    def validate_ml_performance(self) -> None:
        """Validate ML system performance metrics"""
        
        print("\n🧠 ML PERFORMANCE VALIDATION")
        print("=" * 50)
        
        # Test confidence score accuracy with known patterns
        test_cases = [
            {"tag": "netflix", "expected_type": "FIXED", "min_confidence": 0.8},
            {"tag": "loyer", "expected_type": "FIXED", "min_confidence": 0.9},
            {"tag": "courses", "expected_type": "VARIABLE", "min_confidence": 0.7},
            {"tag": "restaurant", "expected_type": "VARIABLE", "min_confidence": 0.7},
            {"tag": "spotify", "expected_type": "FIXED", "min_confidence": 0.8},
        ]
        
        confidence_scores = []
        classification_accuracy = 0
        
        for i, case in enumerate(test_cases):
            try:
                response = self.session.post(
                    f"{BASE_URL}/expense-classification/suggest",
                    json={"tag_name": case["tag"], "transaction_amount": -20.0}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    predicted_type = data.get('expense_type')
                    confidence = data.get('confidence', 0)
                    
                    confidence_scores.append(confidence)
                    
                    # Check accuracy
                    if predicted_type == case["expected_type"] and confidence >= case["min_confidence"]:
                        classification_accuracy += 1
                        status = "✅"
                    else:
                        status = "⚠️"
                    
                    print(f"{status} {case['tag']}: {predicted_type} (confidence: {confidence:.2f})")
                else:
                    print(f"❌ {case['tag']}: API error {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {case['tag']}: Test failed - {e}")
        
        # Calculate performance metrics
        if confidence_scores:
            avg_confidence = statistics.mean(confidence_scores)
            accuracy_rate = classification_accuracy / len(test_cases)
            
            self.performance_metrics['ml_avg_confidence'] = avg_confidence
            self.performance_metrics['ml_accuracy_rate'] = accuracy_rate
            
            print(f"\n📊 ML Performance Summary:")
            print(f"   Average Confidence: {avg_confidence:.2f}")
            print(f"   Accuracy Rate: {accuracy_rate:.2f} ({classification_accuracy}/{len(test_cases)})")
            
            # Performance assessment
            if accuracy_rate >= 0.8 and avg_confidence >= 0.75:
                print("✅ ML Performance: EXCELLENT")
            elif accuracy_rate >= 0.6 and avg_confidence >= 0.65:
                print("⚠️ ML Performance: GOOD")
            else:
                print("❌ ML Performance: NEEDS IMPROVEMENT")

    def validate_response_times(self) -> None:
        """Validate API response times meet performance targets"""
        
        print("\n⚡ PERFORMANCE BENCHMARKS")
        print("=" * 50)
        
        # Target: <100ms for classification endpoints
        TARGET_MS = 100
        
        # Test multiple classification requests
        response_times = []
        
        test_endpoints = [
            ("/expense-classification/suggest", "POST", {"tag_name": "test"}),
            ("/expense-classification/stats", "GET", None),
            ("/expense-classification/rules", "GET", None),
        ]
        
        for endpoint, method, data in test_endpoints:
            times = []
            
            # Run 5 requests to get average
            for _ in range(5):
                start_time = time.time()
                
                if method == "GET":
                    response = self.session.get(f"{BASE_URL}{endpoint}")
                else:
                    response = self.session.post(f"{BASE_URL}{endpoint}", json=data)
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    times.append(response_time)
            
            if times:
                avg_time = statistics.mean(times)
                response_times.extend(times)
                
                status = "✅" if avg_time < TARGET_MS else "⚠️" if avg_time < TARGET_MS * 2 else "❌"
                print(f"{status} {endpoint}: {avg_time:.1f}ms avg")
        
        if response_times:
            overall_avg = statistics.mean(response_times)
            self.performance_metrics['avg_response_time_ms'] = overall_avg
            
            print(f"\n📊 Performance Summary:")
            print(f"   Overall Average: {overall_avg:.1f}ms")
            print(f"   Target: <{TARGET_MS}ms")
            
            if overall_avg < TARGET_MS:
                print("✅ Performance: MEETS TARGET")
            elif overall_avg < TARGET_MS * 1.5:
                print("⚠️ Performance: ACCEPTABLE")
            else:
                print("❌ Performance: BELOW TARGET")

    def validate_error_handling(self) -> None:
        """Test error handling and edge cases"""
        
        print("\n🛡️ ERROR HANDLING & EDGE CASES")
        print("=" * 50)
        
        error_cases = [
            # Invalid transaction ID
            ("/expense-classification/transactions/999999/ai-suggestion", "GET", None, "Invalid Transaction ID"),
            
            # Invalid expense type
            ("/expense-classification/transactions/1/classify", "POST", 
             {"expense_type": "INVALID", "user_feedback": True}, "Invalid Expense Type"),
            
            # Empty tag name
            ("/expense-classification/suggest", "POST", 
             {"tag_name": "", "transaction_amount": -10}, "Empty Tag Name"),
            
            # Malformed request
            ("/expense-classification/batch", "POST", 
             {"tag_names": []}, "Empty Batch Request"),
        ]
        
        error_handling_score = 0
        
        for endpoint, method, data, test_name in error_cases:
            try:
                if method == "GET":
                    response = self.session.get(f"{BASE_URL}{endpoint}")
                else:
                    response = self.session.post(f"{BASE_URL}{endpoint}", json=data)
                
                # We expect 4xx errors for these cases
                if 400 <= response.status_code < 500:
                    print(f"✅ {test_name}: Correctly handled with {response.status_code}")
                    error_handling_score += 1
                elif response.status_code == 200:
                    print(f"⚠️ {test_name}: Should have failed but returned 200")
                else:
                    print(f"❌ {test_name}: Unexpected status {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {test_name}: Test failed - {e}")
        
        self.performance_metrics['error_handling_score'] = error_handling_score / len(error_cases)
        
        print(f"\n📊 Error Handling Score: {error_handling_score}/{len(error_cases)}")

    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        
        recommendations = []
        
        # Check performance
        avg_response_time = self.performance_metrics.get('avg_response_time_ms', 0)
        if avg_response_time > 100:
            recommendations.append(f"⚡ PERFORMANCE: Optimize response times (current: {avg_response_time:.1f}ms, target: <100ms)")
        
        # Check ML accuracy
        ml_accuracy = self.performance_metrics.get('ml_accuracy_rate', 0)
        if ml_accuracy < 0.8:
            recommendations.append(f"🧠 ML ACCURACY: Improve classification accuracy (current: {ml_accuracy:.1%}, target: >80%)")
        
        # Check ML confidence
        ml_confidence = self.performance_metrics.get('ml_avg_confidence', 0)
        if ml_confidence < 0.75:
            recommendations.append(f"🎯 CONFIDENCE: Enhance confidence scoring (current: {ml_confidence:.2f}, target: >0.75)")
        
        # Check error handling
        error_score = self.performance_metrics.get('error_handling_score', 0)
        if error_score < 0.8:
            recommendations.append(f"🛡️ ERROR HANDLING: Improve error handling coverage (current: {error_score:.1%}, target: >80%)")
        
        # Check failed tests
        failed_tests = [r for r in self.test_results if r.status == 'FAIL']
        if failed_tests:
            recommendations.append(f"🔧 API ENDPOINTS: Fix {len(failed_tests)} failing endpoints")
        
        # Add general recommendations
        if not recommendations:
            recommendations.append("✅ EXCELLENT: All quality metrics meet or exceed targets")
        else:
            recommendations.append("🔄 Continue monitoring and optimizing system performance")
        
        return recommendations

    def generate_report(self) -> ValidationReport:
        """Generate comprehensive validation report"""
        
        # Calculate summary statistics
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.status == 'PASS'])
        failed_tests = len([r for r in self.test_results if r.status == 'FAIL'])
        warning_tests = len([r for r in self.test_results if r.status == 'WARNING'])
        
        avg_response_time = statistics.mean([r.response_time_ms for r in self.test_results]) if self.test_results else 0
        
        summary = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'warning_tests': warning_tests,
            'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
            'avg_response_time_ms': round(avg_response_time, 1),
            'overall_status': 'PASS' if failed_tests == 0 else 'FAIL' if failed_tests > total_tests * 0.2 else 'WARNING'
        }
        
        # Add performance metrics
        self.performance_metrics['overall_avg_response_time'] = avg_response_time
        
        # Generate recommendations
        recommendations = self.generate_recommendations()
        
        return ValidationReport(
            test_results=self.test_results,
            summary=summary,
            performance_metrics=self.performance_metrics,
            recommendations=recommendations
        )

    def print_report(self, report: ValidationReport) -> None:
        """Print comprehensive validation report"""
        
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE AI CLASSIFICATION VALIDATION REPORT")
        print("=" * 80)
        
        # Summary
        print(f"\n📊 TEST SUMMARY")
        print(f"   Total Tests: {report.summary['total_tests']}")
        print(f"   ✅ Passed: {report.summary['passed_tests']}")
        print(f"   ❌ Failed: {report.summary['failed_tests']}")
        print(f"   ⚠️ Warnings: {report.summary['warning_tests']}")
        print(f"   Success Rate: {report.summary['success_rate']:.1%}")
        print(f"   Avg Response Time: {report.summary['avg_response_time_ms']}ms")
        
        # Overall Status
        status_icon = "✅" if report.summary['overall_status'] == 'PASS' else "⚠️" if report.summary['overall_status'] == 'WARNING' else "❌"
        print(f"\n{status_icon} OVERALL STATUS: {report.summary['overall_status']}")
        
        # Performance Metrics
        print(f"\n⚡ PERFORMANCE METRICS")
        for metric, value in report.performance_metrics.items():
            if isinstance(value, float):
                if 'time' in metric:
                    print(f"   {metric}: {value:.1f}ms")
                elif 'rate' in metric or 'score' in metric:
                    print(f"   {metric}: {value:.1%}")
                else:
                    print(f"   {metric}: {value:.2f}")
        
        # Failed Tests Details
        failed_tests = [r for r in report.test_results if r.status == 'FAIL']
        if failed_tests:
            print(f"\n❌ FAILED TESTS DETAILS")
            for test in failed_tests:
                print(f"   • {test.test_name} ({test.endpoint})")
                print(f"     Errors: {', '.join(test.errors)}")
        
        # Recommendations
        print(f"\n🔍 RECOMMENDATIONS")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"   {i}. {rec}")
        
        # Quality Assessment
        print(f"\n🏆 QUALITY ASSESSMENT")
        
        success_rate = report.summary['success_rate']
        avg_response_time = report.summary['avg_response_time_ms']
        
        if success_rate >= 0.95 and avg_response_time < 100:
            grade = "A+ EXCELLENT"
            assessment = "System exceeds all quality targets. Ready for production."
        elif success_rate >= 0.85 and avg_response_time < 150:
            grade = "A GOOD"
            assessment = "System meets quality standards with minor optimizations needed."
        elif success_rate >= 0.70 and avg_response_time < 200:
            grade = "B ACCEPTABLE"
            assessment = "System functional but requires improvements before production."
        else:
            grade = "C NEEDS WORK"
            assessment = "System requires significant improvements before production release."
        
        print(f"   Grade: {grade}")
        print(f"   Assessment: {assessment}")
        
        # Release Recommendation
        if failed_tests:
            print(f"\n🚫 RELEASE RECOMMENDATION: BLOCK")
            print(f"   Reason: {len(failed_tests)} critical tests failing")
            print(f"   Action Required: Fix failing endpoints before release")
        elif success_rate < 0.8:
            print(f"\n⚠️ RELEASE RECOMMENDATION: CAUTION")
            print(f"   Reason: Success rate below 80% ({success_rate:.1%})")
            print(f"   Action Required: Address warnings and monitor closely")
        else:
            print(f"\n✅ RELEASE RECOMMENDATION: APPROVED")
            print(f"   Reason: All critical tests passing, performance acceptable")
            print(f"   Next Steps: Deploy with standard monitoring")

    def run_complete_validation(self) -> ValidationReport:
        """Run complete validation suite"""
        
        print("🚀 STARTING COMPREHENSIVE AI CLASSIFICATION VALIDATION")
        print("=" * 80)
        
        if not self.authenticate():
            print("❌ CRITICAL: Authentication failed. Cannot proceed with validation.")
            return ValidationReport([], {}, {}, ["Authentication failed - check credentials"])
        
        try:
            # Run all validation tests
            self.validate_backend_endpoints()
            self.validate_enhanced_endpoints()
            self.validate_ml_performance()
            self.validate_response_times()
            self.validate_error_handling()
            
            # Generate and return report
            report = self.generate_report()
            self.print_report(report)
            
            return report
            
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR during validation: {e}")
            return ValidationReport(
                self.test_results, 
                {'total_tests': len(self.test_results), 'overall_status': 'CRITICAL_ERROR'}, 
                self.performance_metrics,
                [f"Critical validation error: {e}"]
            )

def main():
    """Main execution function"""
    
    validator = AIClassificationValidator()
    
    try:
        report = validator.run_complete_validation()
        
        # Save report to file
        with open('ai_classification_validation_report.json', 'w') as f:
            # Convert dataclass to dict for JSON serialization
            report_dict = {
                'test_results': [asdict(r) for r in report.test_results],
                'summary': report.summary,
                'performance_metrics': report.performance_metrics,
                'recommendations': report.recommendations,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'version': '2.3'
            }
            json.dump(report_dict, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: ai_classification_validation_report.json")
        
        # Return appropriate exit code
        if report.summary.get('overall_status') == 'PASS':
            sys.exit(0)
        elif report.summary.get('overall_status') == 'WARNING':
            sys.exit(1)
        else:
            sys.exit(2)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Validation interrupted by user")
        sys.exit(3)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        sys.exit(4)

if __name__ == "__main__":
    main()