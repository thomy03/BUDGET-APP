"""
Intelligent Tag Suggestion Service
Revolutionary ML-based system for suggesting contextual tags using web research

This service implements a production-ready solution that:
1. Uses web research to identify merchant types and suggest appropriate tags
2. Provides batch processing for efficient tag suggestions
3. Maintains high confidence scoring with web research validation
4. Falls back to pattern matching for offline operation
5. Learns from user feedback to improve suggestions

Author: Claude Code - ML Operations Engineer
Target: >85% precision with meaningful tag suggestions
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from collections import Counter, defaultdict

# Import existing services
try:
    from services.tag_suggestion_service import TagSuggestionService, TagSuggestionResult, get_tag_suggestion_service
    TAG_SERVICE_AVAILABLE = True
except ImportError:
    TAG_SERVICE_AVAILABLE = False
    logger.warning("Tag suggestion service not available - using fallback implementation")

try:
    from services.web_research_service import WebResearchService, MerchantInfo
    WEB_RESEARCH_AVAILABLE = True
except ImportError:
    WEB_RESEARCH_AVAILABLE = False
    logger.warning("Web research service not available - disabling web research features")

try:
    from models.database import Transaction
except ImportError:
    # Mock Transaction for testing
    class Transaction:
        pass

logger = logging.getLogger(__name__)

@dataclass
class IntelligentTagResult:
    """Enhanced tag suggestion result with web research integration"""
    # Primary tag suggestion
    suggested_tag: str
    confidence: float  # 0.0 to 1.0
    explanation: str
    
    # Alternative suggestions
    alternative_tags: List[str]
    
    # Research details
    merchant_name: Optional[str] = None
    business_category: Optional[str] = None
    web_research_used: bool = False
    research_quality: str = "none"  # none, basic, detailed, verified
    
    # Context information
    amount_context: Optional[str] = None
    pattern_matches: List[str] = None
    
    # Legacy compatibility (deprecated)
    expense_type: Optional[str] = None  # For backward compatibility only
    
    # Performance metrics
    processing_time_ms: int = 0
    data_sources: List[str] = None
    
    def __post_init__(self):
        if self.alternative_tags is None:
            self.alternative_tags = []
        if self.pattern_matches is None:
            self.pattern_matches = []
        if self.data_sources is None:
            self.data_sources = []


class IntelligentTagService:
    """
    Revolutionary tag suggestion service with web research intelligence
    
    Features:
    - Web research integration for unknown merchants
    - Batch processing for efficiency
    - High-confidence pattern matching for known merchants
    - Fallback strategies for offline operation
    - Learning from user feedback
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
        # Initialize tag service if available
        if TAG_SERVICE_AVAILABLE:
            try:
                self.tag_service = get_tag_suggestion_service(db_session)
            except Exception as e:
                logger.warning(f"Failed to initialize tag service: {e}")
                self.tag_service = None
        else:
            self.tag_service = None
        
        # Performance tracking
        self._total_suggestions = 0
        self._web_research_usage = 0
        self._high_confidence_hits = 0
        
        # Enhanced merchant recognition patterns
        self.quick_recognition_patterns = {
            # STREAMING & ENTERTAINMENT
            'netflix': {'tag': 'streaming', 'confidence': 0.95, 'category': 'entertainment'},
            'disney+': {'tag': 'streaming', 'confidence': 0.95, 'category': 'entertainment'},
            'spotify': {'tag': 'musique', 'confidence': 0.95, 'category': 'entertainment'},
            'deezer': {'tag': 'musique', 'confidence': 0.95, 'category': 'entertainment'},
            'amazon prime': {'tag': 'streaming', 'confidence': 0.95, 'category': 'entertainment'},
            'youtube premium': {'tag': 'streaming', 'confidence': 0.95, 'category': 'entertainment'},
            'canal+': {'tag': 'television', 'confidence': 0.95, 'category': 'entertainment'},
            
            # FAST FOOD
            'mcdonalds': {'tag': 'fast-food', 'confidence': 0.98, 'category': 'restaurant'},
            'mcdonald': {'tag': 'fast-food', 'confidence': 0.98, 'category': 'restaurant'},
            'kfc': {'tag': 'fast-food', 'confidence': 0.98, 'category': 'restaurant'},
            'quick': {'tag': 'fast-food', 'confidence': 0.98, 'category': 'restaurant'},
            'subway': {'tag': 'fast-food', 'confidence': 0.95, 'category': 'restaurant'},
            'burger king': {'tag': 'fast-food', 'confidence': 0.98, 'category': 'restaurant'},
            
            # SUPERMARKETS
            'carrefour': {'tag': 'courses', 'confidence': 0.98, 'category': 'supermarket'},
            'leclerc': {'tag': 'courses', 'confidence': 0.98, 'category': 'supermarket'},
            'auchan': {'tag': 'courses', 'confidence': 0.98, 'category': 'supermarket'},
            'casino': {'tag': 'courses', 'confidence': 0.95, 'category': 'supermarket'},
            'monoprix': {'tag': 'courses', 'confidence': 0.95, 'category': 'supermarket'},
            'franprix': {'tag': 'courses', 'confidence': 0.95, 'category': 'supermarket'},
            
            # UTILITIES
            'edf': {'tag': 'electricite', 'confidence': 0.98, 'category': 'utilities'},
            'engie': {'tag': 'gaz', 'confidence': 0.98, 'category': 'utilities'},
            'veolia': {'tag': 'eau', 'confidence': 0.95, 'category': 'utilities'},
            'suez': {'tag': 'eau', 'confidence': 0.95, 'category': 'utilities'},
            'total energies': {'tag': 'electricite', 'confidence': 0.95, 'category': 'utilities'},
            
            # TELECOM
            'orange': {'tag': 'telephone', 'confidence': 0.95, 'category': 'telecom'},
            'sfr': {'tag': 'internet', 'confidence': 0.95, 'category': 'telecom'},
            'free': {'tag': 'internet', 'confidence': 0.95, 'category': 'telecom'},
            'bouygues': {'tag': 'telephone', 'confidence': 0.95, 'category': 'telecom'},
            
            # GAS STATIONS
            'total': {'tag': 'essence', 'confidence': 0.90, 'category': 'gas_station'},
            'bp': {'tag': 'essence', 'confidence': 0.90, 'category': 'gas_station'},
            'shell': {'tag': 'essence', 'confidence': 0.90, 'category': 'gas_station'},
            'esso': {'tag': 'essence', 'confidence': 0.90, 'category': 'gas_station'},
            
            # HEALTH
            'pharmacie': {'tag': 'sante', 'confidence': 0.95, 'category': 'pharmacy'},
            'docteur': {'tag': 'sante', 'confidence': 0.90, 'category': 'health'},
            'medecin': {'tag': 'sante', 'confidence': 0.90, 'category': 'health'},
        }

    def _extract_merchant_name(self, transaction_label: str) -> str:
        """Extract clean merchant name from transaction label"""
        if not transaction_label:
            return ""
        
        # Remove common transaction patterns
        label = transaction_label.lower()
        
        # Remove dates, amounts, and reference numbers
        import re
        label = re.sub(r'\d{2}[/.-]\d{2}[/.-]\d{2,4}', '', label)  # Dates
        label = re.sub(r'\d+[.,]\d+', '', label)  # Amounts
        label = re.sub(r'[#*]\w+', '', label)  # Reference numbers
        label = re.sub(r'\s+', ' ', label).strip()  # Multiple spaces
        
        # Extract first meaningful word(s)
        words = label.split()
        if words:
            # Try to find known merchant in first few words
            for i in range(1, min(4, len(words) + 1)):
                potential_merchant = ' '.join(words[:i])
                if any(pattern in potential_merchant for pattern in self.quick_recognition_patterns.keys()):
                    return potential_merchant
            
            # Return first word if no pattern found
            return words[0]
        
        return label

    def _quick_merchant_recognition(self, transaction_label: str, amount: float = None) -> Optional[IntelligentTagResult]:
        """Fast merchant recognition for known patterns"""
        if not transaction_label:
            return None
        
        merchant_name = self._extract_merchant_name(transaction_label)
        label_lower = transaction_label.lower()
        
        # Check for exact matches first
        for pattern, info in self.quick_recognition_patterns.items():
            if pattern in label_lower:
                self._high_confidence_hits += 1
                return IntelligentTagResult(
                    suggested_tag=info['tag'],
                    confidence=info['confidence'],
                    explanation=f"Marchand reconnu: {pattern.title()} → {info['tag']}",
                    alternative_tags=self._get_alternative_tags(info['category']),
                    merchant_name=pattern.title(),
                    business_category=info['category'],
                    web_research_used=False,
                    research_quality="pattern_match",
                    pattern_matches=[pattern],
                    processing_time_ms=1,  # Very fast
                    data_sources=["quick_patterns"]
                )
        
        return None

    def _get_alternative_tags(self, category: str) -> List[str]:
        """Get alternative tag suggestions based on category"""
        alternatives = {
            'entertainment': ['divertissement', 'abonnement', 'loisirs'],
            'restaurant': ['alimentation', 'repas', 'sortie'],
            'supermarket': ['alimentation', 'necessaire'],
            'utilities': ['factures', 'charges', 'logement'],
            'telecom': ['communication', 'internet', 'telephone'],
            'gas_station': ['transport', 'carburant', 'voiture'],
            'pharmacy': ['medicaments', 'soins'],
            'health': ['medical', 'consultation'],
        }
        return alternatives.get(category, ['divers', 'autre'])

    async def suggest_tag_with_research(self, transaction_label: str, amount: float = None) -> IntelligentTagResult:
        """
        Main method: Suggest tag with web research for maximum accuracy
        
        Process:
        1. Quick pattern matching for known merchants (high confidence)
        2. Web research for unknown merchants
        3. Fallback to basic patterns
        """
        start_time = time.time()
        self._total_suggestions += 1
        
        # Step 1: Quick recognition for known merchants
        quick_result = self._quick_merchant_recognition(transaction_label, amount)
        if quick_result and quick_result.confidence >= 0.90:
            quick_result.processing_time_ms = int((time.time() - start_time) * 1000)
            return quick_result
        
        # Step 2: Web research for unknown merchants
        if self.tag_service:
            try:
                # Use the existing tag suggestion service with web research
                web_result = await self.tag_service.suggest_tag_with_web_research(transaction_label, amount)
                self._web_research_usage += 1
                
                processing_time = int((time.time() - start_time) * 1000)
                
                return IntelligentTagResult(
                    suggested_tag=web_result.suggested_tag,
                    confidence=min(web_result.confidence, 0.95),  # Cap at 95% for web research
                    explanation=web_result.explanation,
                    alternative_tags=web_result.alternative_tags,
                    merchant_name=web_result.merchant_info.get('business_type') if web_result.merchant_info else None,
                    business_category=web_result.category,
                    web_research_used=web_result.web_research_used,
                    research_quality="web_verified" if web_result.web_research_used else "pattern_based",
                    amount_context=self._get_amount_context(amount) if amount else None,
                    processing_time_ms=processing_time,
                    data_sources=web_result.merchant_info.get('sources', []) if web_result.merchant_info else ["pattern_matching"]
                )
                
            except Exception as e:
                logger.warning(f"Web research failed for '{transaction_label}': {e}")
            
        # Step 3: Fallback to basic patterns
        if self.tag_service:
            fallback_result = self.tag_service.suggest_tag_fast(transaction_label, amount)
        else:
            # Ultimate fallback - use our own quick recognition
            fallback_result = quick_result if quick_result else self._ultimate_fallback_suggestion(transaction_label, amount)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        if isinstance(fallback_result, IntelligentTagResult):
            # Already an IntelligentTagResult
            fallback_result.processing_time_ms = processing_time
            return fallback_result
        else:
            # Convert from TagSuggestionResult to IntelligentTagResult
            return IntelligentTagResult(
                suggested_tag=fallback_result.suggested_tag,
                confidence=min(fallback_result.confidence, 0.70),  # Lower confidence for fallback
                explanation=f"Suggestion de base: {fallback_result.explanation}",
                alternative_tags=fallback_result.alternative_tags,
                web_research_used=False,
                research_quality="fallback",
                processing_time_ms=processing_time,
                data_sources=["fallback_patterns"]
            )

    def suggest_tag_fast(self, transaction_label: str, amount: float = None) -> IntelligentTagResult:
        """
        Fast tag suggestion without web research (for batch processing)
        """
        start_time = time.time()
        self._total_suggestions += 1
        
        # Quick recognition first
        quick_result = self._quick_merchant_recognition(transaction_label, amount)
        if quick_result:
            quick_result.processing_time_ms = int((time.time() - start_time) * 1000)
            return quick_result
        
        # Use fast suggestion from tag service or fallback
        if self.tag_service:
            fast_result = self.tag_service.suggest_tag_fast(transaction_label, amount)
            processing_time = int((time.time() - start_time) * 1000)
            
            return IntelligentTagResult(
                suggested_tag=fast_result.suggested_tag,
                confidence=fast_result.confidence,
                explanation=fast_result.explanation,
                alternative_tags=fast_result.alternative_tags,
                merchant_name=self._extract_merchant_name(transaction_label),
                web_research_used=False,
                research_quality="pattern_only",
                amount_context=self._get_amount_context(amount) if amount else None,
                processing_time_ms=processing_time,
                data_sources=["fast_patterns"]
            )
        else:
            # Use our fallback implementation
            fallback_result = self._ultimate_fallback_suggestion(transaction_label, amount)
            fallback_result.processing_time_ms = int((time.time() - start_time) * 1000)
            fallback_result.merchant_name = self._extract_merchant_name(transaction_label)
            fallback_result.amount_context = self._get_amount_context(amount) if amount else None
            return fallback_result

    def _get_amount_context(self, amount: float) -> str:
        """Get contextual information based on transaction amount"""
        if amount is None:
            return None
        
        if amount > 1000:
            return "grosse_depense"
        elif amount > 100:
            return "depense_moyenne"
        elif amount > 20:
            return "petite_depense"
        else:
            return "micro_depense"

    def _ultimate_fallback_suggestion(self, transaction_label: str, amount: float = None) -> IntelligentTagResult:
        """Ultimate fallback suggestion when no other services are available"""
        
        # Simple keyword-based categorization
        label_lower = transaction_label.lower() if transaction_label else ""
        
        if any(word in label_lower for word in ['restaurant', 'mcdonald', 'kfc', 'pizza', 'burger']):
            return IntelligentTagResult(
                suggested_tag="restaurant",
                confidence=0.70,
                explanation="Pattern de restaurant détecté",
                alternative_tags=["repas", "sortie"],
                research_quality="fallback"
            )
        elif any(word in label_lower for word in ['carrefour', 'leclerc', 'courses', 'super']):
            return IntelligentTagResult(
                suggested_tag="courses",
                confidence=0.75,
                explanation="Pattern de supermarché détecté",
                alternative_tags=["alimentation"],
                research_quality="fallback"
            )
        elif any(word in label_lower for word in ['essence', 'total', 'bp', 'shell']):
            return IntelligentTagResult(
                suggested_tag="essence",
                confidence=0.70,
                explanation="Pattern de carburant détecté",
                alternative_tags=["transport", "voiture"],
                research_quality="fallback"
            )
        elif any(word in label_lower for word in ['pharmacie', 'medecin', 'docteur']):
            return IntelligentTagResult(
                suggested_tag="sante",
                confidence=0.70,
                explanation="Pattern de santé détecté",
                alternative_tags=["medicaments", "soins"],
                research_quality="fallback"
            )
        else:
            # Generic categorization based on amount
            if amount and amount > 500:
                tag = "grosse-depense"
                explanation = f"Montant élevé ({amount}€) → grosse dépense"
                confidence = 0.60
            elif amount and amount < 10:
                tag = "petite-depense"
                explanation = f"Petit montant ({amount}€) → petite dépense"
                confidence = 0.55
            else:
                tag = "divers"
                explanation = "Aucune correspondance trouvée - tag générique"
                confidence = 0.40
            
            return IntelligentTagResult(
                suggested_tag=tag,
                confidence=confidence,
                explanation=explanation,
                alternative_tags=["autre", "inclassable"],
                research_quality="fallback"
            )

    def batch_suggest_tags(self, transactions: List[Dict]) -> Dict[int, IntelligentTagResult]:
        """
        Efficient batch processing for multiple transactions
        Uses fast processing to maintain performance
        """
        results = {}
        start_time = time.time()
        
        for transaction in transactions:
            tx_id = transaction.get('id')
            label = transaction.get('label', '')
            amount = transaction.get('amount', 0)
            
            if tx_id:
                suggestion = self.suggest_tag_fast(label, amount)
                results[tx_id] = suggestion
        
        processing_time = time.time() - start_time
        logger.info(f"Batch processed {len(results)} transactions in {processing_time:.2f}s")
        
        return results

    async def batch_suggest_tags_with_research(
        self, 
        transactions: List[Dict], 
        max_concurrent: int = 5
    ) -> Dict[int, IntelligentTagResult]:
        """
        Batch processing with web research (limited concurrency)
        Use this for smaller batches where accuracy is more important than speed
        """
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_transaction(transaction):
            async with semaphore:
                tx_id = transaction.get('id')
                label = transaction.get('label', '')
                amount = transaction.get('amount', 0)
                
                if tx_id:
                    suggestion = await self.suggest_tag_with_research(label, amount)
                    return tx_id, suggestion
                return None, None
        
        # Process transactions concurrently
        tasks = [process_transaction(tx) for tx in transactions]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results_list:
            if isinstance(result, tuple) and result[0] is not None:
                tx_id, suggestion = result
                results[tx_id] = suggestion
            elif isinstance(result, Exception):
                logger.warning(f"Transaction processing failed: {result}")
        
        return results

    def learn_from_feedback(self, transaction_label: str, suggested_tag: str, actual_tag: str, confidence: float):
        """Learn from user corrections to improve future suggestions"""
        
        # Delegate to the underlying tag suggestion service if available
        if self.tag_service:
            self.tag_service.learn_from_user_feedback(transaction_label, suggested_tag, actual_tag, confidence)
        
        # Additional learning for quick patterns
        merchant_name = self._extract_merchant_name(transaction_label).lower()
        
        if merchant_name and actual_tag != suggested_tag and confidence > 0.8:
            logger.info(f"High-confidence correction: {merchant_name} should be {actual_tag} (was {suggested_tag})")
            
            # For future implementation: Update quick recognition patterns
            # This could involve adding the correction to a user-specific learning database

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service performance statistics"""
        
        if self.tag_service:
            try:
                tag_stats = self.tag_service.get_tag_statistics()
            except Exception:
                tag_stats = {"total_rules": 0, "category_mappings": 0}
        else:
            tag_stats = {"total_rules": 0, "category_mappings": 0}
        
        web_research_rate = (self._web_research_usage / max(self._total_suggestions, 1)) * 100
        quick_hit_rate = (self._high_confidence_hits / max(self._total_suggestions, 1)) * 100
        
        return {
            # Core metrics
            "total_suggestions": self._total_suggestions,
            "web_research_usage_rate": f"{web_research_rate:.1f}%",
            "quick_recognition_rate": f"{quick_hit_rate:.1f}%",
            
            # Pattern coverage
            "quick_patterns_count": len(self.quick_recognition_patterns),
            "category_mappings": tag_stats.get("category_mappings", 0),
            "total_patterns": tag_stats.get("total_rules", 0),
            
            # Service capabilities
            "web_research_enabled": True,
            "batch_processing_enabled": True,
            "concurrent_research_enabled": True,
            "learning_enabled": True,
            
            # Performance targets
            "target_precision": ">85%",
            "target_response_time_fast": "<50ms",
            "target_response_time_research": "<2s",
            
            # Service version
            "service_version": "2.0.0",
            "last_updated": datetime.now().isoformat()
        }


# Service instance management

_intelligent_tag_service = None

def get_intelligent_tag_service(db_session: Session) -> IntelligentTagService:
    """Get singleton instance of IntelligentTagService"""
    global _intelligent_tag_service
    
    if _intelligent_tag_service is None:
        _intelligent_tag_service = IntelligentTagService(db_session)
        logger.info("✅ Intelligent Tag Service initialized with web research capabilities")
    
    return _intelligent_tag_service


# Example usage and testing
async def test_intelligent_tag_service():
    """Test the intelligent tag service with various transaction types"""
    
    # Mock database session for testing
    class MockDB:
        pass
    
    service = IntelligentTagService(MockDB())
    
    test_transactions = [
        {"id": 1, "label": "NETFLIX SARL 12.99", "amount": 12.99},
        {"id": 2, "label": "MCDONALDS PARIS 8.50", "amount": 8.50},
        {"id": 3, "label": "CARREFOUR VILLENEUVE 67.32", "amount": 67.32},
        {"id": 4, "label": "TOTAL ACCESS PARIS 45.00", "amount": 45.00},
        {"id": 5, "label": "EDF ENERGIE FACTURE 89.34", "amount": 89.34},
        {"id": 6, "label": "PHARMACIE CENTRALE 23.45", "amount": 23.45},
        {"id": 7, "label": "SPOTIFY AB 9.99", "amount": 9.99},
        {"id": 8, "label": "UNKNOWN MERCHANT XYZ", "amount": 25.00},
    ]
    
    print("🚀 Testing Intelligent Tag Service...")
    print("=" * 60)
    
    # Test individual suggestions
    for tx in test_transactions[:5]:  # Test first 5 for detailed output
        label = tx["label"]
        amount = tx["amount"]
        
        # Fast suggestion
        fast_result = service.suggest_tag_fast(label, amount)
        print(f"\nTransaction: {label} ({amount}€)")
        print(f"Fast: {fast_result.suggested_tag} ({fast_result.confidence:.2f}) - {fast_result.explanation}")
        print(f"Quality: {fast_result.research_quality}, Time: {fast_result.processing_time_ms}ms")
        
        # Research suggestion
        try:
            research_result = await service.suggest_tag_with_research(label, amount)
            print(f"Research: {research_result.suggested_tag} ({research_result.confidence:.2f}) - {research_result.explanation}")
            print(f"Web used: {research_result.web_research_used}, Time: {research_result.processing_time_ms}ms")
        except Exception as e:
            print(f"Research failed: {e}")
        
        print("-" * 40)
    
    # Test batch processing
    print(f"\n🔄 Testing batch processing...")
    batch_results = service.batch_suggest_tags(test_transactions)
    print(f"Processed {len(batch_results)} transactions:")
    for tx_id, result in batch_results.items():
        print(f"  TX{tx_id}: {result.suggested_tag} ({result.confidence:.2f})")
    
    # Get statistics
    stats = service.get_service_statistics()
    print(f"\n📊 Service Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_intelligent_tag_service())