"""
Unified Classification Service - Priority: Tag Suggestions over FIXED/VARIABLE

This service replaces the traditional FIXED/VARIABLE classification approach
with intelligent contextual tag suggestions based on web research and ML analysis.

PRIORITY SYSTEM:
1. Contextual Tag Suggestions (Netflix → "streaming")
2. Web Research Enhancement (McDonald's → "fast-food")
3. Fallback to intelligent categorization
4. Optional expense type classification for backward compatibility

Author: Claude Code - ML Operations Engineer
Target: >85% precision with contextual tag accuracy
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy.orm import Session

# Import existing services
from services.tag_suggestion_service import TagSuggestionService, TagSuggestionResult, get_tag_suggestion_service
from services.expense_classification import ExpenseClassificationService, ClassificationResult, get_expense_classification_service
from services.web_research_service import WebResearchService
from models.database import Transaction

logger = logging.getLogger(__name__)

@dataclass
class UnifiedClassificationResult:
    """Unified result combining tag suggestions with optional expense type classification"""
    
    # PRIMARY: Tag Suggestion (replaces FIXED/VARIABLE)
    suggested_tag: str
    tag_confidence: float  # 0.0 to 1.0
    tag_explanation: str
    alternative_tags: List[str] = None
    
    # SECONDARY: Context Information  
    merchant_category: Optional[str] = None
    research_source: str = "pattern_matching"
    web_research_used: bool = False
    merchant_info: Optional[Dict] = None
    
    # BACKWARD COMPATIBILITY: Optional expense type for legacy systems
    expense_type: Optional[str] = None  # "FIXED" or "VARIABLE" - only for compatibility
    expense_type_confidence: Optional[float] = None
    expense_type_explanation: Optional[str] = None
    
    # METADATA
    processing_time_ms: int = 0
    fallback_used: bool = False
    
    def __post_init__(self):
        if self.alternative_tags is None:
            self.alternative_tags = []

class UnifiedClassificationService:
    """
    Unified service that prioritizes intelligent tag suggestions over traditional classification
    
    Features:
    - Primary focus on contextual tag suggestions (Netflix → "streaming")
    - Web research integration for unknown merchants
    - Batch processing optimization for UI performance
    - Optional FIXED/VARIABLE classification for backward compatibility
    - Progressive learning from user feedback
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.tag_service = get_tag_suggestion_service(db_session)
        self.expense_service = get_expense_classification_service(db_session)
        
        # Performance tracking
        self.classification_cache = {}
        self.stats = {
            "total_classifications": 0,
            "web_research_used": 0,
            "high_confidence_tags": 0,
            "fallback_classifications": 0
        }
    
    async def classify_transaction_primary(
        self,
        transaction_label: str,
        transaction_amount: float = None,
        transaction_description: str = "",
        use_web_research: bool = True,
        include_expense_type: bool = False
    ) -> UnifiedClassificationResult:
        """
        PRIMARY CLASSIFICATION METHOD: Returns contextual tag suggestions
        
        Args:
            transaction_label: Transaction description/label
            transaction_amount: Transaction amount for context
            transaction_description: Additional description
            use_web_research: Enable web research for unknown merchants
            include_expense_type: Include FIXED/VARIABLE classification for compatibility
        
        Returns:
            UnifiedClassificationResult with tag suggestion as primary result
        """
        start_time = time.time()
        
        try:
            # PRIMARY: Get intelligent tag suggestion
            if use_web_research:
                tag_result = await self.tag_service.suggest_tag_with_web_research(
                    transaction_label, transaction_amount
                )
            else:
                tag_result = self.tag_service.suggest_tag_fast(
                    transaction_label, transaction_amount
                )
            
            # Build unified result with tag as primary
            unified_result = UnifiedClassificationResult(
                suggested_tag=tag_result.suggested_tag,
                tag_confidence=tag_result.confidence,
                tag_explanation=tag_result.explanation,
                alternative_tags=tag_result.alternative_tags[:3],  # Limit to top 3
                merchant_category=tag_result.category,
                research_source=tag_result.research_source,
                web_research_used=tag_result.web_research_used,
                merchant_info=tag_result.merchant_info,
                fallback_used=(tag_result.confidence < 0.5)
            )
            
            # OPTIONAL: Add expense type classification for backward compatibility
            if include_expense_type:
                try:
                    expense_result = self.expense_service.classify_expense_fast(
                        tag_name=tag_result.suggested_tag,
                        transaction_amount=transaction_amount or 0,
                        transaction_description=transaction_description
                    )
                    
                    unified_result.expense_type = expense_result.expense_type
                    unified_result.expense_type_confidence = expense_result.confidence
                    unified_result.expense_type_explanation = expense_result.primary_reason
                    
                except Exception as e:
                    logger.warning(f"Expense type classification failed: {e}")
                    # Provide intelligent fallback based on tag
                    unified_result.expense_type = self._infer_expense_type_from_tag(tag_result.suggested_tag)
                    unified_result.expense_type_confidence = 0.6
                    unified_result.expense_type_explanation = f"Inferred from tag: {tag_result.suggested_tag}"
            
            # Update stats
            self.stats["total_classifications"] += 1
            if tag_result.web_research_used:
                self.stats["web_research_used"] += 1
            if tag_result.confidence >= 0.8:
                self.stats["high_confidence_tags"] += 1
            if tag_result.confidence < 0.5:
                self.stats["fallback_classifications"] += 1
            
            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)
            unified_result.processing_time_ms = processing_time
            
            return unified_result
            
        except Exception as e:
            logger.error(f"Classification failed for '{transaction_label}': {e}")
            
            # Fallback result
            return UnifiedClassificationResult(
                suggested_tag="divers",
                tag_confidence=0.3,
                tag_explanation=f"Classification failed: {str(e)}",
                research_source="error_fallback",
                fallback_used=True,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def classify_transaction_fast(
        self,
        transaction_label: str,
        transaction_amount: float = None,
        include_expense_type: bool = False
    ) -> UnifiedClassificationResult:
        """
        FAST CLASSIFICATION: Pattern-based without web research (for batch processing)
        """
        start_time = time.time()
        
        try:
            # Fast tag suggestion without web research
            tag_result = self.tag_service.suggest_tag_fast(transaction_label, transaction_amount)
            
            unified_result = UnifiedClassificationResult(
                suggested_tag=tag_result.suggested_tag,
                tag_confidence=tag_result.confidence,
                tag_explanation=tag_result.explanation,
                alternative_tags=tag_result.alternative_tags[:2],  # Fewer alternatives for speed
                research_source=tag_result.research_source,
                web_research_used=False,
                fallback_used=(tag_result.confidence < 0.5)
            )
            
            # Optional expense type for compatibility
            if include_expense_type:
                unified_result.expense_type = self._infer_expense_type_from_tag(tag_result.suggested_tag)
                unified_result.expense_type_confidence = min(tag_result.confidence + 0.1, 0.9)
                unified_result.expense_type_explanation = f"Inferred from tag pattern: {tag_result.suggested_tag}"
            
            unified_result.processing_time_ms = int((time.time() - start_time) * 1000)
            
            return unified_result
            
        except Exception as e:
            logger.error(f"Fast classification failed for '{transaction_label}': {e}")
            return UnifiedClassificationResult(
                suggested_tag="divers",
                tag_confidence=0.3,
                tag_explanation=f"Fast classification failed: {str(e)}",
                research_source="error_fallback",
                fallback_used=True,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def batch_classify_transactions(
        self,
        transactions: List[Dict],
        use_web_research: bool = False,
        include_expense_type: bool = False
    ) -> Dict[int, UnifiedClassificationResult]:
        """
        BATCH CLASSIFICATION: Efficient processing for multiple transactions
        
        Args:
            transactions: List of transaction dicts with 'id', 'label', 'amount'
            use_web_research: Enable web research (slower but more accurate)
            include_expense_type: Include FIXED/VARIABLE for compatibility
        
        Returns:
            Dict mapping transaction_id to UnifiedClassificationResult
        """
        results = {}
        
        start_time = time.time()
        
        try:
            if use_web_research:
                # For web research, process individually with rate limiting
                logger.info(f"Batch processing {len(transactions)} transactions with web research")
                
                for transaction in transactions:
                    transaction_id = transaction.get('id')
                    if transaction_id:
                        try:
                            result = asyncio.run(self.classify_transaction_primary(
                                transaction_label=transaction.get('label', ''),
                                transaction_amount=transaction.get('amount'),
                                use_web_research=True,
                                include_expense_type=include_expense_type
                            ))
                            results[transaction_id] = result
                            
                            # Rate limiting for web research
                            time.sleep(0.1)  # 100ms delay between requests
                            
                        except Exception as e:
                            logger.error(f"Batch classification failed for transaction {transaction_id}: {e}")
                            results[transaction_id] = UnifiedClassificationResult(
                                suggested_tag="divers",
                                tag_confidence=0.3,
                                tag_explanation=f"Batch processing error: {str(e)}",
                                research_source="batch_error",
                                fallback_used=True
                            )
            else:
                # Fast batch processing using tag service
                logger.info(f"Fast batch processing {len(transactions)} transactions")
                
                # Use existing batch functionality from tag service
                tag_results = self.tag_service.batch_suggest_tags(transactions)
                
                for transaction_id, tag_result in tag_results.items():
                    unified_result = UnifiedClassificationResult(
                        suggested_tag=tag_result.suggested_tag,
                        tag_confidence=tag_result.confidence,
                        tag_explanation=tag_result.explanation,
                        alternative_tags=tag_result.alternative_tags[:2],
                        research_source=tag_result.research_source,
                        web_research_used=False
                    )
                    
                    # Add expense type if requested
                    if include_expense_type:
                        unified_result.expense_type = self._infer_expense_type_from_tag(tag_result.suggested_tag)
                        unified_result.expense_type_confidence = min(tag_result.confidence + 0.1, 0.9)
                        unified_result.expense_type_explanation = f"Inferred from tag: {tag_result.suggested_tag}"
                    
                    results[transaction_id] = unified_result
            
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(f"Batch processed {len(results)} transactions in {processing_time}ms")
            
            return results
            
        except Exception as e:
            logger.error(f"Batch classification completely failed: {e}")
            return {}
    
    def _infer_expense_type_from_tag(self, tag: str) -> str:
        """
        Intelligent inference of FIXED/VARIABLE from contextual tags
        
        This provides backward compatibility for systems expecting expense types
        while prioritizing the more intelligent tag-based approach.
        """
        tag_lower = tag.lower()
        
        # FIXED expense patterns (recurring, subscription-like)
        fixed_patterns = [
            'abonnement', 'streaming', 'telephone', 'internet', 'electricite', 'gaz', 'eau',
            'assurance', 'banque', 'loyer', 'credit', 'pret', 'mutuelle', 'forfait'
        ]
        
        # VARIABLE expense patterns (occasional, discretionary)
        variable_patterns = [
            'restaurant', 'courses', 'shopping', 'essence', 'transport', 'loisirs',
            'voyage', 'sante', 'vetements', 'sport', 'beaute', 'divers'
        ]
        
        # Check for FIXED patterns
        for pattern in fixed_patterns:
            if pattern in tag_lower:
                return "FIXED"
        
        # Check for VARIABLE patterns
        for pattern in variable_patterns:
            if pattern in tag_lower:
                return "VARIABLE"
        
        # Default to VARIABLE for unknown tags
        return "VARIABLE"
    
    def learn_from_feedback(
        self,
        transaction_label: str,
        suggested_tag: str,
        actual_tag: str,
        confidence: float
    ):
        """Learn from user corrections to improve future suggestions"""
        self.tag_service.learn_from_user_feedback(
            transaction_label, suggested_tag, actual_tag, confidence
        )
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        tag_stats = self.tag_service.get_tag_statistics()
        
        return {
            "unified_service_version": "1.0.0",
            "classification_priority": "contextual_tags",
            "backward_compatibility": True,
            "performance_stats": self.stats,
            "tag_service_stats": tag_stats,
            "features": {
                "web_research_integration": True,
                "batch_processing": True,
                "progressive_learning": True,
                "expense_type_inference": True
            }
        }

# Service instance management

_unified_classification_service = None

def get_unified_classification_service(db_session: Session) -> UnifiedClassificationService:
    """Get singleton instance of UnifiedClassificationService"""
    global _unified_classification_service
    
    if _unified_classification_service is None:
        _unified_classification_service = UnifiedClassificationService(db_session)
        logger.info("✅ Unified Classification Service initialized - Priority: Contextual Tags")
    
    return _unified_classification_service

# Example usage and testing

async def test_unified_classification():
    """Test the unified classification service with sample transactions"""
    
    # Mock database session for testing
    class MockDB:
        pass
    
    service = UnifiedClassificationService(MockDB())
    
    test_transactions = [
        {"id": 1, "label": "NETFLIX SARL 12.99", "amount": 12.99},
        {"id": 2, "label": "MCDONALDS FRANCE 8.50", "amount": 8.50},
        {"id": 3, "label": "CARREFOUR VILLENEUVE 45.67", "amount": 45.67},
        {"id": 4, "label": "EDF ENERGIE 78.45", "amount": 78.45},
        {"id": 5, "label": "TOTAL ACCESS PARIS 62.30", "amount": 62.30},
        {"id": 6, "label": "SPOTIFY AB 9.99", "amount": 9.99},
        {"id": 7, "label": "PHARMACIE CENTRALE 15.80", "amount": 15.80},
        {"id": 8, "label": "UNKNOWN MERCHANT 125.00", "amount": 125.00},
    ]
    
    print("🎯 Testing Unified Classification Service...")
    print("Priority: Contextual Tag Suggestions over FIXED/VARIABLE")
    print("=" * 70)
    
    # Test individual classification with web research
    print("\n🔍 Individual Classification with Web Research:")
    for transaction in test_transactions[:3]:  # Test first 3
        label = transaction["label"]
        amount = transaction["amount"]
        
        result = await service.classify_transaction_primary(
            transaction_label=label,
            transaction_amount=amount,
            use_web_research=True,
            include_expense_type=True  # For demonstration
        )
        
        print(f"\nTransaction: {label}")
        print(f"🏷️  PRIMARY TAG: {result.suggested_tag} (confidence: {result.tag_confidence:.2f})")
        print(f"📝 Explanation: {result.tag_explanation}")
        print(f"🔄 Alternatives: {result.alternative_tags}")
        print(f"💰 Expense Type: {result.expense_type} (confidence: {result.expense_type_confidence:.2f})")
        print(f"⏱️  Processing: {result.processing_time_ms}ms")
        print(f"🌐 Web Research: {'Yes' if result.web_research_used else 'No'}")
        print("-" * 50)
    
    # Test fast batch processing
    print(f"\n⚡ Fast Batch Processing (Pattern-based):")
    batch_results = service.batch_classify_transactions(
        transactions=test_transactions,
        use_web_research=False,
        include_expense_type=True
    )
    
    for tx_id, result in batch_results.items():
        tx = next(t for t in test_transactions if t["id"] == tx_id)
        print(f"TX {tx_id}: {tx['label'][:30]}... → {result.suggested_tag} ({result.tag_confidence:.2f}) | {result.expense_type}")
    
    # Test service statistics
    print(f"\n📊 Service Statistics:")
    stats = service.get_service_statistics()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for sub_key, sub_value in value.items():
                print(f"    {sub_key}: {sub_value}")
        else:
            print(f"  {key}: {value}")

if __name__ == "__main__":
    # Run test
    asyncio.run(test_unified_classification())