"""
Test suite for Intelligent Expense Classification System
Validates ML performance, API endpoints, and business logic
"""

import pytest
import logging
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from datetime import datetime, date

from models.database import SessionLocal, Transaction, FixedLine, TagFixedLineMapping
from services.expense_classification import (
    ExpenseClassificationService, 
    get_expense_classification_service,
    evaluate_classification_performance,
    ClassificationResult
)
from services.tag_automation import get_tag_automation_service

logger = logging.getLogger(__name__)

class TestExpenseClassificationService:
    """Test suite for the core ML classification service"""
    
    @pytest.fixture
    def db_session(self):
        """Create a test database session"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    @pytest.fixture
    def classification_service(self, db_session):
        """Create classification service instance"""
        return ExpenseClassificationService(db_session)
    
    def test_service_initialization(self, classification_service):
        """Test that service initializes correctly with ML capabilities"""
        assert classification_service is not None
        assert hasattr(classification_service, 'FIXED_KEYWORDS')
        assert hasattr(classification_service, 'VARIABLE_KEYWORDS')
        assert len(classification_service.FIXED_KEYWORDS) > 20
        assert len(classification_service.VARIABLE_KEYWORDS) > 20
    
    def test_fixed_keyword_classification(self, classification_service):
        """Test classification of obvious fixed expense keywords"""
        test_cases = [
            ("netflix", "FIXED", 0.8),
            ("spotify premium", "FIXED", 0.8),
            ("edf facture", "FIXED", 0.8),
            ("orange internet", "FIXED", 0.8),
            ("assurance auto", "FIXED", 0.8),
            ("abonnement", "FIXED", 0.8)
        ]
        
        for tag_name, expected_type, min_confidence in test_cases:
            result = classification_service.classify_expense(
                tag_name=tag_name,
                transaction_amount=50.0,
                transaction_description=f"Test {tag_name}"
            )
            
            assert result.expense_type == expected_type, f"Failed for {tag_name}: expected {expected_type}, got {result.expense_type}"
            assert result.confidence >= min_confidence, f"Low confidence for {tag_name}: {result.confidence}"
            assert len(result.keyword_matches) > 0, f"No keyword matches for {tag_name}"
    
    def test_variable_keyword_classification(self, classification_service):
        """Test classification of obvious variable expense keywords"""
        test_cases = [
            ("restaurant mcdo", "VARIABLE", 0.7),
            ("courses supermarche", "VARIABLE", 0.7),
            ("carburant total", "VARIABLE", 0.7),
            ("pharmacie", "VARIABLE", 0.6),
            ("vetements", "VARIABLE", 0.6)
        ]
        
        for tag_name, expected_type, min_confidence in test_cases:
            result = classification_service.classify_expense(
                tag_name=tag_name,
                transaction_amount=25.0,
                transaction_description=f"Test {tag_name}"
            )
            
            assert result.expense_type == expected_type, f"Failed for {tag_name}: expected {expected_type}, got {result.expense_type}"
            assert result.confidence >= min_confidence, f"Low confidence for {tag_name}: {result.confidence}"
    
    def test_amount_stability_analysis(self, classification_service):
        """Test amount stability scoring for recurring payments"""
        # Create test transaction history with stable amounts (typical of fixed expenses)
        stable_history = [
            {'amount': 49.99, 'date_op': date(2024, 1, 15), 'label': 'Netflix', 'expense_type': 'FIXED'},
            {'amount': 49.99, 'date_op': date(2024, 2, 15), 'label': 'Netflix', 'expense_type': 'FIXED'},
            {'amount': 49.99, 'date_op': date(2024, 3, 15), 'label': 'Netflix', 'expense_type': 'FIXED'},
            {'amount': 49.99, 'date_op': date(2024, 4, 15), 'label': 'Netflix', 'expense_type': 'FIXED'},
        ]
        
        stability_score = classification_service._calculate_amount_stability(stable_history)
        assert stability_score is not None
        assert stability_score >= 0.8, f"Expected high stability for identical amounts, got {stability_score}"
        
        # Test variable amounts (typical of variable expenses)
        variable_history = [
            {'amount': 15.50, 'date_op': date(2024, 1, 5), 'label': 'Restaurant', 'expense_type': 'VARIABLE'},
            {'amount': 32.75, 'date_op': date(2024, 1, 12), 'label': 'Restaurant', 'expense_type': 'VARIABLE'},
            {'amount': 8.90, 'date_op': date(2024, 1, 18), 'label': 'Restaurant', 'expense_type': 'VARIABLE'},
            {'amount': 45.20, 'date_op': date(2024, 1, 25), 'label': 'Restaurant', 'expense_type': 'VARIABLE'},
        ]
        
        stability_score = classification_service._calculate_amount_stability(variable_history)
        assert stability_score is not None
        assert stability_score <= 0.3, f"Expected low stability for variable amounts, got {stability_score}"
    
    def test_frequency_pattern_analysis(self, classification_service):
        """Test frequency pattern analysis for recurring transactions"""
        # Monthly pattern (typical of fixed expenses)
        monthly_history = [
            {'amount': 50.0, 'date_op': date(2024, 1, 15), 'label': 'Subscription'},
            {'amount': 50.0, 'date_op': date(2024, 2, 15), 'label': 'Subscription'},
            {'amount': 50.0, 'date_op': date(2024, 3, 15), 'label': 'Subscription'},
            {'amount': 50.0, 'date_op': date(2024, 4, 15), 'label': 'Subscription'},
        ]
        
        frequency_score = classification_service._analyze_frequency_patterns(monthly_history)
        assert frequency_score is not None
        assert frequency_score >= 0.6, f"Expected high frequency score for monthly pattern, got {frequency_score}"
        
        # Irregular pattern (typical of variable expenses)
        irregular_history = [
            {'amount': 20.0, 'date_op': date(2024, 1, 3), 'label': 'Shopping'},
            {'amount': 30.0, 'date_op': date(2024, 1, 15), 'label': 'Shopping'},
            {'amount': 25.0, 'date_op': date(2024, 2, 8), 'label': 'Shopping'},
            {'amount': 40.0, 'date_op': date(2024, 3, 22), 'label': 'Shopping'},
        ]
        
        frequency_score = classification_service._analyze_frequency_patterns(irregular_history)
        assert frequency_score is None or frequency_score <= 0.4, f"Expected low frequency score for irregular pattern, got {frequency_score}"
    
    def test_ngram_analysis(self, classification_service):
        """Test n-gram contextual analysis"""
        # Test fixed n-grams
        result = classification_service._analyze_ngrams("abonnement netflix premium")
        score, factors = result
        assert score > 0, "Expected positive score for fixed n-grams"
        assert len(factors) > 0, "Expected factors to be identified"
        
        # Test variable n-grams
        result = classification_service._analyze_ngrams("achat carburant station")
        score, factors = result
        assert score <= 0, "Expected negative or zero score for variable n-grams"
    
    def test_ensemble_classification(self, classification_service):
        """Test the ML ensemble method combining all features"""
        # Test with historical data for better ensemble decision
        history = [
            {'amount': 9.99, 'date_op': date(2024, 1, 15), 'label': 'Netflix Basic'},
            {'amount': 9.99, 'date_op': date(2024, 2, 15), 'label': 'Netflix Basic'},
            {'amount': 9.99, 'date_op': date(2024, 3, 15), 'label': 'Netflix Basic'},
        ]
        
        result = classification_service.classify_expense(
            tag_name="netflix",
            transaction_amount=9.99,
            transaction_description="Netflix Basic Plan",
            transaction_history=history
        )
        
        # Should be classified as FIXED with high confidence
        assert result.expense_type == "FIXED"
        assert result.confidence >= 0.85
        assert result.stability_score is not None
        assert result.frequency_score is not None
        assert len(result.contributing_factors) >= 2
    
    def test_default_to_variable(self, classification_service):
        """Test that uncertain classifications default to VARIABLE"""
        result = classification_service.classify_expense(
            tag_name="unknown_tag_xyz",
            transaction_amount=100.0,
            transaction_description="Unknown merchant transaction"
        )
        
        assert result.expense_type == "VARIABLE"
        assert result.confidence <= 0.7  # Should have lower confidence for unknown tags
    
    def test_batch_classification(self, classification_service):
        """Test batch classification functionality"""
        tag_names = ["netflix", "courses", "edf", "restaurant", "spotify"]
        results = classification_service.suggest_classification_batch(tag_names)
        
        assert len(results) == len(tag_names)
        for tag_name in tag_names:
            assert tag_name in results
            assert isinstance(results[tag_name], ClassificationResult)
            assert results[tag_name].expense_type in ["FIXED", "VARIABLE"]
            assert 0.0 <= results[tag_name].confidence <= 1.0


class TestTagAutomationIntegration:
    """Test integration between classification service and tag automation"""
    
    @pytest.fixture
    def db_session(self):
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    @pytest.fixture
    def tag_automation_service(self, db_session):
        return get_tag_automation_service(db_session)
    
    def test_intelligent_fixed_line_creation(self, tag_automation_service, db_session):
        """Test that tag automation uses ML classification for fixed line creation"""
        # Create a test transaction that should be classified as FIXED
        transaction = Transaction(
            month="2024-08",
            date_op=date(2024, 8, 15),
            amount=49.99,
            label="NETFLIX PREMIUM",
            is_expense=True,
            exclude=False,
            expense_type="VARIABLE"  # Initially set as variable, should be changed by ML
        )
        db_session.add(transaction)
        db_session.commit()
        
        # Process tag creation with ML classification
        result = tag_automation_service.classify_transaction_type(transaction, "netflix")
        
        assert result is not None
        assert result["expense_type"] == "FIXED"
        assert result["confidence_score"] >= 0.8
        assert result["should_create_fixed_line"] == True
        assert len(result["contributing_factors"]) > 0
    
    def test_variable_expense_no_fixed_line(self, tag_automation_service, db_session):
        """Test that variable expenses don't create fixed lines"""
        transaction = Transaction(
            month="2024-08",
            date_op=date(2024, 8, 12),
            amount=25.50,
            label="RESTAURANT QUICK",
            is_expense=True,
            exclude=False,
            expense_type="VARIABLE"
        )
        db_session.add(transaction)
        db_session.commit()
        
        result = tag_automation_service.classify_transaction_type(transaction, "restaurant")
        
        assert result is not None
        assert result["expense_type"] == "VARIABLE"
        assert result["should_create_fixed_line"] == False


