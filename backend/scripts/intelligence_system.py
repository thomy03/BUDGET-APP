"""
Dynamic Knowledge Base Intelligence System

This module implements the intelligent learning system for the budget application,
providing advanced merchant classification, web research integration, and
machine learning capabilities for continuous improvement.
"""

import logging
import math
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from models.database import (
    MerchantKnowledgeBase, ResearchCache, Transaction, 
    LabelTagMapping, get_db
)

logger = logging.getLogger(__name__)


@dataclass
class IntelligenceMetrics:
    """Metrics for tracking intelligence system performance"""
    total_merchants: int
    verified_merchants: int
    confidence_avg: float
    success_rate_avg: float
    web_research_count: int
    user_corrections: int
    auto_classifications: int
    cache_hit_rate: float


@dataclass
class MerchantIntelligence:
    """Intelligent merchant information with scoring"""
    merchant_name: str
    normalized_name: str
    business_type: str
    category: str
    expense_type: str
    confidence_score: float
    data_sources: Dict[str, float]
    suggested_tags: List[str]
    location_info: Dict[str, Any]
    patterns: List[str]
    is_verified: bool


class KnowledgeScorer:
    """Advanced scoring system for merchant knowledge evaluation"""
    
    @staticmethod
    def calculate_confidence_score(
        web_confidence: float = 0.0,
        user_feedback_score: float = 0.0,
        usage_frequency: int = 0,
        data_sources_count: int = 0,
        research_quality: float = 0.0
    ) -> float:
        """
        Calculate intelligent confidence score using multiple factors
        
        Formula: weighted average of different confidence sources
        """
        # Base web research confidence (40% weight)
        web_weight = 0.4
        web_score = web_confidence * web_weight
        
        # User feedback and corrections (40% weight) 
        user_weight = 0.4
        user_score = user_feedback_score * user_weight
        
        # Usage frequency with logarithmic scaling (10% weight)
        frequency_weight = 0.1
        frequency_score = min(math.log(usage_frequency + 1) / 5.0, 1.0) * frequency_weight
        
        # Data source diversity bonus (10% weight)
        source_weight = 0.1
        source_score = min(data_sources_count / 3.0, 1.0) * source_weight
        
        # Research quality bonus
        quality_bonus = research_quality * 0.05
        
        final_score = web_score + user_score + frequency_score + source_score + quality_bonus
        
        return min(max(final_score, 0.0), 1.0)
    
    @staticmethod
    def calculate_success_rate(
        auto_classifications: int,
        user_corrections: int
    ) -> float:
        """Calculate success rate of automatic classifications"""
        total_classifications = auto_classifications + user_corrections
        if total_classifications == 0:
            return 1.0  # No data, assume perfect
        
        return auto_classifications / total_classifications
    
    @staticmethod
    def should_trigger_research(merchant_name: str, confidence: float) -> bool:
        """Determine if web research should be triggered"""
        # Trigger research for new merchants or low confidence
        return confidence < 0.7 or merchant_name.strip() == ""
    
    @staticmethod
    def normalize_merchant_name(merchant_name: str) -> str:
        """Normalize merchant name for consistent matching"""
        if not merchant_name:
            return ""
        
        # Remove common noise words and characters
        noise_patterns = [
            r'\b(SARL|SAS|SA|SASU|EURL|SNC|SCP)\b',
            r'\b(LTD|LLC|INC|CORP)\b', 
            r'\b(CB|CARTE)\b',
            r'[*\-_\.]',
            r'\d{2}/\d{2}',  # Remove dates
            r'\s+'
        ]
        
        normalized = merchant_name.upper().strip()
        
        for pattern in noise_patterns:
            normalized = re.sub(pattern, ' ', normalized)
        
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized


