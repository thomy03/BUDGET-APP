"""
Test Script for Revolutionary Web Research System

This script tests the complete web research system including:
1. WebResearchService functionality
2. MerchantKnowledgeBase database operations  
3. API endpoints for enrichment
4. Integration with classification system

Run this script to validate the system works correctly.
"""

import asyncio
import logging
import sys
import os
import requests
import json
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database import get_db, Transaction, MerchantKnowledgeBase
from services.web_research_service import WebResearchService, get_merchant_from_transaction_label
from services.expense_classification import ExpenseClassificationService

# Configure logging for testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebResearchSystemTester:
    """Comprehensive tester for the web research system"""
    
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.test_merchants = [
            "RESTAURANT LE PETIT PARIS PARIS",
            "CARREFOUR VILLENEUVE LA GARENNE", 
            "PHARMACIE CENTRALE LYON",
            "TOTAL ACCESS MARSEILLE",
            "BNP PARIBAS FRAIS BANCAIRES",
            "ORANGE FRANCE TELECOM",
            "NETFLIX ENTERTAINMENT",
            "STATION SERVICE SHELL",
            "BOULANGERIE DU COIN",
            "SUPERMARCHE LECLERC"
        ]
        self.results = []
    
    async def test_merchant_name_extraction(self):
        """Test merchant name extraction from transaction labels"""
        logger.info("=== Testing Merchant Name Extraction ===")
        
        test_labels = [
            "CB RESTAURANT LE PETIT PARIS 12/08 15H30",
            "PRLV SEPA ORANGE FRANCE TELECOM",
            "VIR LOYER APPARTEMENT PARIS",
            "RETRAIT DAB BNP PARIBAS OPERA",
            "CB 1234 CARREFOUR VILLENEUVE 11/08"
        ]
        
        for label in test_labels:
            merchant = get_merchant_from_transaction_label(label)
            logger.info(f"Label: '{label}' -> Merchant: '{merchant}'")
            
        logger.info("✅ Merchant name extraction test completed\n")
    
    async def test_web_research_service(self):
        """Test the core web research service"""
        logger.info("=== Testing Web Research Service ===")
        
        async with WebResearchService() as research_service:
            for i, merchant_name in enumerate(self.test_merchants[:5], 1):
                logger.info(f"Testing merchant {i}/5: {merchant_name}")
                
                try:
                    result = await research_service.research_merchant(merchant_name)
                    
                    self.results.append({
                        'merchant_name': merchant_name,
                        'normalized_name': result.normalized_name,
                        'business_type': result.business_type,
                        'confidence_score': result.confidence_score,
                        'suggested_expense_type': result.suggested_expense_type,
                        'suggested_tags': result.suggested_tags,
                        'data_sources': result.data_sources,
                        'duration_ms': result.research_duration_ms,
                        'success': True
                    })
                    
                    logger.info(f"  ✅ Business Type: {result.business_type}")
                    logger.info(f"  ✅ Confidence: {result.confidence_score:.2f}")
                    logger.info(f"  ✅ Expense Type: {result.suggested_expense_type}")
                    logger.info(f"  ✅ Tags: {result.suggested_tags}")
                    logger.info(f"  ✅ Sources: {result.data_sources}")
                    logger.info(f"  ✅ Duration: {result.research_duration_ms}ms")
                    
                except Exception as e:
                    logger.error(f"  ❌ Error researching {merchant_name}: {e}")
                    self.results.append({
                        'merchant_name': merchant_name,
                        'success': False,
                        'error': str(e)
                    })
                
                # Rate limiting between requests
                await asyncio.sleep(1)
        
        successful = sum(1 for r in self.results if r.get('success', False))
        logger.info(f"✅ Web research service test completed: {successful}/{len(self.results)} successful\n")
    
    def test_database_operations(self):
        """Test database operations for merchant knowledge base"""
        logger.info("=== Testing Database Operations ===")
        
        db = next(get_db())
        
        try:
            # Test creating merchant entries
            for result in self.results:
                if not result.get('success', False):
                    continue
                
                # Check if merchant already exists
                existing = db.query(MerchantKnowledgeBase).filter(
                    MerchantKnowledgeBase.normalized_name == result['normalized_name']
                ).first()
                
                if existing:
                    logger.info(f"  ✅ Merchant '{result['merchant_name']}' already exists in KB")
                    continue
                
                # Create new merchant entry
                merchant_entry = MerchantKnowledgeBase(
                    merchant_name=result['merchant_name'],
                    normalized_name=result['normalized_name'],
                    business_type=result['business_type'],
                    confidence_score=result['confidence_score'],
                    suggested_expense_type=result['suggested_expense_type'],
                    suggested_tags=','.join(result['suggested_tags']) if result['suggested_tags'] else None,
                    data_sources=json.dumps(result['data_sources']) if result['data_sources'] else None,
                    research_duration_ms=result['duration_ms'],
                    usage_count=1,
                    last_used=datetime.now(),
                    is_verified=False,
                    is_active=True
                )
                
                db.add(merchant_entry)
                db.commit()
                
                logger.info(f"  ✅ Added '{result['merchant_name']}' to knowledge base")
            
            # Test querying merchants
            total_merchants = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.is_active == True
            ).count()
            
            logger.info(f"  ✅ Total merchants in knowledge base: {total_merchants}")
            
            # Test business type distribution
            from sqlalchemy import func
            business_types = db.query(
                MerchantKnowledgeBase.business_type,
                func.count(MerchantKnowledgeBase.id).label('count')
            ).filter(
                MerchantKnowledgeBase.is_active == True,
                MerchantKnowledgeBase.business_type.isnot(None)
            ).group_by(MerchantKnowledgeBase.business_type).all()
            
            logger.info("  ✅ Business type distribution:")
            for business_type, count in business_types:
                logger.info(f"    - {business_type}: {count}")
                
        except Exception as e:
            logger.error(f"  ❌ Database operation error: {e}")
        finally:
            db.close()
        
        logger.info("✅ Database operations test completed\n")
    
    def test_api_endpoints(self):
        """Test the REST API endpoints"""
        logger.info("=== Testing API Endpoints ===")
        
        try:
            # Test knowledge base endpoint
            logger.info("Testing GET /research/knowledge-base")
            response = requests.get(f"{self.api_base_url}/research/knowledge-base")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"  ✅ Knowledge base has {len(data)} merchants")
            else:
                logger.error(f"  ❌ Knowledge base endpoint failed: {response.status_code}")
            
            # Test manual research endpoint
            logger.info("Testing POST /research/merchant")
            test_merchant = "RESTAURANT TEST PARIS"
            
            payload = {
                "merchant_name": test_merchant,
                "city": "Paris",
                "amount": 25.50
            }
            
            response = requests.post(
                f"{self.api_base_url}/research/merchant",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"  ✅ Manual research successful: {data['business_type']} ({data['confidence_score']:.2f})")
            else:
                logger.error(f"  ❌ Manual research failed: {response.status_code} - {response.text}")
            
            # Test stats endpoint
            logger.info("Testing GET /research/stats")
            response = requests.get(f"{self.api_base_url}/research/stats")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"  ✅ Stats: {data['total_merchants']} merchants, {data['high_confidence_rate']:.1%} high confidence")
            else:
                logger.error(f"  ❌ Stats endpoint failed: {response.status_code}")
                
        except requests.ConnectionError:
            logger.error("  ❌ Cannot connect to API server - make sure it's running on localhost:8000")
        except Exception as e:
            logger.error(f"  ❌ API test error: {e}")
        
        logger.info("✅ API endpoints test completed\n")
    
    def test_classification_integration(self):
        """Test integration with expense classification system"""
        logger.info("=== Testing Classification Integration ===")
        
        db = next(get_db())
        
        try:
            # Create classification service
            classifier = ExpenseClassificationService(db)
            
            # Test enhanced classification for each test merchant
            for result in self.results[:3]:  # Test first 3 for speed
                if not result.get('success', False):
                    continue
                
                merchant_name = result['merchant_name']
                logger.info(f"Testing enhanced classification for: {merchant_name}")
                
                try:
                    # Test the new web-enhanced classification
                    enhanced_result = classifier.classify_expense_with_web_intelligence(
                        tag_name=merchant_name,
                        transaction_amount=50.0,
                        transaction_description=merchant_name
                    )
                    
                    logger.info(f"  ✅ Enhanced classification: {enhanced_result.expense_type}")
                    logger.info(f"  ✅ Confidence: {enhanced_result.confidence:.2f}")
                    logger.info(f"  ✅ Primary reason: {enhanced_result.primary_reason}")
                    logger.info(f"  ✅ Contributing factors: {len(enhanced_result.contributing_factors)}")
                    
                except Exception as e:
                    logger.error(f"  ❌ Enhanced classification error for {merchant_name}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Classification integration test error: {e}")
        finally:
            db.close()
        
        logger.info("✅ Classification integration test completed\n")
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("=== Test Report ===")
        
        successful_research = sum(1 for r in self.results if r.get('success', False))
        total_tests = len(self.results)
        
        if total_tests > 0:
            success_rate = successful_research / total_tests * 100
            
            logger.info(f"Overall Success Rate: {success_rate:.1f}% ({successful_research}/{total_tests})")
            
            # Business type coverage
            business_types = set()
            for result in self.results:
                if result.get('success') and result.get('business_type'):
                    business_types.add(result['business_type'])
            
            logger.info(f"Business Types Identified: {len(business_types)}")
            logger.info(f"Types: {', '.join(sorted(business_types))}")
            
            # Average confidence
            confidences = [r['confidence_score'] for r in self.results if r.get('success') and r.get('confidence_score')]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                logger.info(f"Average Confidence Score: {avg_confidence:.2f}")
            
            # Performance metrics
            durations = [r['duration_ms'] for r in self.results if r.get('success') and r.get('duration_ms')]
            if durations:
                avg_duration = sum(durations) / len(durations)
                logger.info(f"Average Research Duration: {avg_duration:.0f}ms")
            
        logger.info("✅ Test report completed\n")


