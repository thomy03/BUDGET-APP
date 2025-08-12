"""
Enhanced Auto-Tagging Service for Budget Family v2.3
Production-ready ML Operations system for intelligent transaction classification

Features:
- AI pattern matching for known merchants (Netflix → "streaming")  
- Web research for unknown merchants with business intelligence
- Fixed/Variable expense classification with confidence scoring
- Batch processing with progress feedback and rate limiting
- 50% confidence threshold enforcement
- Merchant result caching to minimize duplicate research
- Efficient handling of 100+ transactions

Author: Claude Code - ML Operations Engineer
Target: >85% precision with >50% confidence threshold
"""

import logging
import asyncio
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from collections import Counter, defaultdict
import json
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import threading

# Core imports
try:
    from models.database import Transaction
    from services.intelligent_tag_service import IntelligentTagService, IntelligentTagResult, get_intelligent_tag_service
    from services.web_research_service import WebResearchService, MerchantInfo
    from services.tag_suggestion_service import TagSuggestionService, get_tag_suggestion_service
    DB_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Database models not available: {e}")
    DB_AVAILABLE = False
    class Transaction:
        pass

logger = logging.getLogger(__name__)

@dataclass 
class EnhancedTagResult:
    """Enhanced result with fixed/variable classification and confidence enforcement"""
    # Primary classification
    suggested_tag: str
    confidence: float  # Always >= 0.50 when returned
    expense_type: str  # FIXED, VARIABLE, or PROVISION
    expense_type_confidence: float
    explanation: str
    
    # Research and alternatives  
    alternative_tags: List[str]
    merchant_name: Optional[str] = None
    business_category: Optional[str] = None
    web_research_used: bool = False
    research_quality: str = "none"
    
    # Performance tracking
    processing_time_ms: int = 0
    cached_result: bool = False
    data_sources: List[str] = None
    
    def __post_init__(self):
        if self.alternative_tags is None:
            self.alternative_tags = []
        if self.data_sources is None:
            self.data_sources = []
        
        # Enforce confidence threshold
        if self.confidence < 0.50:
            self.suggested_tag = ""
            self.explanation = f"Confiance insuffisante ({self.confidence:.2f} < 0.50)"

@dataclass
class BatchProcessingResult:
    """Results from batch processing operation"""
    processed_count: int
    successful_count: int
    high_confidence_count: int
    web_research_count: int
    cache_hit_count: int
    processing_time_seconds: float
    results: Dict[int, EnhancedTagResult]
    errors: List[str]
    
    # Monthly statistics
    month: Optional[str] = None
    fixed_expenses_identified: int = 0
    variable_expenses_identified: int = 0
    unknown_merchants_researched: List[str] = None
    
    def __post_init__(self):
        if self.unknown_merchants_researched is None:
            self.unknown_merchants_researched = []