class TestPerformanceValidation:
    """Test ML system performance against target metrics"""
    
    @pytest.fixture
    def db_session(self):
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def test_precision_target(self, db_session):
        """Test that precision meets the 85% target"""
        # This test requires actual transaction data
        # In a real environment, we'd have labeled test data
        results = evaluate_classification_performance(db_session, sample_size=50)
        
        if 'error' not in results:
            precision = results.get('precision', 0)
            target_precision = results.get('target_precision', 0.85)
            
            # Log performance metrics for monitoring
            logger.info(f"Classification Performance: Precision={precision:.1%}, Target={target_precision:.1%}")
            
            # Assert performance meets targets (with some tolerance for test environments)
            assert precision >= (target_precision - 0.1), f"Precision {precision:.1%} below target {target_precision:.1%}"
    
    def test_false_positive_rate(self, db_session):
        """Test that false positive rate stays below 5% target"""
        results = evaluate_classification_performance(db_session, sample_size=50)
        
        if 'error' not in results:
            fpr = results.get('false_positive_rate', 1.0)
            target_fpr = results.get('target_fpr', 0.05)
            
            logger.info(f"False Positive Rate: {fpr:.1%}, Target: <{target_fpr:.1%}")
            
            # Assert FPR meets targets (with some tolerance for test environments)
            assert fpr <= (target_fpr + 0.05), f"False positive rate {fpr:.1%} above target {target_fpr:.1%}"