class MerchantIntelligenceEngine:
    """Core engine for merchant intelligence and learning"""
    
    def __init__(self, db: Session):
        self.db = db
        self.scorer = KnowledgeScorer()
    
    def get_or_create_merchant(self, merchant_name: str) -> MerchantKnowledgeBase:
        """Get existing merchant or create new one for learning"""
        normalized_name = self.scorer.normalize_merchant_name(merchant_name)
        
        # Try to find existing merchant
        merchant = self.db.query(MerchantKnowledgeBase).filter(
            or_(
                MerchantKnowledgeBase.merchant_name == merchant_name,
                MerchantKnowledgeBase.normalized_name == normalized_name
            )
        ).first()
        
        if merchant:
            # Update usage metrics
            merchant.usage_count += 1
            merchant.last_used = datetime.now()
            self.db.commit()
            return merchant
        
        # Create new merchant entry
        merchant = MerchantKnowledgeBase(
            merchant_name=merchant_name,
            normalized_name=normalized_name,
            confidence_score=0.1,  # Low initial confidence
            usage_count=1,
            created_by="auto_learning",
            needs_review=True  # Flag for potential research
        )
        
        self.db.add(merchant)
        self.db.commit()
        self.db.refresh(merchant)
        
        logger.info(f"Created new merchant entry: {merchant_name}")
        return merchant
    
    def update_merchant_intelligence(
        self, 
        merchant: MerchantKnowledgeBase,
        web_data: Optional[Dict] = None,
        user_correction: Optional[Dict] = None
    ) -> MerchantKnowledgeBase:
        """Update merchant intelligence with new data"""
        
        if web_data:
            self._apply_web_research_data(merchant, web_data)
        
        if user_correction:
            self._apply_user_correction(merchant, user_correction)
        
        # Recalculate confidence score
        merchant.confidence_score = self.scorer.calculate_confidence_score(
            web_confidence=merchant.research_quality or 0.0,
            user_feedback_score=merchant.accuracy_rating,
            usage_frequency=merchant.usage_count,
            data_sources_count=len(json.loads(merchant.data_sources or "{}")),
            research_quality=merchant.research_quality or 0.0
        )
        
        # Update success rate
        merchant.success_rate = self.scorer.calculate_success_rate(
            merchant.auto_classifications,
            merchant.user_corrections
        )
        
        merchant.last_updated = datetime.now()
        self.db.commit()
        
        logger.info(f"Updated merchant intelligence: {merchant.merchant_name} (confidence: {merchant.confidence_score:.2f})")
        return merchant
    
    def _apply_web_research_data(self, merchant: MerchantKnowledgeBase, web_data: Dict):
        """Apply web research data to merchant"""
        merchant.business_type = web_data.get('business_type')
        merchant.category = web_data.get('category')
        merchant.sub_category = web_data.get('sub_category')
        merchant.city = web_data.get('city')
        merchant.address = web_data.get('address')
        merchant.website_url = web_data.get('website')
        merchant.phone_number = web_data.get('phone')
        merchant.description = web_data.get('description')
        
        # Update data sources
        sources = json.loads(merchant.data_sources or "{}")
        sources.update(web_data.get('sources', {}))
        merchant.data_sources = json.dumps(sources)
        
        # Set research metadata
        merchant.research_date = datetime.now()
        merchant.research_quality = web_data.get('quality_score', 0.5)
        merchant.research_duration_ms = web_data.get('duration_ms', 0)
        
        # Auto-suggest expense type and tags
        merchant.suggested_expense_type = self._suggest_expense_type(web_data)
        merchant.suggested_tags = self._suggest_tags(web_data)
        
        merchant.auto_classifications += 1
        merchant.needs_review = False
    
    def _apply_user_correction(self, merchant: MerchantKnowledgeBase, correction: Dict):
        """Apply user correction to improve learning"""
        if 'expense_type' in correction:
            merchant.expense_type = correction['expense_type']
        
        if 'business_type' in correction:
            merchant.business_type = correction['business_type']
        
        if 'category' in correction:
            merchant.category = correction['category']
        
        if 'accuracy_rating' in correction:
            merchant.accuracy_rating = correction['accuracy_rating']
        
        merchant.user_corrections += 1
        merchant.is_validated = True
        
        # Learn patterns from corrections
        self._learn_from_correction(merchant, correction)
    
    def _suggest_expense_type(self, web_data: Dict) -> str:
        """Suggest expense type based on business intelligence"""
        business_type = web_data.get('business_type', '').lower()
        category = web_data.get('category', '').lower()
        
        # Fixed expense patterns
        fixed_patterns = [
            'insurance', 'assurance', 'utilities', 'rent', 'loyer',
            'subscription', 'abonnement', 'tax', 'impot', 'bank',
            'telecom', 'internet', 'phone', 'electricity', 'gas'
        ]
        
        # Provision expense patterns  
        provision_patterns = [
            'medical', 'healthcare', 'medical', 'vacation', 'travel',
            'maintenance', 'repair', 'emergency'
        ]
        
        text_to_check = f"{business_type} {category}".lower()
        
        if any(pattern in text_to_check for pattern in fixed_patterns):
            return "FIXED"
        elif any(pattern in text_to_check for pattern in provision_patterns):
            return "PROVISION"
        else:
            return "VARIABLE"
    
    def _suggest_tags(self, web_data: Dict) -> str:
        """Suggest tags based on business intelligence"""
        tags = []
        
        business_type = web_data.get('business_type', '').lower()
        category = web_data.get('category', '').lower()
        
        # Business type tags
        type_tag_mapping = {
            'restaurant': ['alimentation', 'restaurant'],
            'supermarket': ['courses', 'alimentation'],
            'gas_station': ['carburant', 'transport'],
            'pharmacy': ['sante', 'pharmacie'],
            'bank': ['banque', 'finance'],
            'insurance': ['assurance', 'fixe']
        }
        
        for key, tag_list in type_tag_mapping.items():
            if key in business_type:
                tags.extend(tag_list)
        
        # Category-specific tags
        if 'food' in category or 'grocery' in category:
            tags.append('alimentation')
        
        if 'health' in category or 'medical' in category:
            tags.append('sante')
        
        if 'transport' in category:
            tags.append('transport')
        
        return ','.join(list(set(tags)))
    
    def _learn_from_correction(self, merchant: MerchantKnowledgeBase, correction: Dict):
        """Learn patterns from user corrections to improve future predictions"""
        # Store pattern in label_tag_mappings for future reference
        if 'tags' in correction and correction['tags']:
            pattern_mapping = LabelTagMapping(
                label_pattern=merchant.normalized_name,
                suggested_tags=correction['tags'],
                confidence_score=0.8,  # High confidence from user input
                match_type="contains",
                created_by="user_correction"
            )
            
            # Check if mapping already exists
            existing = self.db.query(LabelTagMapping).filter(
                LabelTagMapping.label_pattern == merchant.normalized_name
            ).first()
            
            if existing:
                existing.suggested_tags = correction['tags']
                existing.confidence_score = min(existing.confidence_score + 0.1, 1.0)
                existing.accepted_count += 1
            else:
                self.db.add(pattern_mapping)
            
            self.db.commit()


