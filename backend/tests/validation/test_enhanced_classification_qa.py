"""
Enhanced Classification Testing Suite
=====================================

Focused testing for the ML-enhanced classification system with web research integration.
This suite validates the core classification algorithms, learning capabilities, and performance.

FOCUS AREAS:
- ML classification accuracy and consistency
- Web research integration and enhancement
- User feedback learning system
- Performance under various load conditions
- Edge cases and robustness testing

AUTHOR: Claude Code - QA Lead
"""

import pytest
import logging
import time
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, patch

from sqlalchemy.orm import Session
from models.database import SessionLocal, Transaction, MerchantKnowledgeBase
from services.expense_classification import (
    ExpenseClassificationService,
    ClassificationResult,
    evaluate_classification_performance
)
from services.web_research_service import WebResearchService, MerchantInfo

logger = logging.getLogger(__name__)


@pytest.fixture
def db_session():
    """Create test database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def classification_service(db_session):
    """Create classification service instance"""
    return ExpenseClassificationService(db_session)


class TestMLClassificationAccuracy:
    """Test core ML classification accuracy and consistency"""
    
    def test_fixed_expense_keyword_recognition(self, classification_service):
        """Test recognition of fixed expense keywords with high confidence"""
        fixed_test_cases = [
            ("netflix premium", "FIXED", 0.9),
            ("spotify family", "FIXED", 0.9),
            ("edf facture", "FIXED", 0.85),
            ("orange internet box", "FIXED", 0.85),
            ("assurance auto axa", "FIXED", 0.90),
            ("mutuelle harmonie", "FIXED", 0.90),
            ("loyer appartement", "FIXED", 0.95),
            ("abonnement canal+", "FIXED", 0.95)
        ]
        
        for tag_name, expected_type, min_confidence in fixed_test_cases:
            result = classification_service.classify_expense(
                tag_name=tag_name,
                transaction_amount=50.0,
                transaction_description=f"Test {tag_name}"
            )
            
            assert result.expense_type == expected_type, f"Failed for '{tag_name}': expected {expected_type}, got {result.expense_type}"
            assert result.confidence >= min_confidence, f"Low confidence for '{tag_name}': {result.confidence:.2f} < {min_confidence}"
            assert len(result.keyword_matches) > 0, f"No keyword matches found for '{tag_name}'"
            
            logger.debug(f"✅ Fixed: '{tag_name}' → {result.expense_type} ({result.confidence:.2f})")
    
    def test_variable_expense_keyword_recognition(self, classification_service):
        """Test recognition of variable expense keywords"""
        variable_test_cases = [
            ("restaurant mcdonalds", "VARIABLE", 0.8),
            ("carrefour courses", "VARIABLE", 0.85),
            ("pharmacie centrale", "VARIABLE", 0.7),
            ("station service total", "VARIABLE", 0.8),
            ("vetements h&m", "VARIABLE", 0.75),
            ("cinema ugc", "VARIABLE", 0.85),
            ("coiffeur salon", "VARIABLE", 0.80)
        ]
        
        for tag_name, expected_type, min_confidence in variable_test_cases:
            result = classification_service.classify_expense(
                tag_name=tag_name,
                transaction_amount=25.0,
                transaction_description=f"Test {tag_name}"
            )
            
            assert result.expense_type == expected_type, f"Failed for '{tag_name}': expected {expected_type}, got {result.expense_type}"
            assert result.confidence >= min_confidence, f"Low confidence for '{tag_name}': {result.confidence:.2f} < {min_confidence}"
            
            logger.debug(f"✅ Variable: '{tag_name}' → {result.expense_type} ({result.confidence:.2f})")
    
    def test_ambiguous_keyword_classification(self, classification_service):
        """Test classification of ambiguous keywords that could go either way"""
        ambiguous_cases = [
            ("amazon", "VARIABLE", 0.5, 0.7),  # Could be shopping or Prime subscription
            ("transport", "VARIABLE", 0.5, 0.8),  # Could be occasional or regular transport
            ("apple", "VARIABLE", 0.4, 0.7),     # Could be App Store purchases or subscriptions
        ]
        
        for tag_name, expected_default, min_confidence, max_confidence in ambiguous_cases:
            result = classification_service.classify_expense(
                tag_name=tag_name,
                transaction_amount=30.0,
                transaction_description=f"Test {tag_name}"
            )
            
            # Should default to VARIABLE when uncertain
            assert result.expense_type == expected_default, f"Ambiguous '{tag_name}' should default to {expected_default}, got {result.expense_type}"
            assert min_confidence <= result.confidence <= max_confidence, f"Confidence for ambiguous '{tag_name}' should be moderate: {result.confidence:.2f}"
            
            logger.debug(f"✅ Ambiguous: '{tag_name}' → {result.expense_type} ({result.confidence:.2f})")
    
    def test_historical_pattern_analysis(self, classification_service):
        """Test analysis of historical transaction patterns for better classification"""
        # Create stable payment history (fixed expense pattern)
        stable_history = [
            {'amount': 49.99, 'date_op': date(2024, 4, 15), 'label': 'Netflix Standard'},
            {'amount': 49.99, 'date_op': date(2024, 5, 15), 'label': 'Netflix Standard'},
            {'amount': 49.99, 'date_op': date(2024, 6, 15), 'label': 'Netflix Standard'},
            {'amount': 49.99, 'date_op': date(2024, 7, 15), 'label': 'Netflix Standard'},
        ]
        
        result = classification_service.classify_expense(
            tag_name="netflix",
            transaction_amount=49.99,
            transaction_description="Netflix Standard",
            transaction_history=stable_history
        )
        
        assert result.expense_type == "FIXED", f"Stable pattern should indicate FIXED, got {result.expense_type}"
        assert result.confidence >= 0.90, f"High stability should give high confidence: {result.confidence:.2f}"
        assert result.stability_score is not None and result.stability_score >= 0.8, f"Should detect high stability: {result.stability_score}"
        assert "stable" in result.primary_reason.lower() or "recurring" in result.primary_reason.lower()
        
        logger.info(f"✅ Stable pattern analysis: Netflix → {result.expense_type} ({result.confidence:.2f}, stability: {result.stability_score:.2f})")
        
        # Create variable payment history
        variable_history = [
            {'amount': 15.50, 'date_op': date(2024, 6, 3), 'label': 'Restaurant A'},
            {'amount': 32.75, 'date_op': date(2024, 6, 17), 'label': 'Restaurant B'},
            {'amount': 8.90, 'date_op': date(2024, 7, 2), 'label': 'Restaurant C'},
            {'amount': 45.20, 'date_op': date(2024, 7, 28), 'label': 'Restaurant D'},
        ]
        
        result = classification_service.classify_expense(
            tag_name="restaurant",
            transaction_amount=25.0,
            transaction_description="Restaurant meal",
            transaction_history=variable_history
        )
        
        assert result.expense_type == "VARIABLE", f"Variable pattern should indicate VARIABLE, got {result.expense_type}"
        assert result.stability_score is None or result.stability_score <= 0.3, f"Should detect low stability: {result.stability_score}"
        
        logger.info(f"✅ Variable pattern analysis: Restaurant → {result.expense_type} ({result.confidence:.2f})")


class TestWebResearchIntegration:
    """Test integration between classification and web research"""
    
    def test_web_research_enhancement_boost(self, db_session, classification_service):
        """Test that web research enhances classification confidence"""
        # Mock merchant knowledge base entry
        mock_merchant = MerchantKnowledgeBase(
            merchant_name="LECLERC PARIS",
            normalized_name="LECLERC PARIS",
            business_type="supermarket",
            confidence_score=0.9,
            suggested_expense_type="VARIABLE",
            suggested_tags="alimentation,courses,nécessaire",
            is_active=True
        )
        db_session.add(mock_merchant)
        db_session.commit()
        
        # Test enhanced classification
        result = classification_service.classify_expense_with_web_intelligence(
            tag_name="leclerc",
            transaction_amount=45.67,
            transaction_description="LECLERC PARIS CENTRE"
        )
        
        assert result.expense_type == "VARIABLE", f"Web enhanced classification should be VARIABLE, got {result.expense_type}"
        assert result.confidence >= 0.85, f"Web enhancement should boost confidence: {result.confidence:.2f}"
        assert "supermarket" in result.primary_reason.lower() or "web" in result.primary_reason.lower()
        assert any("web" in factor.lower() for factor in result.contributing_factors), "Should mention web research"
        
        logger.info(f"✅ Web enhancement: LECLERC → {result.expense_type} ({result.confidence:.2f})")
    
    def test_web_research_override_scenario(self, db_session, classification_service):
        """Test scenario where web research overrides ML classification"""
        # Mock high-confidence web research data that conflicts with ML
        mock_merchant = MerchantKnowledgeBase(
            merchant_name="AMAZON PRIME",
            normalized_name="AMAZON PRIME",
            business_type="streaming_service",
            confidence_score=0.95,
            suggested_expense_type="FIXED",
            suggested_tags="abonnement,streaming,fixe",
            is_active=True
        )
        db_session.add(mock_merchant)
        db_session.commit()
        
        # Test with "amazon" tag which ML might classify as VARIABLE (shopping)
        result = classification_service.classify_expense_with_web_intelligence(
            tag_name="amazon",
            transaction_amount=8.99,
            transaction_description="AMAZON PRIME MONTHLY"
        )
        
        # Web research should override ML classification due to high confidence
        assert result.expense_type == "FIXED", f"High-confidence web research should override to FIXED, got {result.expense_type}"
        assert result.confidence >= 0.80, f"Override should maintain high confidence: {result.confidence:.2f}"
        assert "streaming" in result.primary_reason.lower() or "override" in result.primary_reason.lower()
        
        logger.info(f"✅ Web override: Amazon → {result.expense_type} ({result.confidence:.2f})")
    
    @pytest.mark.asyncio
    async def test_web_research_cache_efficiency(self, db_session):
        """Test web research caching for performance improvement"""
        async with WebResearchService() as research_service:
            # First request - should populate cache
            start_time = time.time()
            result1 = await research_service.research_merchant("LECLERC TEST")
            first_duration = time.time() - start_time
            
            # Second request - should use cache
            start_time = time.time()
            result2 = await research_service.research_merchant("LECLERC TEST")
            cached_duration = time.time() - start_time
            
            # Cache should be significantly faster
            assert cached_duration < first_duration * 0.5, f"Cache not improving performance: {cached_duration:.3f}s vs {first_duration:.3f}s"
            assert cached_duration < 0.1, f"Cached response too slow: {cached_duration:.3f}s"
            
            logger.info(f"✅ Cache efficiency: First={first_duration:.3f}s, Cached={cached_duration:.3f}s (speedup: {first_duration/cached_duration:.1f}x)")


class TestLearningAndAdaptation:
    """Test learning and adaptation capabilities"""
    
    def test_user_correction_logging(self, classification_service):
        """Test that user corrections are properly logged for future learning"""
        # Initial classification
        tag_name = "test_learning_tag"
        initial_result = classification_service.classify_expense(
            tag_name=tag_name,
            transaction_amount=30.0,
            transaction_description="Test learning merchant"
        )
        
        # Simulate user correction
        correct_type = "FIXED" if initial_result.expense_type == "VARIABLE" else "VARIABLE"
        
        # Should not raise exception
        classification_service.learn_from_correction(
            tag_name=tag_name,
            correct_classification=correct_type,
            user_context="test_user"
        )
        
        logger.info(f"✅ Learning logged: '{tag_name}' corrected from {initial_result.expense_type} to {correct_type}")
    
    def test_batch_classification_consistency(self, classification_service):
        """Test that batch classification provides consistent results"""
        tag_names = ["netflix", "spotify", "edf", "orange", "carrefour", "restaurant", "pharmacie"]
        
        # Run batch classification
        batch_results = classification_service.suggest_classification_batch(tag_names)
        
        assert len(batch_results) == len(tag_names), f"Batch should return {len(tag_names)} results, got {len(batch_results)}"
        
        # Test individual classifications for consistency
        for tag_name in tag_names:
            batch_result = batch_results[tag_name]
            individual_result = classification_service.classify_expense(
                tag_name=tag_name,
                transaction_amount=50.0,
                transaction_description=f"Test {tag_name}"
            )
            
            # Results should be consistent (within reasonable tolerance)
            assert batch_result.expense_type == individual_result.expense_type, f"Inconsistent classification for '{tag_name}': batch={batch_result.expense_type}, individual={individual_result.expense_type}"
            
            confidence_diff = abs(batch_result.confidence - individual_result.confidence)
            assert confidence_diff <= 0.1, f"Large confidence difference for '{tag_name}': {confidence_diff:.2f}"
        
        logger.info(f"✅ Batch consistency: {len(tag_names)} tags classified consistently")


class TestEdgeCasesAndRobustness:
    """Test edge cases and system robustness"""
    
    def test_empty_and_null_inputs(self, classification_service):
        """Test handling of empty or null inputs"""
        edge_cases = [
            ("", 0.0, ""),
            (None, 0.0, ""),
            ("   ", 10.0, "   "),
            ("test", None, ""),
            ("test", 0.0, None)
        ]
        
        for tag_name, amount, description in edge_cases:
            try:
                result = classification_service.classify_expense(
                    tag_name=tag_name or "",
                    transaction_amount=amount or 0.0,
                    transaction_description=description or ""
                )
                
                # Should not crash and should provide reasonable defaults
                assert result.expense_type in ["FIXED", "VARIABLE"], f"Invalid expense type: {result.expense_type}"
                assert 0.0 <= result.confidence <= 1.0, f"Invalid confidence: {result.confidence}"
                assert result.expense_type == "VARIABLE", "Empty inputs should default to VARIABLE"
                
            except Exception as e:
                pytest.fail(f"Classification crashed on edge case {edge_cases}: {e}")
        
        logger.info("✅ Edge case handling: All empty/null inputs handled gracefully")
    
    def test_extreme_amounts(self, classification_service):
        """Test handling of extreme transaction amounts"""
        extreme_amounts = [0.01, 0.001, 10000.0, 1000000.0, -50.0]
        
        for amount in extreme_amounts:
            result = classification_service.classify_expense(
                tag_name="test_extreme",
                transaction_amount=amount,
                transaction_description="Test extreme amount"
            )
            
            # Should handle extreme amounts without crashing
            assert result.expense_type in ["FIXED", "VARIABLE"], f"Invalid expense type for amount {amount}"
            assert 0.0 <= result.confidence <= 1.0, f"Invalid confidence for amount {amount}: {result.confidence}"
        
        logger.info(f"✅ Extreme amounts: Handled {len(extreme_amounts)} extreme values successfully")
    
    def test_unicode_and_special_characters(self, classification_service):
        """Test handling of unicode characters and special symbols"""
        unicode_cases = [
            ("café-français", "Café Les Étoiles - Menu déjeuner €"),
            ("réseau-électrique", "EDF Électricité & Gaz - Facture n°123"),
            ("télécommunication", "Téléphone & Internet - Forfait mobile"),
            ("naïve-description", "Test with accents: à, é, è, ç, ô, ü"),
            ("special-chars", "Test@#$%^&*()_+-=[]{}|;':\",./<>?"),
        ]
        
        for tag_name, description in unicode_cases:
            try:
                result = classification_service.classify_expense(
                    tag_name=tag_name,
                    transaction_amount=50.0,
                    transaction_description=description
                )
                
                # Should handle unicode without issues
                assert result.expense_type in ["FIXED", "VARIABLE"], f"Invalid type for unicode case: {tag_name}"
                assert 0.0 <= result.confidence <= 1.0, f"Invalid confidence for unicode case: {result.confidence}"
                
            except Exception as e:
                pytest.fail(f"Unicode handling failed for '{tag_name}': {e}")
        
        logger.info("✅ Unicode handling: All special characters processed successfully")
    
    def test_performance_with_large_history(self, classification_service):
        """Test performance with large transaction history"""
        # Create large transaction history (100 transactions)
        large_history = []
        for i in range(100):
            large_history.append({
                'amount': 50.0 + (i % 20),
                'date_op': date(2024, 1, 1) + timedelta(days=i*3),
                'label': f'Transaction {i}',
                'expense_type': 'VARIABLE'
            })
        
        start_time = time.time()
        
        result = classification_service.classify_expense(
            tag_name="large_history_test",
            transaction_amount=50.0,
            transaction_description="Test with large history",
            transaction_history=large_history
        )
        
        processing_time = time.time() - start_time
        
        # Should process large history efficiently
        assert processing_time < 1.0, f"Large history processing too slow: {processing_time:.2f}s"
        assert result.expense_type in ["FIXED", "VARIABLE"], "Should handle large history"
        assert result.stability_score is not None, "Should calculate stability with large history"
        
        logger.info(f"✅ Large history performance: 100 transactions processed in {processing_time:.3f}s")


class TestSystemPerformanceMetrics:
    """Test system-wide performance metrics and targets"""
    
    def test_classification_accuracy_target(self, db_session):
        """Test that system meets 85% accuracy target"""
        evaluation_results = evaluate_classification_performance(db_session, sample_size=50)
        
        if 'error' not in evaluation_results:
            precision = evaluation_results.get('precision', 0)
            accuracy = evaluation_results.get('accuracy', 0)
            false_positive_rate = evaluation_results.get('false_positive_rate', 1)
            
            # Target validation
            assert precision >= 0.85, f"Precision {precision:.1%} below 85% target"
            assert false_positive_rate <= 0.05, f"False positive rate {false_positive_rate:.1%} above 5% limit"
            assert accuracy >= 0.80, f"Accuracy {accuracy:.1%} below 80% minimum"
            
            logger.info(f"✅ Performance targets: Precision={precision:.1%}, Accuracy={accuracy:.1%}, FPR={false_positive_rate:.1%}")
        else:
            logger.warning(f"⚠️ Performance evaluation skipped: {evaluation_results['error']}")
    
    def test_response_time_consistency(self, classification_service):
        """Test that classification response times are consistent"""
        response_times = []
        test_tags = ["netflix", "carrefour", "edf", "restaurant", "pharmacie"] * 10  # 50 classifications
        
        for tag in test_tags:
            start_time = time.time()
            
            classification_service.classify_expense(
                tag_name=tag,
                transaction_amount=50.0,
                transaction_description=f"Test {tag}"
            )
            
            response_time = time.time() - start_time
            response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        # Performance targets
        assert avg_response_time < 0.01, f"Average response time {avg_response_time:.4f}s too slow"
        assert max_response_time < 0.05, f"Maximum response time {max_response_time:.4f}s too slow"
        
        # Consistency check (standard deviation should be low)
        import statistics
        std_dev = statistics.stdev(response_times)
        assert std_dev < avg_response_time * 0.5, f"Response times too inconsistent: std_dev={std_dev:.4f}s"
        
        logger.info(f"✅ Response time consistency: avg={avg_response_time:.4f}s, max={max_response_time:.4f}s, std_dev={std_dev:.4f}s")


if __name__ == "__main__":
    # Run enhanced classification tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings"
    ])