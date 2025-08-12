"""
Unified ML Tagging Service
Production-ready service integrating all ML capabilities for intelligent tagging

This service provides:
1. High-accuracy tag suggestions with confidence scoring
2. Fixed vs Variable expense classification
3. Web research integration for unknown merchants
4. Continuous learning from user feedback
5. Batch processing with performance optimization

Author: Claude Code - ML Operations Engineer
Performance Targets:
- >85% accuracy for known merchants
- >60% accuracy for unknown merchants via web research
- <50ms response time for cached results
- <2s response time with web research
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session

# Import ML and research services
from services.ml_tagging_engine import MLTaggingEngine, MLTagResult, get_ml_tagging_engine
from services.intelligent_tag_service import IntelligentTagService, IntelligentTagResult, get_intelligent_tag_service
from services.web_research_service import WebResearchService, MerchantInfo

logger = logging.getLogger(__name__)


@dataclass
class UnifiedTagSuggestion:
    """Unified tag suggestion with all ML insights"""
    # Primary suggestion
    tag: str
    confidence: float
    should_auto_apply: bool
    
    # Classification
    expense_type: str  # FIXED or VARIABLE
    merchant_category: Optional[str] = None
    
    # Confidence breakdown
    pattern_confidence: float = 0.0
    web_confidence: float = 0.0
    learning_confidence: float = 0.0
    context_confidence: float = 0.0
    
    # Explainability
    explanation: str = ""
    confidence_factors: Dict[str, float] = None
    
    # Alternatives
    alternative_tags: List[str] = None
    all_suggestions: List[Tuple[str, float]] = None
    
    # Merchant info
    merchant_name: Optional[str] = None
    merchant_clean: Optional[str] = None
    business_type: Optional[str] = None
    
    # Data sources
    sources_used: List[str] = None
    web_research_performed: bool = False
    cache_hit: bool = False
    
    # Performance
    processing_time_ms: int = 0
    
    # Learning signals
    user_feedback_applied: bool = False
    recurring_pattern_detected: bool = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            'tag': self.tag,
            'confidence': round(self.confidence, 3),
            'should_auto_apply': self.should_auto_apply,
            'expense_type': self.expense_type,
            'explanation': self.explanation,
            'alternatives': self.alternative_tags or [],
            'merchant': {
                'name': self.merchant_name,
                'category': self.merchant_category,
                'business_type': self.business_type
            },
            'confidence_breakdown': {
                'pattern': round(self.pattern_confidence, 2),
                'web': round(self.web_confidence, 2),
                'learning': round(self.learning_confidence, 2),
                'context': round(self.context_confidence, 2)
            },
            'metadata': {
                'sources': self.sources_used or [],
                'web_research': self.web_research_performed,
                'cached': self.cache_hit,
                'processing_ms': self.processing_time_ms,
                'recurring': self.recurring_pattern_detected
            }
        }


class UnifiedMLTaggingService:
    """
    Unified service orchestrating all ML tagging capabilities
    
    This service integrates:
    - ML pattern matching engine
    - Web research capabilities
    - Intelligent tag suggestions
    - User feedback learning
    - Recurring pattern detection
    """
    
    # Confidence thresholds
    AUTO_APPLY_THRESHOLD = 0.80  # 80% minimum for auto-application
    MEDIUM_CONFIDENCE = 0.60     # 60-79% for suggestions
    LOW_CONFIDENCE = 0.50         # Below 50% - do not suggest
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
        # Initialize sub-services
        self.ml_engine = get_ml_tagging_engine(db_session)
        self.intelligent_service = get_intelligent_tag_service(db_session)
        
        # Statistics
        self.stats = {
            'total_suggestions': 0,
            'auto_applied': 0,
            'web_research_used': 0,
            'cache_hits': 0,
            'user_corrections': 0
        }
        
        logger.info("Unified ML Tagging Service initialized with all capabilities")
    
    async def suggest_tag_unified(
        self,
        transaction_label: str,
        amount: float = None,
        transaction_date: datetime = None,
        transaction_history: List[Dict] = None,
        use_web_research: bool = True
    ) -> UnifiedTagSuggestion:
        """
        Main method: Provide unified tag suggestion with all ML insights
        
        Args:
            transaction_label: Transaction description
            amount: Transaction amount
            transaction_date: Date of transaction
            transaction_history: Previous transactions for pattern detection
            use_web_research: Whether to use web research
            
        Returns:
            UnifiedTagSuggestion with comprehensive analysis
        """
        start_time = datetime.now()
        self.stats['total_suggestions'] += 1
        
        # Step 1: ML Engine Analysis (Pattern matching + confidence scoring)
        ml_result = await self.ml_engine.suggest_tag(
            transaction_label=transaction_label,
            amount=amount,
            use_web_research=False  # We'll handle web research separately
        )
        
        # Step 2: Intelligent Service Analysis (with web research if needed)
        intelligent_result = None
        if use_web_research and ml_result.confidence < self.AUTO_APPLY_THRESHOLD:
            try:
                intelligent_result = await self.intelligent_service.suggest_tag_with_research(
                    transaction_label=transaction_label,
                    amount=amount
                )
                self.stats['web_research_used'] += 1
            except Exception as e:
                logger.warning(f"Web research failed: {e}")
        
        # Step 3: Detect recurring patterns if history provided
        recurring_pattern = False
        fixed_expense_confidence = 0.0
        
        if transaction_history:
            patterns = self.ml_engine.detect_recurring_patterns(transaction_history)
            merchant_clean = ml_result.merchant_name_clean
            
            if merchant_clean and merchant_clean in patterns:
                pattern_info = patterns[merchant_clean]
                if pattern_info.get('is_fixed'):
                    recurring_pattern = True
                    fixed_expense_confidence = pattern_info.get('consistency_score', 0)
        
        # Step 4: Combine results for unified suggestion
        final_tag = ml_result.suggested_tag
        final_confidence = ml_result.confidence
        sources_used = ['ml_patterns']
        
        # Use intelligent service result if it has higher confidence
        if intelligent_result and intelligent_result.confidence > ml_result.confidence:
            final_tag = intelligent_result.suggested_tag
            final_confidence = intelligent_result.confidence
            sources_used.append('web_research')
        
        # Boost confidence for recurring patterns
        if recurring_pattern:
            final_confidence = min(final_confidence * 1.1, 0.99)
            sources_used.append('recurring_pattern')
        
        # Determine if we should auto-apply
        should_auto_apply = final_confidence >= self.AUTO_APPLY_THRESHOLD
        
        if should_auto_apply:
            self.stats['auto_applied'] += 1
        
        # Classify expense type
        expense_type = self.ml_engine.classify_expense_type(
            merchant_info={'type': ml_result.expense_type} if ml_result.expense_type else None,
            amount=amount,
            transaction_history=transaction_history
        )
        
        # Override to FIXED if recurring pattern detected
        if recurring_pattern and fixed_expense_confidence > 0.8:
            expense_type = 'FIXED'
        
        # Build comprehensive explanation
        explanation_parts = []
        
        if final_confidence >= self.AUTO_APPLY_THRESHOLD:
            explanation_parts.append(f"Haute confiance ({final_confidence:.0%})")
        elif final_confidence >= self.MEDIUM_CONFIDENCE:
            explanation_parts.append(f"Confiance moyenne ({final_confidence:.0%})")
        else:
            explanation_parts.append(f"Confiance faible ({final_confidence:.0%})")
        
        if ml_result.merchant_name_clean:
            explanation_parts.append(f"Marchand: {ml_result.merchant_name_clean}")
        
        if recurring_pattern:
            explanation_parts.append("Pattern récurrent détecté")
        
        if intelligent_result and intelligent_result.web_research_used:
            explanation_parts.append("Vérifié par recherche web")
        
        explanation = " - ".join(explanation_parts)
        
        # Prepare alternatives
        alternatives = []
        if ml_result.alternative_tags:
            alternatives.extend(ml_result.alternative_tags[:3])
        if intelligent_result and intelligent_result.alternative_tags:
            for alt in intelligent_result.alternative_tags:
                if alt not in alternatives:
                    alternatives.append(alt)
        alternatives = alternatives[:5]  # Limit to 5 alternatives
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Create unified result
        return UnifiedTagSuggestion(
            tag=final_tag if final_confidence >= self.LOW_CONFIDENCE else 'aucun',
            confidence=final_confidence,
            should_auto_apply=should_auto_apply,
            expense_type=expense_type,
            merchant_category=ml_result.merchant_category,
            pattern_confidence=ml_result.confidence_factors.pattern_match_score,
            web_confidence=intelligent_result.confidence if intelligent_result else 0,
            learning_confidence=ml_result.confidence_factors.user_feedback_score,
            context_confidence=ml_result.confidence_factors.context_score,
            explanation=explanation,
            confidence_factors={
                'pattern': ml_result.confidence_factors.pattern_match_score,
                'web': intelligent_result.confidence if intelligent_result else 0,
                'learning': ml_result.confidence_factors.user_feedback_score,
                'context': ml_result.confidence_factors.context_score
            },
            alternative_tags=alternatives,
            all_suggestions=ml_result.all_suggestions,
            merchant_name=transaction_label,
            merchant_clean=ml_result.merchant_name_clean,
            business_type=intelligent_result.business_category if intelligent_result else ml_result.web_business_type,
            sources_used=sources_used,
            web_research_performed=(intelligent_result is not None),
            cache_hit=ml_result.cache_hit,
            processing_time_ms=processing_time,
            user_feedback_applied=ml_result.user_correction_applied,
            recurring_pattern_detected=recurring_pattern
        )
    
    def suggest_tag_fast(self, transaction_label: str, amount: float = None) -> UnifiedTagSuggestion:
        """Fast synchronous suggestion without web research"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.suggest_tag_unified(
                    transaction_label=transaction_label,
                    amount=amount,
                    use_web_research=False
                )
            )
        finally:
            loop.close()
    
    async def batch_suggest_tags(
        self,
        transactions: List[Dict],
        use_web_research: bool = False,
        detect_patterns: bool = True
    ) -> Dict[int, UnifiedTagSuggestion]:
        """
        Batch process multiple transactions with pattern detection
        
        Args:
            transactions: List of transaction dicts
            use_web_research: Whether to use web research
            detect_patterns: Whether to detect recurring patterns
            
        Returns:
            Dict mapping transaction ID to UnifiedTagSuggestion
        """
        results = {}
        
        # Detect recurring patterns if requested
        patterns = {}
        if detect_patterns and len(transactions) > 1:
            patterns = self.ml_engine.detect_recurring_patterns(transactions)
        
        # Process each transaction
        for tx in transactions:
            tx_id = tx.get('id')
            if tx_id is None:
                continue
            
            # Get transaction history for this merchant if patterns detected
            tx_history = None
            if patterns:
                merchant_clean = self.ml_engine._clean_merchant_name(tx.get('label', ''))
                if merchant_clean in patterns:
                    # Find all transactions for this merchant
                    tx_history = [
                        t for t in transactions 
                        if self.ml_engine._clean_merchant_name(t.get('label', '')) == merchant_clean
                    ]
            
            # Get suggestion
            suggestion = await self.suggest_tag_unified(
                transaction_label=tx.get('label', ''),
                amount=tx.get('amount'),
                transaction_date=tx.get('date'),
                transaction_history=tx_history,
                use_web_research=use_web_research
            )
            
            results[tx_id] = suggestion
        
        return results
    
    def learn_from_feedback(
        self,
        transaction_label: str,
        suggested_tag: str,
        actual_tag: str,
        was_accepted: bool
    ):
        """Process user feedback to improve future suggestions"""
        self.ml_engine.learn_from_correction(
            transaction_label=transaction_label,
            suggested_tag=suggested_tag,
            actual_tag=actual_tag,
            was_accepted=was_accepted
        )
        
        if not was_accepted:
            self.stats['user_corrections'] += 1
        
        logger.info(
            f"Learning: '{transaction_label}' - "
            f"Suggested: '{suggested_tag}' -> Actual: '{actual_tag}' "
            f"(Accepted: {was_accepted})"
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        ml_stats = self.ml_engine.get_statistics()
        
        total = max(self.stats['total_suggestions'], 1)
        
        return {
            'service': 'UnifiedMLTaggingService',
            'version': '3.0.0',
            'performance': {
                'total_suggestions': self.stats['total_suggestions'],
                'auto_applied': self.stats['auto_applied'],
                'auto_apply_rate': f"{(self.stats['auto_applied'] / total * 100):.1f}%",
                'web_research_usage': f"{(self.stats['web_research_used'] / total * 100):.1f}%",
                'cache_hit_rate': f"{(self.stats['cache_hits'] / total * 100):.1f}%",
                'user_corrections': self.stats['user_corrections']
            },
            'ml_engine': ml_stats,
            'thresholds': {
                'auto_apply': f"{self.AUTO_APPLY_THRESHOLD:.0%}",
                'medium_confidence': f"{self.MEDIUM_CONFIDENCE:.0%}",
                'low_confidence': f"{self.LOW_CONFIDENCE:.0%}"
            },
            'capabilities': {
                'pattern_matching': True,
                'web_research': True,
                'user_learning': True,
                'recurring_detection': True,
                'expense_classification': True,
                'batch_processing': True,
                'multi_factor_confidence': True
            }
        }


# Service management
_unified_service_instance = None

def get_unified_ml_tagging_service(db_session: Session) -> UnifiedMLTaggingService:
    """Get singleton instance of Unified ML Tagging Service"""
    global _unified_service_instance
    
    if _unified_service_instance is None:
        _unified_service_instance = UnifiedMLTaggingService(db_session)
        logger.info("Unified ML Tagging Service initialized successfully")
    
    return _unified_service_instance


# Example usage and testing
async def test_unified_service():
    """Test the unified ML tagging service"""
    
    # Mock database session
    class MockDB:
        pass
    
    service = UnifiedMLTaggingService(MockDB())
    
    print("Testing Unified ML Tagging Service")
    print("=" * 80)
    
    # Test cases
    test_cases = [
        {
            'label': 'NETFLIX SARL 12.99',
            'amount': 12.99,
            'expected': 'streaming',
            'scenario': 'Known subscription'
        },
        {
            'label': 'CARREFOUR MARKET LYON',
            'amount': 67.45,
            'expected': 'courses',
            'scenario': 'Known supermarket'
        },
        {
            'label': 'RESTAURANT LE BISTRO',
            'amount': 45.00,
            'expected': 'restaurant',
            'scenario': 'Restaurant pattern'
        },
        {
            'label': 'UNKNOWN MERCHANT XYZ',
            'amount': 100.00,
            'expected': 'aucun',
            'scenario': 'Unknown merchant'
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['scenario']}")
        print(f"Transaction: {test['label']} ({test['amount']}€)")
        print("-" * 40)
        
        result = await service.suggest_tag_unified(
            transaction_label=test['label'],
            amount=test['amount'],
            use_web_research=False  # Disable for testing
        )
        
        print(f"Suggested Tag: {result.tag}")
        print(f"Confidence: {result.confidence:.1%}")
        print(f"Auto-Apply: {'Yes' if result.should_auto_apply else 'No'}")
        print(f"Expense Type: {result.expense_type}")
        print(f"Explanation: {result.explanation}")
        
        if result.confidence_factors:
            print("Confidence Breakdown:")
            for factor, score in result.confidence_factors.items():
                if score > 0:
                    print(f"  - {factor}: {score:.0%}")
        
        if result.alternative_tags:
            print(f"Alternatives: {', '.join(result.alternative_tags[:3])}")
        
        # Check expectation
        if test['expected'] == result.tag or (test['expected'] == 'aucun' and result.confidence < 0.5):
            print("✓ PASS: Expected result achieved")
        else:
            print(f"✗ FAIL: Expected '{test['expected']}', got '{result.tag}'")
    
    # Test batch processing with pattern detection
    print("\n" + "=" * 80)
    print("Testing Batch Processing with Pattern Detection")
    print("-" * 40)
    
    batch_transactions = [
        {'id': 1, 'label': 'NETFLIX', 'amount': 12.99, 'date': '2024-01-15'},
        {'id': 2, 'label': 'NETFLIX', 'amount': 12.99, 'date': '2024-02-15'},
        {'id': 3, 'label': 'NETFLIX', 'amount': 12.99, 'date': '2024-03-15'},
        {'id': 4, 'label': 'CARREFOUR', 'amount': 67.45, 'date': '2024-03-10'},
        {'id': 5, 'label': 'CARREFOUR', 'amount': 89.20, 'date': '2024-03-17'}
    ]
    
    batch_results = await service.batch_suggest_tags(
        transactions=batch_transactions,
        detect_patterns=True
    )
    
    for tx_id, result in batch_results.items():
        tx = next(t for t in batch_transactions if t['id'] == tx_id)
        print(f"\nTX {tx_id}: {tx['label']} ({tx['amount']}€)")
        print(f"  Tag: {result.tag} ({result.confidence:.0%})")
        print(f"  Type: {result.expense_type}")
        if result.recurring_pattern_detected:
            print(f"  ✓ Recurring pattern detected!")
    
    # Display statistics
    print("\n" + "=" * 80)
    print("Service Statistics")
    print("-" * 40)
    
    stats = service.get_statistics()
    for category, data in stats.items():
        if isinstance(data, dict):
            print(f"\n{category.upper()}:")
            for key, value in data.items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for k, v in value.items():
                        print(f"    {k}: {v}")
                else:
                    print(f"  {key}: {value}")
        else:
            print(f"{category}: {data}")


if __name__ == "__main__":
    asyncio.run(test_unified_service())