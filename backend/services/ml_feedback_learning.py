"""
ML Feedback Learning Integration Service
Integrates user feedback into the ML classification pipeline for continuous improvement

This service enhances the existing expense classification system by:
1. Loading learned patterns from user feedback
2. Prioritizing user corrections over default rules
3. Updating confidence scores based on historical feedback
4. Providing explainable AI decisions with feedback-based reasoning

Author: Claude Code - ML Backend Architect
"""

import logging
import re
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from collections import defaultdict, Counter
from dataclasses import dataclass

from models.database import MLFeedback, Transaction, MerchantKnowledgeBase, TagFixedLineMapping
from services.expense_classification import ExpenseClassificationService, ClassificationResult

logger = logging.getLogger(__name__)


@dataclass
class FeedbackPattern:
    """Represents a learned pattern from user feedback"""
    merchant_pattern: str
    learned_tag: str
    learned_expense_type: str
    confidence_score: float
    usage_count: int
    success_rate: float
    last_used: Optional[datetime]
    source: str = "feedback"


class MLFeedbackLearningService:
    """
    Enhanced ML service that learns from user feedback and improves classification accuracy
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.base_classifier = ExpenseClassificationService()
        self.feedback_patterns: Dict[str, FeedbackPattern] = {}
        self.merchant_corrections: Dict[str, Dict[str, Any]] = {}
        self._load_feedback_patterns()
    
    def _load_feedback_patterns(self):
        """Load learned patterns from feedback data on initialization"""
        try:
            # Load patterns that have been successfully learned from feedback
            learned_patterns = self.db.query(
                MLFeedback.merchant_pattern,
                MLFeedback.corrected_tag,
                MLFeedback.corrected_expense_type,
                func.count(MLFeedback.id).label('usage_count'),
                func.avg(MLFeedback.pattern_success_rate).label('success_rate'),
                func.max(MLFeedback.applied_at).label('last_used')
            ).filter(
                and_(
                    MLFeedback.pattern_learned == True,
                    MLFeedback.merchant_pattern.isnot(None),
                    or_(
                        MLFeedback.corrected_tag.isnot(None),
                        MLFeedback.corrected_expense_type.isnot(None)
                    )
                )
            ).group_by(
                MLFeedback.merchant_pattern,
                MLFeedback.corrected_tag,
                MLFeedback.corrected_expense_type
            ).all()
            
            for pattern in learned_patterns:
                if pattern.merchant_pattern:
                    # Calculate confidence based on usage and success rate
                    base_confidence = min(0.95, 0.6 + (pattern.usage_count * 0.05))
                    success_boost = (pattern.success_rate or 0.8) * 0.2
                    final_confidence = min(0.98, base_confidence + success_boost)
                    
                    self.feedback_patterns[pattern.merchant_pattern] = FeedbackPattern(
                        merchant_pattern=pattern.merchant_pattern,
                        learned_tag=pattern.corrected_tag or "",
                        learned_expense_type=pattern.corrected_expense_type or "VARIABLE",
                        confidence_score=final_confidence,
                        usage_count=pattern.usage_count,
                        success_rate=pattern.success_rate or 0.8,
                        last_used=pattern.last_used
                    )
            
            # Load merchant knowledge base entries created from feedback
            merchant_entries = self.db.query(MerchantKnowledgeBase).filter(
                and_(
                    MerchantKnowledgeBase.created_by == "feedback_learning",
                    MerchantKnowledgeBase.is_active == True
                )
            ).all()
            
            for merchant in merchant_entries:
                if merchant.normalized_name not in self.feedback_patterns:
                    self.feedback_patterns[merchant.normalized_name] = FeedbackPattern(
                        merchant_pattern=merchant.normalized_name,
                        learned_tag=merchant.suggested_tags or "",
                        learned_expense_type=merchant.expense_type,
                        confidence_score=merchant.confidence_score,
                        usage_count=merchant.usage_count,
                        success_rate=merchant.success_rate,
                        last_used=merchant.last_used
                    )
            
            # Load correction patterns for confidence adjustment
            self._load_correction_patterns()
            
            logger.info(f"Loaded {len(self.feedback_patterns)} feedback patterns for ML enhancement")
            
        except Exception as e:
            logger.error(f"Error loading feedback patterns: {e}")
            self.feedback_patterns = {}
    
    def _load_correction_patterns(self):
        """Load patterns of frequent corrections to adjust confidence"""
        try:
            # Get frequently corrected tags and expense types
            correction_patterns = self.db.query(
                MLFeedback.original_tag,
                MLFeedback.original_expense_type,
                MLFeedback.corrected_tag,
                MLFeedback.corrected_expense_type,
                func.count(MLFeedback.id).label('correction_count'),
                func.avg(MLFeedback.confidence_before).label('avg_confidence_before')
            ).filter(
                MLFeedback.feedback_type == 'correction'
            ).group_by(
                MLFeedback.original_tag,
                MLFeedback.original_expense_type,
                MLFeedback.corrected_tag,
                MLFeedback.corrected_expense_type
            ).having(func.count(MLFeedback.id) >= 2).all()
            
            for correction in correction_patterns:
                original_key = f"{correction.original_tag}:{correction.original_expense_type}"
                if original_key not in self.merchant_corrections:
                    self.merchant_corrections[original_key] = {}
                
                self.merchant_corrections[original_key] = {
                    'correction_count': correction.correction_count,
                    'avg_confidence_before': correction.avg_confidence_before or 0.5,
                    'corrected_tag': correction.corrected_tag,
                    'corrected_expense_type': correction.corrected_expense_type,
                    'confidence_penalty': min(0.4, correction.correction_count * 0.1)
                }
            
            logger.info(f"Loaded {len(self.merchant_corrections)} correction patterns")
            
        except Exception as e:
            logger.error(f"Error loading correction patterns: {e}")
    
    def normalize_merchant_name(self, description: str) -> str:
        """Normalize merchant name for pattern matching (consistent with feedback service)"""
        if not description:
            return ""
            
        clean_desc = description.upper()
        
        # Remove common banking patterns
        patterns_to_remove = [
            r'^CB\s+',  # Carte Bleue
            r'^CARTE\s+',
            r'^VIR\s+',  # Virement
            r'^PRLV\s+',  # Prélèvement
            r'^CHQ\s+',  # Chèque
            r'\s+\d{2}/\d{2}$',  # Date patterns
            r'\s+\d{1,2}H\d{2}$',  # Time patterns
            r'\s+\d+\.\d{2}$',  # Amount patterns
        ]
        
        for pattern in patterns_to_remove:
            clean_desc = re.sub(pattern, '', clean_desc)
        
        # Extract meaningful merchant part
        words = clean_desc.strip().split()
        if words:
            meaningful_words = [w for w in words[:3] if not w.isdigit() and len(w) > 2]
            if meaningful_words:
                return ' '.join(meaningful_words[:2]).lower()
        
        return clean_desc.strip().lower()[:50]
    
    def classify_with_feedback(self, transaction_label: str, amount: float = 0.0, 
                             use_web_research: bool = False) -> ClassificationResult:
        """
        Enhanced classification that prioritizes user feedback patterns
        """
        # Normalize merchant name for pattern matching
        normalized_merchant = self.normalize_merchant_name(transaction_label)
        
        # Check for learned feedback patterns first (highest priority)
        feedback_result = self._check_feedback_patterns(normalized_merchant, transaction_label, amount)
        if feedback_result:
            return feedback_result
        
        # Get base classification from original service
        base_result = self.base_classifier.classify_transaction(
            transaction_label, amount, use_web_research
        )
        
        # Apply feedback-based confidence adjustments
        adjusted_result = self._apply_feedback_adjustments(base_result, normalized_merchant)
        
        return adjusted_result
    
    def _check_feedback_patterns(self, normalized_merchant: str, 
                               transaction_label: str, amount: float) -> Optional[ClassificationResult]:
        """Check if transaction matches learned feedback patterns"""
        
        # Direct pattern match
        if normalized_merchant in self.feedback_patterns:
            pattern = self.feedback_patterns[normalized_merchant]
            
            # Update usage statistics
            self._update_pattern_usage(normalized_merchant)
            
            explanation = f"Learned from user feedback: {pattern.learned_tag} (confidence: {pattern.confidence_score:.2f})"
            if pattern.usage_count > 1:
                explanation += f" - Pattern used {pattern.usage_count} times"
            
            return ClassificationResult(
                expense_type=pattern.learned_expense_type,
                confidence=pattern.confidence_score,
                primary_reason="user_feedback_pattern",
                contributing_factors=[
                    f"Exact pattern match: {normalized_merchant}",
                    f"Learned from {pattern.usage_count} user corrections",
                    f"Success rate: {pattern.success_rate:.2f}"
                ],
                keyword_matches=[normalized_merchant],
                suggested_tag=pattern.learned_tag,
                tag_confidence=pattern.confidence_score,
                alternative_tags=[],
                tag_explanation=explanation,
                web_research_used=False
            )
        
        # Partial pattern matching (substring match for similar merchants)
        for pattern_key, pattern in self.feedback_patterns.items():
            if (len(pattern_key) > 3 and pattern_key in normalized_merchant) or \
               (len(normalized_merchant) > 3 and normalized_merchant in pattern_key):
                
                # Reduced confidence for partial matches
                partial_confidence = pattern.confidence_score * 0.7
                
                if partial_confidence > 0.5:  # Only use if still reasonably confident
                    explanation = f"Similar to learned pattern '{pattern_key}': {pattern.learned_tag}"
                    
                    return ClassificationResult(
                        expense_type=pattern.learned_expense_type,
                        confidence=partial_confidence,
                        primary_reason="user_feedback_pattern_partial",
                        contributing_factors=[
                            f"Partial pattern match: {pattern_key}",
                            f"Similarity with learned pattern",
                            f"Original confidence: {pattern.confidence_score:.2f}"
                        ],
                        keyword_matches=[pattern_key],
                        suggested_tag=pattern.learned_tag,
                        tag_confidence=partial_confidence,
                        alternative_tags=[],
                        tag_explanation=explanation,
                        web_research_used=False
                    )
        
        return None
    
    def _apply_feedback_adjustments(self, base_result: ClassificationResult, 
                                  normalized_merchant: str) -> ClassificationResult:
        """Apply feedback-based confidence adjustments to base classification"""
        
        # Check if this tag/expense_type combination has been frequently corrected
        result_key = f"{base_result.suggested_tag}:{base_result.expense_type}"
        
        if result_key in self.merchant_corrections:
            correction_info = self.merchant_corrections[result_key]
            
            # Apply confidence penalty for frequently corrected combinations
            confidence_penalty = correction_info['confidence_penalty']
            adjusted_confidence = max(0.1, base_result.confidence - confidence_penalty)
            
            # Update explanation
            adjusted_explanation = base_result.tag_explanation or base_result.primary_reason
            adjusted_explanation += f" (Confidence adjusted -{confidence_penalty:.2f} due to {correction_info['correction_count']} user corrections)"
            
            # Suggest the most common correction as alternative
            alternative_tags = base_result.alternative_tags or []
            if correction_info['corrected_tag'] and correction_info['corrected_tag'] not in alternative_tags:
                alternative_tags = [correction_info['corrected_tag']] + alternative_tags[:2]
            
            return ClassificationResult(
                expense_type=base_result.expense_type,
                confidence=adjusted_confidence,
                primary_reason=f"{base_result.primary_reason}_feedback_adjusted",
                contributing_factors=base_result.contributing_factors + [
                    f"Confidence reduced due to {correction_info['correction_count']} user corrections",
                    f"Users often correct to: {correction_info['corrected_tag']}"
                ],
                keyword_matches=base_result.keyword_matches,
                stability_score=base_result.stability_score,
                frequency_score=base_result.frequency_score,
                suggested_tag=base_result.suggested_tag,
                tag_confidence=adjusted_confidence,
                alternative_tags=alternative_tags,
                tag_explanation=adjusted_explanation,
                web_research_used=base_result.web_research_used,
                merchant_info=base_result.merchant_info
            )
        
        return base_result
    
    def _update_pattern_usage(self, merchant_pattern: str):
        """Update usage statistics for a feedback pattern"""
        try:
            # Update in-memory pattern
            if merchant_pattern in self.feedback_patterns:
                self.feedback_patterns[merchant_pattern].usage_count += 1
                self.feedback_patterns[merchant_pattern].last_used = datetime.utcnow()
            
            # Update database feedback records
            self.db.query(MLFeedback).filter(
                MLFeedback.merchant_pattern == merchant_pattern
            ).update({
                'times_pattern_used': MLFeedback.times_pattern_used + 1
            })
            
            # Update merchant knowledge base
            self.db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.normalized_name == merchant_pattern
            ).update({
                'usage_count': MerchantKnowledgeBase.usage_count + 1,
                'last_used': datetime.utcnow()
            })
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating pattern usage for {merchant_pattern}: {e}")
    
    def get_feedback_enhanced_suggestions(self, transaction_label: str, 
                                        amount: float = 0.0, 
                                        top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Get multiple tag suggestions enhanced with feedback learning
        """
        # Get primary suggestion
        primary_result = self.classify_with_feedback(transaction_label, amount)
        
        suggestions = [{
            'tag': primary_result.suggested_tag,
            'expense_type': primary_result.expense_type,
            'confidence': primary_result.confidence,
            'explanation': primary_result.tag_explanation or primary_result.primary_reason,
            'source': 'feedback_enhanced' if 'feedback' in primary_result.primary_reason else 'base_classifier'
        }]
        
        # Add alternative suggestions
        if primary_result.alternative_tags:
            for alt_tag in primary_result.alternative_tags[:top_n-1]:
                suggestions.append({
                    'tag': alt_tag,
                    'expense_type': 'VARIABLE',  # Default for alternatives
                    'confidence': primary_result.confidence * 0.7,  # Reduced confidence
                    'explanation': f"Alternative suggestion to {primary_result.suggested_tag}",
                    'source': 'alternative'
                })
        
        # Add feedback-based alternatives if available
        normalized_merchant = self.normalize_merchant_name(transaction_label)
        for pattern_key, pattern in self.feedback_patterns.items():
            if len(suggestions) >= top_n:
                break
                
            if (pattern_key != normalized_merchant and 
                pattern.learned_tag not in [s['tag'] for s in suggestions] and
                (pattern_key in normalized_merchant or normalized_merchant in pattern_key)):
                
                suggestions.append({
                    'tag': pattern.learned_tag,
                    'expense_type': pattern.learned_expense_type,
                    'confidence': pattern.confidence_score * 0.6,  # Reduced for partial match
                    'explanation': f"Based on similar pattern: {pattern_key}",
                    'source': 'feedback_similarity'
                })
        
        return suggestions[:top_n]
    
    def reload_patterns(self):
        """Reload feedback patterns from database (call after new feedback is added)"""
        self.feedback_patterns.clear()
        self.merchant_corrections.clear()
        self._load_feedback_patterns()
        logger.info("Feedback patterns reloaded")
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded feedback patterns"""
        if not self.feedback_patterns:
            return {
                'total_patterns': 0,
                'high_confidence_patterns': 0,
                'frequently_used_patterns': 0,
                'average_confidence': 0.0,
                'correction_patterns': len(self.merchant_corrections)
            }
        
        high_confidence = sum(1 for p in self.feedback_patterns.values() if p.confidence_score > 0.8)
        frequently_used = sum(1 for p in self.feedback_patterns.values() if p.usage_count > 5)
        avg_confidence = sum(p.confidence_score for p in self.feedback_patterns.values()) / len(self.feedback_patterns)
        
        return {
            'total_patterns': len(self.feedback_patterns),
            'high_confidence_patterns': high_confidence,
            'frequently_used_patterns': frequently_used,
            'average_confidence': avg_confidence,
            'correction_patterns': len(self.merchant_corrections),
            'top_patterns': [
                {
                    'pattern': pattern.merchant_pattern,
                    'tag': pattern.learned_tag,
                    'confidence': pattern.confidence_score,
                    'usage_count': pattern.usage_count
                }
                for pattern in sorted(self.feedback_patterns.values(), 
                                    key=lambda x: x.usage_count, reverse=True)[:5]
            ]
        }