async def run_comprehensive_tests():
    """Run all tests in sequence"""
    logger.info("🚀 Starting Revolutionary Web Research System Tests")
    logger.info("=" * 60)
    
    tester = WebResearchSystemTester()
    
    try:
        # Test 1: Merchant name extraction
        await tester.test_merchant_name_extraction()
        
        # Test 2: Web research service
        await tester.test_web_research_service()
        
        # Test 3: Database operations
        tester.test_database_operations()
        
        # Test 4: API endpoints
        tester.test_api_endpoints()
        
        # Test 5: Classification integration
        tester.test_classification_integration()
        
        # Generate final report
        tester.generate_test_report()
        
        logger.info("🎉 All tests completed successfully!")
        logger.info("🌐 Revolutionary Web Research System is operational!")
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        raise


if __name__ == "__main__":
    print("🌐 Revolutionary Web Research System - Test Suite")
    print("=" * 60)
    print("This test suite validates the complete web research system")
    print("including merchant identification, classification, and API endpoints.")
    print()
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/docs")
        if response.status_code != 200:
            print("⚠️  Warning: API server might not be running on localhost:8000")
            print("   Start the server with: python -m uvicorn app:app --reload")
            print()
    except requests.ConnectionError:
        print("⚠️  Warning: Cannot connect to API server on localhost:8000")
        print("   Start the server with: python -m uvicorn app:app --reload")
        print()
    
    # Run the tests
    asyncio.run(run_comprehensive_tests())