class WebResearchEngine:
    """Engine for web research and caching"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_cached_research(self, search_term: str) -> Optional[Dict]:
        """Get cached research results if available and fresh"""
        cache_entry = self.db.query(ResearchCache).filter(
            ResearchCache.search_term == search_term.lower()
        ).first()
        
        if not cache_entry:
            return None
        
        # Check if cache is still fresh (30 days)
        if cache_entry.created_at < datetime.now() - timedelta(days=30):
            cache_entry.needs_refresh = True
            self.db.commit()
            return None
        
        # Update usage stats
        cache_entry.usage_count += 1
        cache_entry.last_used = datetime.now()
        self.db.commit()
        
        try:
            return json.loads(cache_entry.research_results)
        except json.JSONDecodeError:
            return None
    
    def cache_research_results(
        self, 
        search_term: str, 
        results: Dict, 
        confidence: float = 0.5,
        sources_count: int = 0,
        duration_ms: int = 0
    ):
        """Cache research results for future use"""
        cache_entry = ResearchCache(
            search_term=search_term.lower(),
            research_results=json.dumps(results),
            confidence_score=confidence,
            result_quality=self._evaluate_result_quality(results),
            sources_count=sources_count,
            search_duration_ms=duration_ms,
            research_method="web_search"
        )
        
        # Check if entry exists and update or create new
        existing = self.db.query(ResearchCache).filter(
            ResearchCache.search_term == search_term.lower()
        ).first()
        
        if existing:
            existing.research_results = cache_entry.research_results
            existing.confidence_score = cache_entry.confidence_score
            existing.result_quality = cache_entry.result_quality
            existing.sources_count = cache_entry.sources_count
            existing.last_used = datetime.now()
            existing.usage_count += 1
            existing.needs_refresh = False
        else:
            self.db.add(cache_entry)
        
        self.db.commit()
        logger.info(f"Cached research results for: {search_term}")
    
    def _evaluate_result_quality(self, results: Dict) -> float:
        """Evaluate the quality of research results"""
        quality_score = 0.0
        
        # Check for key information presence
        if results.get('business_type'):
            quality_score += 0.3
        
        if results.get('category'):
            quality_score += 0.2
        
        if results.get('location'):
            quality_score += 0.2
        
        if results.get('website'):
            quality_score += 0.15
        
        if results.get('description'):
            quality_score += 0.15
        
        return min(quality_score, 1.0)


class IntelligenceAnalytics:
    """Analytics and reporting for the intelligence system"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_intelligence_report(self) -> Dict:
        """Generate comprehensive intelligence system report"""
        # Get basic metrics
        total_merchants = self.db.query(MerchantKnowledgeBase).count()
        verified_merchants = self.db.query(MerchantKnowledgeBase).filter(
            MerchantKnowledgeBase.is_verified == True
        ).count()
        
        # Calculate average confidence
        avg_confidence = self.db.query(
            func.avg(MerchantKnowledgeBase.confidence_score)
        ).scalar() or 0.0
        
        # Calculate average success rate
        avg_success_rate = self.db.query(
            func.avg(MerchantKnowledgeBase.success_rate)
        ).scalar() or 0.0
        
        # Get research statistics
        research_count = self.db.query(ResearchCache).count()
        total_usage = self.db.query(
            func.sum(ResearchCache.usage_count)
        ).scalar() or 0
        
        cache_hit_rate = (total_usage / max(research_count, 1)) if research_count > 0 else 0.0
        
        # Get correction statistics
        total_corrections = self.db.query(
            func.sum(MerchantKnowledgeBase.user_corrections)
        ).scalar() or 0
        
        total_auto_classifications = self.db.query(
            func.sum(MerchantKnowledgeBase.auto_classifications)
        ).scalar() or 0
        
        # Top performing merchants by confidence
        top_merchants = self.db.query(MerchantKnowledgeBase).filter(
            MerchantKnowledgeBase.confidence_score >= 0.8
        ).order_by(
            MerchantKnowledgeBase.confidence_score.desc()
        ).limit(10).all()
        
        # Merchants needing review
        needs_review = self.db.query(MerchantKnowledgeBase).filter(
            MerchantKnowledgeBase.needs_review == True
        ).count()
        
        return {
            'generated_at': datetime.now().isoformat(),
            'metrics': {
                'total_merchants': total_merchants,
                'verified_merchants': verified_merchants,
                'confidence_avg': round(avg_confidence, 3),
                'success_rate_avg': round(avg_success_rate, 3),
                'web_research_count': research_count,
                'user_corrections': total_corrections,
                'auto_classifications': total_auto_classifications,
                'cache_hit_rate': round(cache_hit_rate, 3)
            },
            'top_performers': [
                {
                    'name': m.merchant_name,
                    'confidence': round(m.confidence_score, 3),
                    'usage_count': m.usage_count,
                    'success_rate': round(m.success_rate, 3)
                } for m in top_merchants
            ],
            'needs_attention': {
                'merchants_needing_review': needs_review,
                'low_confidence_merchants': self.db.query(MerchantKnowledgeBase).filter(
                    MerchantKnowledgeBase.confidence_score < 0.3
                ).count()
            },
            'learning_efficiency': {
                'correction_rate': round(total_corrections / max(total_auto_classifications, 1), 3),
                'verification_rate': round(verified_merchants / max(total_merchants, 1), 3)
            }
        }
    
    def get_merchant_patterns(self) -> Dict:
        """Analyze merchant patterns for insights"""
        # Business type distribution
        business_types = self.db.query(
            MerchantKnowledgeBase.business_type,
            func.count(MerchantKnowledgeBase.id).label('count')
        ).filter(
            MerchantKnowledgeBase.business_type.isnot(None)
        ).group_by(MerchantKnowledgeBase.business_type).all()
        
        # Geographic distribution
        cities = self.db.query(
            MerchantKnowledgeBase.city,
            func.count(MerchantKnowledgeBase.id).label('count')
        ).filter(
            MerchantKnowledgeBase.city.isnot(None)
        ).group_by(MerchantKnowledgeBase.city).all()
        
        # Confidence distribution
        confidence_ranges = {
            'high (0.8-1.0)': self.db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.confidence_score >= 0.8
            ).count(),
            'medium (0.5-0.8)': self.db.query(MerchantKnowledgeBase).filter(
                and_(
                    MerchantKnowledgeBase.confidence_score >= 0.5,
                    MerchantKnowledgeBase.confidence_score < 0.8
                )
            ).count(),
            'low (0.0-0.5)': self.db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.confidence_score < 0.5
            ).count()
        }
        
        return {
            'business_type_distribution': [
                {'type': bt[0], 'count': bt[1]} for bt in business_types
            ],
            'geographic_distribution': [
                {'city': city[0], 'count': city[1]} for city in cities
            ],
            'confidence_distribution': confidence_ranges
        }


# Utility functions for easy access

def get_intelligence_engine(db: Session = None) -> MerchantIntelligenceEngine:
    """Get merchant intelligence engine instance"""
    if db is None:
        db = next(get_db())
    return MerchantIntelligenceEngine(db)


def get_web_research_engine(db: Session = None) -> WebResearchEngine:
    """Get web research engine instance"""
    if db is None:
        db = next(get_db())
    return WebResearchEngine(db)


def get_intelligence_analytics(db: Session = None) -> IntelligenceAnalytics:
    """Get intelligence analytics instance"""
    if db is None:
        db = next(get_db())
    return IntelligenceAnalytics(db)


logger.info("Intelligence system initialized successfully")