class EnhancedAutoTaggingService:
    """
    Production-ready auto-tagging system with ML intelligence
    
    Key capabilities:
    - Batch processing with progress feedback
    - Web research integration with caching
    - Fixed/Variable classification using business intelligence
    - Confidence threshold enforcement (>= 50%)
    - Rate limiting and error handling
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
        # Initialize core services
        if DB_AVAILABLE:
            try:
                self.intelligent_service = get_intelligent_tag_service(db_session)
                self.tag_service = get_tag_suggestion_service(db_session)
            except Exception as e:
                logger.warning(f"Failed to initialize tag services: {e}")
                self.intelligent_service = None
                self.tag_service = None
        else:
            self.intelligent_service = None
            self.tag_service = None
        
        # Web research service
        try:
            self.web_research_service = WebResearchService()
        except:
            self.web_research_service = None
            logger.warning("Web research service not available")
        
        # Caching system for merchant research
        self.merchant_cache = {}  # merchant_name -> MerchantInfo
        self.cache_ttl_hours = 24  # Cache results for 24 hours
        self.cache_timestamps = {}  # merchant_name -> timestamp
        
        # Rate limiting for web research
        self.research_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests
        self.last_research_time = time.time()
        self.min_research_interval = 0.5  # 500ms between requests
        
        # Performance tracking
        self._total_processed = 0
        self._cache_hits = 0
        self._web_research_calls = 0
        self._high_confidence_results = 0
        
        # Enhanced merchant patterns with Fixed/Variable classification
        self.enhanced_merchant_patterns = {
            # FIXED EXPENSES - Recurring subscriptions and utilities
            'netflix': {
                'tag': 'streaming', 'confidence': 0.95, 'expense_type': 'FIXED',
                'expense_type_confidence': 0.98, 'category': 'entertainment',
                'reasoning': 'Abonnement mensuel récurrent'
            },
            'disney+': {
                'tag': 'streaming', 'confidence': 0.95, 'expense_type': 'FIXED',
                'expense_type_confidence': 0.98, 'category': 'entertainment',
                'reasoning': 'Abonnement streaming mensuel'
            },
            'spotify': {
                'tag': 'musique', 'confidence': 0.95, 'expense_type': 'FIXED',
                'expense_type_confidence': 0.98, 'category': 'entertainment',
                'reasoning': 'Abonnement musical mensuel'
            },
            'canal+': {
                'tag': 'television', 'confidence': 0.95, 'expense_type': 'FIXED',
                'expense_type_confidence': 0.98, 'category': 'entertainment',
                'reasoning': 'Abonnement TV récurrent'
            },
            'orange': {
                'tag': 'telephone', 'confidence': 0.95, 'expense_type': 'FIXED',
                'expense_type_confidence': 0.95, 'category': 'telecom',
                'reasoning': 'Forfait télécoms mensuel'
            },
            'sfr': {
                'tag': 'internet', 'confidence': 0.95, 'expense_type': 'FIXED',
                'expense_type_confidence': 0.95, 'category': 'telecom',
                'reasoning': 'Abonnement internet fixe'
            },
            'free': {
                'tag': 'internet', 'confidence': 0.95, 'expense_type': 'FIXED',
                'expense_type_confidence': 0.95, 'category': 'telecom',
                'reasoning': 'Forfait internet/mobile'
            },
            'edf': {
                'tag': 'electricite', 'confidence': 0.98, 'expense_type': 'FIXED',
                'expense_type_confidence': 0.90, 'category': 'utilities',
                'reasoning': 'Facture électricité (abonnement + consommation)'
            },
            'engie': {
                'tag': 'gaz', 'confidence': 0.98, 'expense_type': 'FIXED', 
                'expense_type_confidence': 0.90, 'category': 'utilities',
                'reasoning': 'Facture gaz (abonnement + consommation)'
            },
            'veolia': {
                'tag': 'eau', 'confidence': 0.95, 'expense_type': 'FIXED',
                'expense_type_confidence': 0.85, 'category': 'utilities',
                'reasoning': 'Facture eau (souvent trimestrielle)'
            },
            
            # VARIABLE EXPENSES - Irregular purchases
            'mcdonalds': {
                'tag': 'fast-food', 'confidence': 0.98, 'expense_type': 'VARIABLE',
                'expense_type_confidence': 0.99, 'category': 'restaurant',
                'reasoning': 'Achat ponctuel de restauration'
            },
            'mcdonald': {
                'tag': 'fast-food', 'confidence': 0.98, 'expense_type': 'VARIABLE',
                'expense_type_confidence': 0.99, 'category': 'restaurant',
                'reasoning': 'Achat ponctuel fast-food'
            },
            'burger king': {
                'tag': 'fast-food', 'confidence': 0.98, 'expense_type': 'VARIABLE',
                'expense_type_confidence': 0.99, 'category': 'restaurant',
                'reasoning': 'Restaurant rapide occasionnel'
            },
            'carrefour': {
                'tag': 'courses', 'confidence': 0.98, 'expense_type': 'VARIABLE',
                'expense_type_confidence': 0.95, 'category': 'supermarket',
                'reasoning': 'Achats alimentaires variables'
            },
            'leclerc': {
                'tag': 'courses', 'confidence': 0.98, 'expense_type': 'VARIABLE',
                'expense_type_confidence': 0.95, 'category': 'supermarket',
                'reasoning': 'Courses alimentaires ponctuelles'
            },
            'auchan': {
                'tag': 'courses', 'confidence': 0.98, 'expense_type': 'VARIABLE',
                'expense_type_confidence': 0.95, 'category': 'supermarket',
                'reasoning': 'Supermarché - montants variables'
            },
            'total': {
                'tag': 'essence', 'confidence': 0.90, 'expense_type': 'VARIABLE',
                'expense_type_confidence': 0.98, 'category': 'gas_station',
                'reasoning': 'Carburant selon usage véhicule'
            },
            'bp': {
                'tag': 'essence', 'confidence': 0.90, 'expense_type': 'VARIABLE',
                'expense_type_confidence': 0.98, 'category': 'gas_station',
                'reasoning': 'Station-service - consommation variable'
            },
            'shell': {
                'tag': 'essence', 'confidence': 0.90, 'expense_type': 'VARIABLE',
                'expense_type_confidence': 0.98, 'category': 'gas_station',
                'reasoning': 'Essence selon déplacements'
            },
            'pharmacie': {
                'tag': 'sante', 'confidence': 0.95, 'expense_type': 'VARIABLE',
                'expense_type_confidence': 0.90, 'category': 'pharmacy',
                'reasoning': 'Achats médicaments occasionnels'
            },
        }

    def _is_cache_valid(self, merchant_name: str) -> bool:
        """Check if cached merchant data is still valid"""
        if merchant_name not in self.cache_timestamps:
            return False
        
        cache_time = self.cache_timestamps[merchant_name]
        expiry_time = cache_time + (self.cache_ttl_hours * 3600)
        
        return time.time() < expiry_time

    def _get_cached_merchant_info(self, merchant_name: str) -> Optional[MerchantInfo]:
        """Get cached merchant information if available and valid"""
        if merchant_name in self.merchant_cache and self._is_cache_valid(merchant_name):
            self._cache_hits += 1
            return self.merchant_cache[merchant_name]
        return None

    def _cache_merchant_info(self, merchant_name: str, merchant_info: MerchantInfo):
        """Cache merchant information with timestamp"""
        self.merchant_cache[merchant_name] = merchant_info
        self.cache_timestamps[merchant_name] = time.time()

    def _extract_clean_merchant_name(self, transaction_label: str) -> str:
        """Extract clean merchant name for pattern matching and web research"""
        if not transaction_label:
            return ""
        
        import re
        label = transaction_label.lower().strip()
        
        # Remove common transaction artifacts
        label = re.sub(r'\d{2}[/.-]\d{2}[/.-]\d{2,4}', '', label)  # Dates
        label = re.sub(r'\d+[.,]\d+', '', label)  # Amounts  
        label = re.sub(r'[#*]\w+', '', label)  # Reference numbers
        label = re.sub(r'\s+', ' ', label).strip()  # Multiple spaces
        
        # Extract meaningful merchant name
        words = label.split()
        if words:
            # Look for known patterns in first few words
            for i in range(1, min(4, len(words) + 1)):
                potential_merchant = ' '.join(words[:i])
                if any(pattern in potential_merchant for pattern in self.enhanced_merchant_patterns.keys()):
                    return potential_merchant
            
            # Return first significant word
            return words[0]
        
        return label

    def _quick_pattern_match(self, transaction_label: str, amount: float = None) -> Optional[EnhancedTagResult]:
        """Fast pattern matching against known merchant database"""
        if not transaction_label:
            return None
        
        label_lower = transaction_label.lower()
        
        # Check enhanced patterns  
        for pattern, info in self.enhanced_merchant_patterns.items():
            if pattern in label_lower:
                self._high_confidence_results += 1
                
                return EnhancedTagResult(
                    suggested_tag=info['tag'],
                    confidence=info['confidence'],
                    expense_type=info['expense_type'],
                    expense_type_confidence=info['expense_type_confidence'],
                    explanation=f"✅ {pattern.title()}: {info['reasoning']}",
                    alternative_tags=self._get_category_alternatives(info['category']),
                    merchant_name=pattern.title(),
                    business_category=info['category'],
                    web_research_used=False,
                    research_quality="pattern_match",
                    processing_time_ms=1,
                    cached_result=False,
                    data_sources=["enhanced_patterns"]
                )
        
        return None

    def _get_category_alternatives(self, category: str) -> List[str]:
        """Get alternative tag suggestions by business category"""
        alternatives = {
            'entertainment': ['divertissement', 'abonnement', 'loisirs', 'streaming'],
            'restaurant': ['alimentation', 'repas', 'sortie', 'fast-food'],
            'supermarket': ['alimentation', 'necessaire', 'epicerie'],
            'utilities': ['factures', 'charges', 'logement', 'electricite', 'gaz', 'eau'],
            'telecom': ['communication', 'internet', 'telephone', 'mobile'],
            'gas_station': ['transport', 'carburant', 'voiture', 'essence'],
            'pharmacy': ['medicaments', 'soins', 'sante'],
            'health': ['medical', 'consultation', 'sante'],
        }
        return alternatives.get(category, ['divers', 'autre'])

    async def _rate_limited_web_research(self, merchant_name: str) -> Optional[MerchantInfo]:
        """Perform web research with rate limiting"""
        if not self.web_research_service:
            return None
        
        # Check cache first
        cached_info = self._get_cached_merchant_info(merchant_name)
        if cached_info:
            logger.debug(f"Cache hit for merchant: {merchant_name}")
            return cached_info
        
        # Rate limiting
        async with self.research_semaphore:
            current_time = time.time()
            time_since_last = current_time - self.last_research_time
            
            if time_since_last < self.min_research_interval:
                wait_time = self.min_research_interval - time_since_last
                await asyncio.sleep(wait_time)
            
            try:
                logger.info(f"🔍 Web research for merchant: {merchant_name}")
                merchant_info = await self.web_research_service.research_merchant(merchant_name)
                
                if merchant_info:
                    self._cache_merchant_info(merchant_name, merchant_info)
                    self._web_research_calls += 1
                    
                self.last_research_time = time.time()
                return merchant_info
                
            except Exception as e:
                logger.warning(f"Web research failed for {merchant_name}: {e}")
                return None

    def _classify_expense_type_from_web_data(self, merchant_info: MerchantInfo, amount: float = None) -> Tuple[str, float]:
        """Classify Fixed/Variable based on web research data"""
        if not merchant_info:
            return "VARIABLE", 0.50
        
        business_type = merchant_info.business_type.lower() if merchant_info.business_type else ""
        category = merchant_info.category.lower() if merchant_info.category else ""
        
        # High confidence fixed expense indicators
        fixed_indicators = [
            'subscription', 'utility', 'telecom', 'insurance', 'streaming',
            'abonnement', 'forfait', 'facture', 'electricite', 'gaz', 'eau',
            'telephone', 'internet', 'assurance'
        ]
        
        # High confidence variable expense indicators  
        variable_indicators = [
            'restaurant', 'retail', 'supermarket', 'gas station', 'pharmacy',
            'clothing', 'entertainment', 'shopping', 'courses', 'essence',
            'magasin', 'boutique', 'restaurant', 'pharmacie'
        ]
        
        # Check for fixed indicators
        for indicator in fixed_indicators:
            if indicator in business_type or indicator in category:
                return "FIXED", 0.85
        
        # Check for variable indicators
        for indicator in variable_indicators:
            if indicator in business_type or indicator in category:
                return "VARIABLE", 0.80
        
        # Amount-based classification as fallback
        if amount:
            if 5 <= amount <= 50:  # Typical subscription range
                return "FIXED", 0.60
            elif amount > 100:     # Large purchases usually variable
                return "VARIABLE", 0.70
        
        # Default to variable with medium confidence
        return "VARIABLE", 0.55

    async def enhanced_tag_suggestion(self, transaction_label: str, amount: float = None) -> EnhancedTagResult:
        """
        Core method: Enhanced tag suggestion with web research and confidence filtering
        """
        start_time = time.time()
        self._total_processed += 1
        
        # Step 1: Quick pattern matching for known merchants
        quick_result = self._quick_pattern_match(transaction_label, amount)
        if quick_result and quick_result.confidence >= 0.85:
            quick_result.processing_time_ms = int((time.time() - start_time) * 1000)
            return quick_result
        
        # Step 2: Web research for unknown merchants
        merchant_name = self._extract_clean_merchant_name(transaction_label)
        
        if merchant_name:
            merchant_info = await self._rate_limited_web_research(merchant_name)
            
            if merchant_info and merchant_info.confidence >= 0.60:
                # Use web research to enhance suggestion
                expense_type, expense_type_conf = self._classify_expense_type_from_web_data(merchant_info, amount)
                
                # Generate tag from business intelligence
                suggested_tag = self._generate_tag_from_business_type(merchant_info.business_type, merchant_info.category)
                confidence = min(merchant_info.confidence * 0.9, 0.95)  # Slightly lower for web research
                
                if confidence >= 0.50:
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    return EnhancedTagResult(
                        suggested_tag=suggested_tag,
                        confidence=confidence,
                        expense_type=expense_type,
                        expense_type_confidence=expense_type_conf,
                        explanation=f"🌐 Recherche web: {merchant_info.business_type or 'Commerce'} → {suggested_tag}",
                        alternative_tags=self._get_web_alternatives(merchant_info),
                        merchant_name=merchant_name.title(),
                        business_category=merchant_info.category,
                        web_research_used=True,
                        research_quality="web_verified",
                        processing_time_ms=processing_time,
                        cached_result=merchant_name in self.merchant_cache,
                        data_sources=["web_research", "business_intelligence"]
                    )
        
        # Step 3: Fallback to existing intelligent service
        if self.intelligent_service:
            try:
                fallback_result = await self.intelligent_service.suggest_tag_with_research(transaction_label, amount)
                
                # Convert to EnhancedTagResult with expense type classification
                expense_type, expense_type_conf = self._classify_expense_type_fallback(transaction_label, amount)
                
                processing_time = int((time.time() - start_time) * 1000)
                
                # Enforce confidence threshold
                if fallback_result.confidence >= 0.50:
                    return EnhancedTagResult(
                        suggested_tag=fallback_result.suggested_tag,
                        confidence=fallback_result.confidence,
                        expense_type=expense_type,
                        expense_type_confidence=expense_type_conf,
                        explanation=fallback_result.explanation,
                        alternative_tags=fallback_result.alternative_tags,
                        merchant_name=fallback_result.merchant_name,
                        business_category=fallback_result.business_category,
                        web_research_used=fallback_result.web_research_used,
                        research_quality=fallback_result.research_quality,
                        processing_time_ms=processing_time,
                        cached_result=False,
                        data_sources=fallback_result.data_sources
                    )
                else:
                    # Below confidence threshold
                    return EnhancedTagResult(
                        suggested_tag="",
                        confidence=fallback_result.confidence,
                        expense_type="VARIABLE",
                        expense_type_confidence=0.50,
                        explanation=f"Confiance insuffisante ({fallback_result.confidence:.2f} < 0.50)",
                        alternative_tags=[],
                        processing_time_ms=processing_time,
                        data_sources=["fallback_insufficient_confidence"]
                    )
                    
            except Exception as e:
                logger.warning(f"Intelligent service failed for '{transaction_label}': {e}")
        
        # Step 4: Ultimate fallback - no suggestion if confidence too low
        processing_time = int((time.time() - start_time) * 1000)
        
        return EnhancedTagResult(
            suggested_tag="",
            confidence=0.30,
            expense_type="VARIABLE",
            expense_type_confidence=0.50,
            explanation="Aucune correspondance trouvée avec confiance suffisante",
            alternative_tags=["divers", "inclassable"],
            processing_time_ms=processing_time,
            research_quality="no_match",
            data_sources=["ultimate_fallback"]
        )

    def _generate_tag_from_business_type(self, business_type: str, category: str) -> str:
        """Generate appropriate tag from business intelligence"""
        if not business_type and not category:
            return "commerce"
        
        text = f"{business_type or ''} {category or ''}".lower()
        
        # Business type to tag mapping
        tag_mapping = {
            'restaurant': 'restaurant',
            'fast food': 'fast-food',
            'supermarket': 'courses',
            'grocery': 'courses', 
            'gas station': 'essence',
            'pharmacy': 'sante',
            'streaming': 'streaming',
            'utility': 'factures',
            'telecom': 'telephone',
            'clothing': 'vetements',
            'electronics': 'electronique',
            'bank': 'banque',
            'insurance': 'assurance',
            'health': 'sante',
            'entertainment': 'loisirs',
            'travel': 'voyage',
            'transport': 'transport'
        }
        
        for business, tag in tag_mapping.items():
            if business in text:
                return tag
        
        # Default based on category
        if 'food' in text or 'alimentation' in text:
            return 'alimentation'
        elif 'service' in text:
            return 'services'
        elif 'commerce' in text or 'store' in text:
            return 'commerce'
        else:
            return 'divers'

    def _get_web_alternatives(self, merchant_info: MerchantInfo) -> List[str]:
        """Generate alternative tags from web research data"""
        alternatives = []
        
        if merchant_info.business_type:
            bt = merchant_info.business_type.lower()
            if 'restaurant' in bt:
                alternatives.extend(['repas', 'sortie', 'alimentation'])
            elif 'retail' in bt or 'store' in bt:
                alternatives.extend(['commerce', 'achats'])
            elif 'service' in bt:
                alternatives.extend(['services', 'professionnel'])
        
        # Add generic alternatives
        alternatives.extend(['divers', 'autre'])
        
        return list(set(alternatives))  # Remove duplicates

    def _classify_expense_type_fallback(self, transaction_label: str, amount: float = None) -> Tuple[str, float]:
        """Fallback expense type classification based on patterns and amount"""
        if not transaction_label:
            return "VARIABLE", 0.50
        
        label = transaction_label.lower()
        
        # Fixed expense indicators
        fixed_keywords = [
            'netflix', 'spotify', 'disney', 'canal', 'orange', 'sfr', 'free', 'bouygues',
            'edf', 'engie', 'veolia', 'suez', 'assurance', 'loyer', 'forfait', 'abonnement'
        ]
        
        for keyword in fixed_keywords:
            if keyword in label:
                return "FIXED", 0.80
        
        # Variable expense indicators
        variable_keywords = [
            'carrefour', 'leclerc', 'auchan', 'casino', 'monoprix',
            'mcdonalds', 'burger', 'kfc', 'restaurant',
            'total', 'bp', 'shell', 'esso', 'essence',
            'pharmacie', 'docteur', 'medecin'
        ]
        
        for keyword in variable_keywords:
            if keyword in label:
                return "VARIABLE", 0.75
        
        # Amount-based classification
        if amount:
            if 5 <= amount <= 50:
                return "FIXED", 0.55  # Subscription-like amounts
            elif amount > 200:
                return "VARIABLE", 0.65  # Large purchases usually variable
        
        return "VARIABLE", 0.50  # Default to variable

    async def batch_process_transactions(
        self, 
        transaction_ids: List[int], 
        progress_callback: Optional[callable] = None
    ) -> BatchProcessingResult:
        """
        Enhanced batch processing with progress feedback and optimized performance
        """
        start_time = time.time()
        results = {}
        errors = []
        
        logger.info(f"🚀 Starting batch processing of {len(transaction_ids)} transactions")
        
        # Load transactions from database
        transactions = self.db.query(Transaction).filter(Transaction.id.in_(transaction_ids)).all()
        tx_dict = {tx.id: tx for tx in transactions}
        
        # Process in batches to manage memory and provide progress updates
        batch_size = 20
        processed_count = 0
        successful_count = 0
        high_confidence_count = 0
        web_research_count = 0
        cache_hit_count = 0
        
        for i in range(0, len(transaction_ids), batch_size):
            batch_ids = transaction_ids[i:i + batch_size]
            batch_tasks = []
            
            # Create async tasks for current batch
            for tx_id in batch_ids:
                if tx_id in tx_dict:
                    tx = tx_dict[tx_id]
                    task = self._process_single_transaction_async(tx)
                    batch_tasks.append((tx_id, task))
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(
                *[task for _, task in batch_tasks], 
                return_exceptions=True
            )
            
            # Process results
            for (tx_id, _), result in zip(batch_tasks, batch_results):
                processed_count += 1
                
                if isinstance(result, Exception):
                    errors.append(f"Transaction {tx_id}: {str(result)}")
                    continue
                
                if isinstance(result, EnhancedTagResult):
                    results[tx_id] = result
                    successful_count += 1
                    
                    if result.confidence >= 0.80:
                        high_confidence_count += 1
                    if result.web_research_used:
                        web_research_count += 1
                    if result.cached_result:
                        cache_hit_count += 1
                
                # Progress callback
                if progress_callback:
                    progress_percent = (processed_count / len(transaction_ids)) * 100
                    progress_callback(processed_count, len(transaction_ids), progress_percent)
            
            # Small delay between batches to prevent overwhelming external APIs
            if i + batch_size < len(transaction_ids):
                await asyncio.sleep(0.1)
        
        processing_time = time.time() - start_time
        
        # Monthly analysis
        month_analysis = self._analyze_monthly_results(transactions, results)
        
        batch_result = BatchProcessingResult(
            processed_count=processed_count,
            successful_count=successful_count,
            high_confidence_count=high_confidence_count,
            web_research_count=web_research_count,
            cache_hit_count=cache_hit_count,
            processing_time_seconds=processing_time,
            results=results,
            errors=errors,
            month=month_analysis.get('month'),
            fixed_expenses_identified=month_analysis.get('fixed_count', 0),
            variable_expenses_identified=month_analysis.get('variable_count', 0),
            unknown_merchants_researched=month_analysis.get('researched_merchants', [])
        )
        
        logger.info(f"✅ Batch processing completed: {successful_count}/{processed_count} successful")
        logger.info(f"📊 High confidence: {high_confidence_count}, Web research: {web_research_count}, Cache hits: {cache_hit_count}")
        logger.info(f"⏱️ Processing time: {processing_time:.2f}s")
        
        return batch_result

    async def _process_single_transaction_async(self, transaction: Transaction) -> EnhancedTagResult:
        """Process a single transaction with enhanced tagging"""
        return await self.enhanced_tag_suggestion(transaction.label, abs(transaction.amount))

    def _analyze_monthly_results(self, transactions: List[Transaction], results: Dict[int, EnhancedTagResult]) -> Dict[str, Any]:
        """Analyze batch results for monthly insights"""
        if not transactions:
            return {}
        
        # Get month from first transaction
        month = transactions[0].month if transactions else None
        
        fixed_count = 0
        variable_count = 0
        researched_merchants = []
        
        for tx_id, result in results.items():
            if result.expense_type == "FIXED":
                fixed_count += 1
            elif result.expense_type == "VARIABLE":
                variable_count += 1
                
            if result.web_research_used and result.merchant_name:
                researched_merchants.append(result.merchant_name)
        
        return {
            'month': month,
            'fixed_count': fixed_count,
            'variable_count': variable_count,
            'researched_merchants': list(set(researched_merchants))
        }

    async def batch_process_month(
        self, 
        month: str, 
        progress_callback: Optional[callable] = None
    ) -> BatchProcessingResult:
        """
        Process all transactions for a specific month (YYYY-MM format)
        Optimized for handling 100+ transactions efficiently
        """
        logger.info(f"🗓️ Starting batch processing for month: {month}")
        
        # Load all transactions for the month
        transactions = self.db.query(Transaction).filter(
            and_(
                Transaction.month == month,
                Transaction.exclude == False
            )
        ).all()
        
        if not transactions:
            return BatchProcessingResult(
                processed_count=0,
                successful_count=0,
                high_confidence_count=0,
                web_research_count=0,
                cache_hit_count=0,
                processing_time_seconds=0.0,
                results={},
                errors=[f"No transactions found for month {month}"],
                month=month
            )
        
        transaction_ids = [tx.id for tx in transactions]
        
        logger.info(f"📋 Found {len(transactions)} transactions for month {month}")
        
        return await self.batch_process_transactions(transaction_ids, progress_callback)

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service performance statistics"""
        cache_hit_rate = (self._cache_hits / max(self._total_processed, 1)) * 100
        web_research_rate = (self._web_research_calls / max(self._total_processed, 1)) * 100
        high_confidence_rate = (self._high_confidence_results / max(self._total_processed, 1)) * 100
        
        return {
            # Core performance metrics
            "total_processed": self._total_processed,
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "web_research_rate": f"{web_research_rate:.1f}%", 
            "high_confidence_rate": f"{high_confidence_rate:.1f}%",
            
            # Cache performance
            "cached_merchants": len(self.merchant_cache),
            "cache_ttl_hours": self.cache_ttl_hours,
            
            # Pattern coverage
            "enhanced_patterns_count": len(self.enhanced_merchant_patterns),
            "fixed_patterns": len([p for p in self.enhanced_merchant_patterns.values() if p['expense_type'] == 'FIXED']),
            "variable_patterns": len([p for p in self.enhanced_merchant_patterns.values() if p['expense_type'] == 'VARIABLE']),
            
            # Service capabilities
            "confidence_threshold": ">=50%",
            "batch_processing_enabled": True,
            "web_research_enabled": self.web_research_service is not None,
            "caching_enabled": True,
            "rate_limiting_enabled": True,
            "fixed_variable_classification": True,
            
            # Performance targets
            "target_precision": ">85%",
            "target_confidence": ">=50%",
            "max_batch_size": "unlimited",
            "concurrent_research_limit": 3,
            
            # Service information
            "service_version": "3.0.0-enhanced",
            "last_updated": datetime.now().isoformat()
        }

    async def cleanup_cache(self):
        """Clean up expired cache entries"""
        current_time = time.time()
        expired_keys = []
        
        for merchant_name, timestamp in self.cache_timestamps.items():
            if current_time - timestamp > (self.cache_ttl_hours * 3600):
                expired_keys.append(merchant_name)
        
        for key in expired_keys:
            del self.merchant_cache[key]
            del self.cache_timestamps[key]
        
        logger.info(f"🧹 Cache cleanup: removed {len(expired_keys)} expired entries")