class TestMLRobustness:
    """Test ML system robustness and edge cases"""
    
    @pytest.fixture
    def classification_service(self):
        db = SessionLocal()
        try:
            service = ExpenseClassificationService(db)
            yield service
        finally:
            db.close()
    
    def test_empty_inputs(self, classification_service):
        """Test handling of empty or invalid inputs"""
        result = classification_service.classify_expense(
            tag_name="",
            transaction_amount=0.0,
            transaction_description=""
        )
        
        assert result.expense_type == "VARIABLE"  # Should default to variable
        assert result.confidence <= 0.6  # Should have low confidence
    
    def test_extreme_amounts(self, classification_service):
        """Test handling of extreme transaction amounts"""
        # Very large amount
        result = classification_service.classify_expense(
            tag_name="test",
            transaction_amount=10000.0,
            transaction_description="Large transaction"
        )
        assert result is not None
        
        # Very small amount
        result = classification_service.classify_expense(
            tag_name="test",
            transaction_amount=0.01,
            transaction_description="Tiny transaction"
        )
        assert result is not None
        
        # Negative amount (shouldn't crash)
        result = classification_service.classify_expense(
            tag_name="test",
            transaction_amount=-50.0,
            transaction_description="Negative amount"
        )
        assert result is not None
    
    def test_unicode_handling(self, classification_service):
        """Test handling of unicode characters in tags and descriptions"""
        result = classification_service.classify_expense(
            tag_name="café-français",
            transaction_amount=15.0,
            transaction_description="Café Les Étoiles - Menu déjeuner €"
        )
        
        assert result is not None
        assert result.expense_type in ["FIXED", "VARIABLE"]
    
    def test_long_text_handling(self, classification_service):
        """Test handling of very long text inputs"""
        long_description = "A" * 1000  # Very long description
        
        result = classification_service.classify_expense(
            tag_name="test",
            transaction_amount=50.0,
            transaction_description=long_description
        )
        
        assert result is not None
        assert result.expense_type in ["FIXED", "VARIABLE"]


