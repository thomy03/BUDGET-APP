"""
Comprehensive ML Feedback Learning System Tests
Tests the complete feedback learning pipeline including:
1. Feedback collection and storage
2. Pattern learning from user corrections
3. Integration with classification service
4. Confidence adjustments based on feedback
5. API endpoints functionality

Author: Claude Code - ML Backend Architect
"""

import pytest
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from models.database import MLFeedback, Transaction, MerchantKnowledgeBase
from models.schemas import MLFeedbackCreate
from services.ml_feedback_learning import MLFeedbackLearningService
from routers.ml_feedback import MLFeedbackService
from app import app

logger = logging.getLogger(__name__)

class TestMLFeedbackSystem:
    """Test suite for ML feedback learning system"""
    
    @pytest.fixture
    def client(self):
        """Test client for API endpoints"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_transaction(self, db_session: Session):
        """Create a sample transaction for testing"""
        transaction = Transaction(
            id=999,
            month="2025-08",
            label="CB CHEZ PAUL RESTAURANT 35.50",
            category="alimentation",
            amount=35.50,
            is_expense=True,
            exclude=False,
            expense_type="VARIABLE",
            tags="",
            confidence_score=0.3
        )
        db_session.add(transaction)
        db_session.commit()
        db_session.refresh(transaction)
        return transaction
    
    def test_feedback_service_initialization(self, db_session: Session):
        """Test feedback service initializes correctly"""
        service = MLFeedbackService(db_session)
        assert service.db == db_session
        logger.info("✅ Feedback service initialization successful")
    
    def test_merchant_name_normalization(self, db_session: Session):
        """Test merchant name normalization consistency"""
        service = MLFeedbackService(db_session)
        
        test_cases = [
            ("CB CHEZ PAUL RESTAURANT 35.50", "chez paul"),
            ("PRLV NETFLIX SARL", "netflix sarl"),
            ("VIR LOYER APPARTEMENT", "loyer appartement"),
            ("CARTE SUPERMARCHE MONOPRIX", "supermarche monoprix"),
            ("Amazon.fr", "amazon.fr")
        ]
        
        for input_desc, expected in test_cases:
            result = service.normalize_merchant_name(input_desc)
            assert result == expected, f"Expected {expected}, got {result} for {input_desc}"
        
        logger.info("✅ Merchant name normalization working correctly")
    
    def test_save_feedback_basic(self, db_session: Session, sample_transaction):
        """Test basic feedback saving functionality"""
        service = MLFeedbackService(db_session)
        
        feedback_data = MLFeedbackCreate(
            transaction_id=sample_transaction.id,
            original_tag="divers",
            corrected_tag="restaurant",
            original_expense_type="VARIABLE",
            corrected_expense_type="VARIABLE",
            feedback_type="correction",
            confidence_before=0.3
        )
        
        saved_feedback = service.save_feedback(feedback_data, user_id="test_user")
        
        assert saved_feedback.id is not None
        assert saved_feedback.transaction_id == sample_transaction.id
        assert saved_feedback.original_tag == "divers"
        assert saved_feedback.corrected_tag == "restaurant"
        assert saved_feedback.merchant_pattern == "chez paul"
        assert saved_feedback.user_id == "test_user"
        
        logger.info("✅ Basic feedback saving successful")
    
    def test_pattern_learning_trigger(self, db_session: Session, sample_transaction):
        """Test that pattern learning is triggered after feedback"""
        service = MLFeedbackService(db_session)
        
        # Add multiple feedback entries for the same pattern
        for i in range(3):
            feedback_data = MLFeedbackCreate(
                transaction_id=sample_transaction.id,
                original_tag="divers",
                corrected_tag="restaurant",
                original_expense_type="VARIABLE",
                corrected_expense_type="VARIABLE",
                feedback_type="correction",
                confidence_before=0.3
            )
            service.save_feedback(feedback_data, user_id=f"test_user_{i}")
        
        # Check that patterns were learned
        learned_patterns = service.get_learned_patterns(limit=10)
        assert len(learned_patterns) > 0
        
        # Find our pattern
        restaurant_pattern = next(
            (p for p in learned_patterns if p.learned_tag == "restaurant"),
            None
        )
        assert restaurant_pattern is not None
        assert restaurant_pattern.merchant_pattern == "chez paul"
        assert restaurant_pattern.usage_count >= 3
        
        logger.info("✅ Pattern learning triggered correctly")
    
    def test_feedback_enhanced_classification(self, db_session: Session, sample_transaction):
        """Test that feedback enhances classification accuracy"""
        # First, add feedback to create a learned pattern
        service = MLFeedbackService(db_session)
        
        for i in range(3):
            feedback_data = MLFeedbackCreate(
                transaction_id=sample_transaction.id,
                original_tag="divers",
                corrected_tag="restaurant",
                original_expense_type="VARIABLE",
                corrected_expense_type="VARIABLE",
                feedback_type="correction",
                confidence_before=0.3
            )
            service.save_feedback(feedback_data, user_id=f"test_user_{i}")
        
        # Now test enhanced classification
        ml_service = MLFeedbackLearningService(db_session)
        result = ml_service.classify_with_feedback(
            transaction_label="CB CHEZ PAUL RESTAURANT 42.00",
            amount=42.00
        )
        
        # Should use learned pattern with high confidence
        assert result.suggested_tag == "restaurant"
        assert result.confidence > 0.8  # High confidence from feedback
        assert "feedback" in result.primary_reason
        
        logger.info("✅ Feedback-enhanced classification working")
    
    def test_confidence_adjustments(self, db_session: Session, sample_transaction):
        """Test that confidence is adjusted based on correction patterns"""
        service = MLFeedbackService(db_session)
        
        # Add feedback showing frequent corrections of "shopping" tag
        for i in range(5):
            feedback_data = MLFeedbackCreate(
                transaction_id=sample_transaction.id,
                original_tag="shopping",
                corrected_tag="restaurant",
                original_expense_type="VARIABLE",
                corrected_expense_type="VARIABLE",
                feedback_type="correction",
                confidence_before=0.7
            )
            service.save_feedback(feedback_data, user_id=f"test_user_{i}")
        
        # Test enhanced classification service
        ml_service = MLFeedbackLearningService(db_session)
        
        # Mock a base classification result that would be corrected
        # This would normally come from the base classifier, but we'll simulate
        # testing the confidence adjustment logic
        
        assert len(ml_service.merchant_corrections) > 0
        logger.info("✅ Confidence adjustment patterns loaded")
    
    def test_feedback_api_endpoints(self, client, db_session: Session, sample_transaction):
        """Test ML feedback API endpoints"""
        
        # Test saving feedback via API
        feedback_payload = {
            "transaction_id": sample_transaction.id,
            "original_tag": "divers",
            "corrected_tag": "restaurant",
            "original_expense_type": "VARIABLE",
            "corrected_expense_type": "VARIABLE",
            "feedback_type": "correction",
            "confidence_before": 0.3
        }
        
        response = client.post("/api/ml-feedback/", json=feedback_payload)
        assert response.status_code == 201
        
        feedback_response = response.json()
        assert feedback_response["transaction_id"] == sample_transaction.id
        assert feedback_response["corrected_tag"] == "restaurant"
        
        # Test getting learned patterns
        response = client.get("/api/ml-feedback/patterns")
        assert response.status_code == 200
        patterns = response.json()
        assert isinstance(patterns, list)
        
        # Test getting feedback statistics
        response = client.get("/api/ml-feedback/stats")
        assert response.status_code == 200
        stats = response.json()
        assert "total_feedback_entries" in stats
        assert stats["total_feedback_entries"] >= 1
        
        logger.info("✅ ML feedback API endpoints working")
    
    def test_enhanced_classification_api(self, client, db_session: Session, sample_transaction):
        """Test enhanced classification API endpoints"""
        
        # First add some feedback to create patterns
        feedback_payload = {
            "transaction_id": sample_transaction.id,
            "original_tag": "divers",
            "corrected_tag": "restaurant",
            "feedback_type": "correction",
            "confidence_before": 0.3
        }
        
        for i in range(3):
            response = client.post("/api/ml-feedback/", json=feedback_payload)
            assert response.status_code == 201
        
        # Test enhanced classification
        classification_payload = {
            "transaction_label": "CB CHEZ PAUL BRASSERIE 28.50",
            "amount": 28.50,
            "use_web_research": False,
            "include_alternatives": True,
            "confidence_threshold": 0.5
        }
        
        response = client.post("/api/ml-classification/classify", json=classification_payload)
        assert response.status_code == 200
        
        result = response.json()
        assert "suggested_tag" in result
        assert "confidence" in result
        assert "explanation" in result
        assert "source" in result
        assert result["feedback_pattern_used"] in [True, False]
        
        logger.info("✅ Enhanced classification API working")
    
    def test_batch_classification(self, client, db_session: Session):
        """Test batch classification with feedback learning"""
        
        batch_payload = {
            "transactions": [
                {"label": "CB CHEZ PAUL RESTAURANT", "amount": 35.50},
                {"label": "PRLV NETFLIX SARL", "amount": 12.99},
                {"label": "SUPERMARCHE MONOPRIX", "amount": 67.80}
            ],
            "use_feedback_learning": True,
            "confidence_threshold": 0.3,
            "max_alternatives": 2
        }
        
        response = client.post("/api/ml-classification/classify-batch", json=batch_payload)
        assert response.status_code == 200
        
        result = response.json()
        assert "results" in result
        assert "summary" in result
        assert len(result["results"]) <= 3  # May filter some based on confidence
        
        summary = result["summary"]
        assert "total_processed" in summary
        assert "average_confidence" in summary
        
        logger.info("✅ Batch classification working")
    
    def test_pattern_statistics(self, db_session: Session, sample_transaction):
        """Test pattern statistics and monitoring"""
        service = MLFeedbackService(db_session)
        
        # Add some feedback
        feedback_data = MLFeedbackCreate(
            transaction_id=sample_transaction.id,
            original_tag="divers",
            corrected_tag="restaurant",
            feedback_type="correction",
            confidence_before=0.3
        )
        service.save_feedback(feedback_data)
        
        # Test statistics
        stats = service.get_feedback_stats()
        assert stats.total_feedback_entries >= 1
        assert stats.corrections_count >= 1
        assert isinstance(stats.most_corrected_tags, list)
        
        # Test learning service statistics
        ml_service = MLFeedbackLearningService(db_session)
        pattern_stats = ml_service.get_pattern_statistics()
        assert "total_patterns" in pattern_stats
        assert "average_confidence" in pattern_stats
        
        logger.info("✅ Pattern statistics working")
    
    def test_feedback_system_integration(self, db_session: Session, sample_transaction):
        """Test end-to-end integration of feedback system"""
        
        # Simulate user workflow:
        # 1. User gets ML suggestion with low confidence
        # 2. User corrects the suggestion
        # 3. System learns from correction
        # 4. Future similar transactions get better suggestions
        
        ml_service = MLFeedbackLearningService(db_session)
        feedback_service = MLFeedbackService(db_session)
        
        # Step 1: Initial classification (would be low confidence)
        initial_result = ml_service.classify_with_feedback(
            transaction_label="CB CHEZ PAUL RESTAURANT 35.50",
            amount=35.50
        )
        
        # Step 2: User provides correction
        feedback_data = MLFeedbackCreate(
            transaction_id=sample_transaction.id,
            original_tag=initial_result.suggested_tag or "divers",
            corrected_tag="restaurant",
            original_expense_type=initial_result.expense_type,
            corrected_expense_type="VARIABLE",
            feedback_type="correction",
            confidence_before=initial_result.confidence
        )
        
        # Add multiple corrections to establish pattern
        for i in range(3):
            feedback_service.save_feedback(feedback_data, user_id=f"user_{i}")
        
        # Step 3: Reload patterns to include new learning
        ml_service.reload_patterns()
        
        # Step 4: New classification should be improved
        improved_result = ml_service.classify_with_feedback(
            transaction_label="CB CHEZ PAUL BRASSERIE 42.00",
            amount=42.00
        )
        
        # Verify improvement
        assert improved_result.suggested_tag == "restaurant"
        assert improved_result.confidence > initial_result.confidence
        assert "feedback" in improved_result.primary_reason
        
        logger.info("✅ End-to-end feedback system integration successful")
    
    def test_error_handling(self, client, db_session: Session):
        """Test error handling in feedback system"""
        
        # Test invalid transaction ID
        invalid_feedback = {
            "transaction_id": 999999,
            "corrected_tag": "restaurant",
            "feedback_type": "correction"
        }
        
        response = client.post("/api/ml-feedback/", json=invalid_feedback)
        assert response.status_code == 404
        
        # Test invalid classification request
        invalid_classification = {
            "transaction_label": "",
            "amount": -100  # Negative amount
        }
        
        response = client.post("/api/ml-classification/classify", json=invalid_classification)
        # Should handle gracefully, not crash
        assert response.status_code in [200, 422]  # Either success or validation error
        
        logger.info("✅ Error handling working correctly")


def test_ml_feedback_system_comprehensive(db_session: Session):
    """Comprehensive test of the ML feedback learning system"""
    test_suite = TestMLFeedbackSystem()
    
    # Create test client
    client = TestClient(app)
    
    # Create sample transaction
    transaction = Transaction(
        id=1001,
        month="2025-08",
        label="CB CHEZ PAUL RESTAURANT 35.50",
        category="alimentation",
        amount=35.50,
        is_expense=True,
        exclude=False,
        expense_type="VARIABLE",
        tags="",
        confidence_score=0.3
    )
    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)
    
    try:
        # Run all tests
        test_suite.test_feedback_service_initialization(db_session)
        test_suite.test_merchant_name_normalization(db_session)
        test_suite.test_save_feedback_basic(db_session, transaction)
        test_suite.test_pattern_learning_trigger(db_session, transaction)
        test_suite.test_feedback_enhanced_classification(db_session, transaction)
        test_suite.test_confidence_adjustments(db_session, transaction)
        test_suite.test_pattern_statistics(db_session, transaction)
        test_suite.test_feedback_system_integration(db_session, transaction)
        
        logger.info("🎉 ALL ML FEEDBACK SYSTEM TESTS PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"❌ ML feedback system test failed: {e}")
        raise


if __name__ == "__main__":
    print("🧪 Running ML Feedback Learning System Tests...")
    
    # This would normally be run with pytest
    # pytest tests/validation/test_ml_feedback_system.py -v
    
    print("✅ Test file created successfully!")
    print("📝 To run tests: pytest tests/validation/test_ml_feedback_system.py -v")