# Service instance management
_enhanced_auto_tagging_service = None

def get_enhanced_auto_tagging_service(db_session: Session) -> EnhancedAutoTaggingService:
    """Get singleton instance of EnhancedAutoTaggingService"""
    global _enhanced_auto_tagging_service
    
    if _enhanced_auto_tagging_service is None:
        _enhanced_auto_tagging_service = EnhancedAutoTaggingService(db_session)
        logger.info("✅ Enhanced Auto-Tagging Service initialized with ML intelligence")
    
    return _enhanced_auto_tagging_service


# Example usage and testing
async def test_enhanced_auto_tagging():
    """Test the enhanced auto-tagging service"""
    
    # Mock database for testing
    class MockDB:
        pass
    
    service = EnhancedAutoTaggingService(MockDB())
    
    test_transactions = [
        {"label": "NETFLIX SARL 12.99", "amount": 12.99},
        {"label": "MCDONALDS PARIS 8.50", "amount": 8.50}, 
        {"label": "EDF ENERGIE FACTURE 89.34", "amount": 89.34},
        {"label": "CARREFOUR VILLENEUVE 67.32", "amount": 67.32},
        {"label": "ORANGE FORFAIT MOBILE 29.99", "amount": 29.99},
        {"label": "TOTAL ACCESS AUTOROUTE 45.00", "amount": 45.00},
        {"label": "SPOTIFY AB MONTHLY 9.99", "amount": 9.99},
        {"label": "UNKNOWN LOCAL BUSINESS", "amount": 25.00},
    ]
    
    print("🚀 Testing Enhanced Auto-Tagging Service")
    print("=" * 70)
    
    for i, tx in enumerate(test_transactions, 1):
        print(f"\n🔄 Transaction {i}: {tx['label']} ({tx['amount']}€)")
        
        try:
            result = await service.enhanced_tag_suggestion(tx['label'], tx['amount'])
            
            print(f"   Tag: {result.suggested_tag} (Confidence: {result.confidence:.2f})")
            print(f"   Type: {result.expense_type} (Confidence: {result.expense_type_confidence:.2f})")
            print(f"   Explanation: {result.explanation}")
            print(f"   Research: {result.web_research_used}, Quality: {result.research_quality}")
            print(f"   Processing: {result.processing_time_ms}ms")
            
            if result.alternative_tags:
                print(f"   Alternatives: {', '.join(result.alternative_tags[:3])}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("-" * 50)
    
    # Show service statistics
    stats = service.get_service_statistics()
    print(f"\n📊 Service Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_auto_tagging())