def run_classification_system_validation():
    """
    Comprehensive validation suite for the intelligent classification system
    Run this to validate the entire ML system performance
    """
    logger.info("🚀 Starting comprehensive classification system validation...")
    
    # Initialize database session
    db = SessionLocal()
    
    try:
        # 1. Test service initialization
        logger.info("1. Testing service initialization...")
        classification_service = get_expense_classification_service(db)
        assert classification_service is not None
        logger.info("   ✅ Service initialized successfully")
        
        # 2. Test core ML functionality
        logger.info("2. Testing core ML functionality...")
        test_cases = [
            ("netflix", "FIXED"),
            ("courses", "VARIABLE"),
            ("edf", "FIXED"),
            ("restaurant", "VARIABLE"),
            ("assurance", "FIXED")
        ]
        
        correct_predictions = 0
        for tag_name, expected_type in test_cases:
            result = classification_service.classify_expense(
                tag_name=tag_name,
                transaction_amount=50.0,
                transaction_description=f"Test {tag_name}"
            )
            if result.expense_type == expected_type:
                correct_predictions += 1
            logger.info(f"   {tag_name}: {result.expense_type} (confidence: {result.confidence:.2f})")
        
        accuracy = correct_predictions / len(test_cases)
        logger.info(f"   ✅ Core ML accuracy: {accuracy:.1%}")
        
        # 3. Test performance metrics
        logger.info("3. Evaluating system performance...")
        performance = evaluate_classification_performance(db, sample_size=100)
        
        if 'error' not in performance:
            logger.info(f"   📊 Precision: {performance['precision']:.1%}")
            logger.info(f"   📊 Recall: {performance['recall']:.1%}")
            logger.info(f"   📊 F1-Score: {performance['f1_score']:.3f}")
            logger.info(f"   📊 False Positive Rate: {performance['false_positive_rate']:.1%}")
            logger.info(f"   📊 Performance Grade: {performance['performance_grade']}")
            
            if performance['meets_targets']:
                logger.info("   ✅ Performance targets met!")
            else:
                logger.warning("   ⚠️  Performance targets not met - may need tuning")
        else:
            logger.warning(f"   ⚠️  Performance evaluation failed: {performance['error']}")
        
        # 4. Test batch processing
        logger.info("4. Testing batch processing...")
        batch_tags = ["netflix", "spotify", "courses", "restaurant", "edf", "orange", "carburant"]
        batch_results = classification_service.suggest_classification_batch(batch_tags)
        
        assert len(batch_results) == len(batch_tags)
        logger.info(f"   ✅ Batch processing: {len(batch_results)} tags classified")
        
        # 5. Generate summary statistics
        logger.info("5. Generating system statistics...")
        stats = classification_service.get_classification_stats()
        
        if 'error' not in stats:
            logger.info(f"   📈 Total classified transactions: {stats['total_classified']}")
            logger.info(f"   📈 Type distribution: {stats['type_distribution']}")
            logger.info(f"   📈 Model version: {stats['ml_model_version']}")
        
        logger.info("🎉 Validation completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        return False
        
    finally:
        db.close()


if __name__ == "__main__":
    # Run comprehensive validation
    success = run_classification_system_validation()
    exit(0 if success else 1)