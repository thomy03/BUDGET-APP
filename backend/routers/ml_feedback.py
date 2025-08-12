"""
ML Feedback Learning System
Comprehensive feedback collection and pattern learning for AI classification improvements

This module implements:
1. User correction collection for ML model improvement
2. Pattern learning from feedback data
3. Confidence score adjustments based on user feedback
4. Integration with expense classification service for continuous learning

Author: Claude Code - ML Backend Architect
"""

import logging
import re
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from collections import defaultdict, Counter

from models.database import get_db, MLFeedback, Transaction, MerchantKnowledgeBase
from models.schemas import (
    MLFeedbackCreate, MLFeedbackResponse, MLFeedbackStats, 
    MLLearningPattern, BatchResultsSummary
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ml-feedback", tags=["ML Feedback Learning"])


class MLFeedbackService:
    """Service for managing ML feedback and learning patterns"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def normalize_merchant_name(self, description: str) -> str:
        """Normalize merchant name from transaction description for pattern matching"""
        if not description:
            return ""
            
        # Clean common prefixes and suffixes
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
        
        # Extract meaningful merchant part (first meaningful word sequence)
        words = clean_desc.strip().split()
        if words:
            # Take first 2-3 meaningful words, exclude numbers-only words
            meaningful_words = [w for w in words[:3] if not w.isdigit() and len(w) > 2]
            if meaningful_words:
                return ' '.join(meaningful_words[:2]).lower()
        
        return clean_desc.strip().lower()[:50]  # Fallback
    
    def extract_learning_data(self, transaction: Transaction) -> Dict[str, Any]:
        """Extract learning data from transaction for pattern recognition"""
        return {
            'merchant_pattern': self.normalize_merchant_name(transaction.label or ''),
            'transaction_amount': transaction.amount,
            'transaction_description': transaction.label or '',
            'category': transaction.category or '',
            'account_label': transaction.account_label or ''
        }
    
    def save_feedback(self, feedback_data: MLFeedbackCreate, user_id: str = "system") -> MLFeedback:
        """Save user feedback and extract learning patterns"""
        
        # Get transaction details
        transaction = self.db.query(Transaction).filter(
            Transaction.id == feedback_data.transaction_id
        ).first()
        
        if not transaction:
            raise HTTPException(
                status_code=404,
                detail=f"Transaction {feedback_data.transaction_id} not found"
            )
        
        # Extract learning data
        learning_data = self.extract_learning_data(transaction)
        
        # Create feedback record
        feedback = MLFeedback(
            transaction_id=feedback_data.transaction_id,
            original_tag=feedback_data.original_tag,
            corrected_tag=feedback_data.corrected_tag,
            original_expense_type=feedback_data.original_expense_type,
            corrected_expense_type=feedback_data.corrected_expense_type,
            merchant_pattern=learning_data['merchant_pattern'],
            transaction_amount=learning_data['transaction_amount'],
            transaction_description=learning_data['transaction_description'],
            feedback_type=feedback_data.feedback_type,
            confidence_before=feedback_data.confidence_before,
            user_id=user_id,
            pattern_learned=False,  # Will be updated when pattern is learned
            times_pattern_used=0,
            pattern_success_rate=0.0
        )
        
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        
        # Trigger pattern learning update
        self._update_learned_patterns()
        
        logger.info(f"Saved ML feedback for transaction {feedback_data.transaction_id}: {feedback_data.feedback_type}")
        
        return feedback
    
    def _update_learned_patterns(self):
        """Update learned patterns based on accumulated feedback"""
        
        # Group feedback by merchant pattern
        feedback_groups = self.db.query(
            MLFeedback.merchant_pattern,
            MLFeedback.corrected_tag,
            MLFeedback.corrected_expense_type,
            func.count(MLFeedback.id).label('feedback_count'),
            func.avg(MLFeedback.confidence_before).label('avg_confidence_before')
        ).filter(
            and_(
                MLFeedback.merchant_pattern.isnot(None),
                MLFeedback.merchant_pattern != '',
                MLFeedback.feedback_type == 'correction'
            )
        ).group_by(
            MLFeedback.merchant_pattern,
            MLFeedback.corrected_tag,
            MLFeedback.corrected_expense_type
        ).having(func.count(MLFeedback.id) >= 2).all()  # At least 2 corrections for pattern
        
        patterns_updated = 0
        
        for group in feedback_groups:
            merchant_pattern = group.merchant_pattern
            corrected_tag = group.corrected_tag
            corrected_expense_type = group.corrected_expense_type
            feedback_count = group.feedback_count
            avg_confidence_before = group.avg_confidence_before or 0.5
            
            if not corrected_tag and not corrected_expense_type:
                continue  # Skip if no useful correction
            
            # Calculate pattern confidence based on consistency
            pattern_confidence = min(0.95, 0.5 + (feedback_count * 0.1))
            
            # Update merchant knowledge base if pattern exists
            merchant_entry = self.db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.normalized_name == merchant_pattern
            ).first()
            
            if merchant_entry:
                # Update existing entry with learned information
                if corrected_tag:
                    merchant_entry.suggested_tags = corrected_tag
                if corrected_expense_type:
                    merchant_entry.expense_type = corrected_expense_type
                
                merchant_entry.confidence_score = pattern_confidence
                merchant_entry.user_corrections += feedback_count
                merchant_entry.last_updated = datetime.utcnow()
                merchant_entry.success_rate = pattern_confidence
                
            else:
                # Create new merchant knowledge entry from feedback
                merchant_entry = MerchantKnowledgeBase(
                    merchant_name=merchant_pattern,
                    normalized_name=merchant_pattern,
                    business_type="learned_from_feedback",
                    expense_type=corrected_expense_type or "VARIABLE",
                    confidence_score=pattern_confidence,
                    suggested_tags=corrected_tag,
                    usage_count=1,
                    user_corrections=feedback_count,
                    success_rate=pattern_confidence,
                    created_by="feedback_learning",
                    is_active=True,
                    is_verified=False,
                    needs_review=False
                )
                self.db.add(merchant_entry)
            
            # Mark feedback entries as contributing to learned patterns
            self.db.query(MLFeedback).filter(
                and_(
                    MLFeedback.merchant_pattern == merchant_pattern,
                    MLFeedback.corrected_tag == corrected_tag,
                    MLFeedback.corrected_expense_type == corrected_expense_type
                )
            ).update({
                'pattern_learned': True,
                'applied_at': datetime.utcnow()
            })
            
            patterns_updated += 1
        
        self.db.commit()
        
        if patterns_updated > 0:
            logger.info(f"Updated {patterns_updated} learned patterns from feedback")
    
    def get_learned_patterns(self, limit: int = 50) -> List[MLLearningPattern]:
        """Retrieve learned patterns from feedback data"""
        
        # Get patterns that have been learned and are being used
        learned_patterns = self.db.query(
            MLFeedback.merchant_pattern,
            MLFeedback.corrected_tag,
            MLFeedback.corrected_expense_type,
            func.avg(MLFeedback.confidence_before).label('confidence_score'),
            func.count(MLFeedback.id).label('usage_count'),
            func.avg(MLFeedback.pattern_success_rate).label('success_rate'),
            func.max(MLFeedback.applied_at).label('last_used'),
            func.min(MLFeedback.created_at).label('created_from_feedback')
        ).filter(
            and_(
                MLFeedback.pattern_learned == True,
                MLFeedback.merchant_pattern.isnot(None),
                MLFeedback.corrected_tag.isnot(None)
            )
        ).group_by(
            MLFeedback.merchant_pattern,
            MLFeedback.corrected_tag,
            MLFeedback.corrected_expense_type
        ).order_by(
            desc('usage_count'),
            desc('confidence_score')
        ).limit(limit).all()
        
        patterns = []
        for pattern in learned_patterns:
            patterns.append(MLLearningPattern(
                merchant_pattern=pattern.merchant_pattern,
                learned_tag=pattern.corrected_tag,
                learned_expense_type=pattern.corrected_expense_type or "VARIABLE",
                confidence_score=min(1.0, (pattern.confidence_score or 0.5) + 0.3),  # Boost learned patterns
                usage_count=pattern.usage_count,
                success_rate=pattern.success_rate or 0.8,  # Default good success rate
                last_used=pattern.last_used,
                created_from_feedback=pattern.created_from_feedback
            ))
        
        return patterns
    
    def get_feedback_stats(self) -> MLFeedbackStats:
        """Get comprehensive feedback statistics"""
        
        # Basic counts
        total_feedback = self.db.query(MLFeedback).count()
        corrections = self.db.query(MLFeedback).filter(MLFeedback.feedback_type == 'correction').count()
        acceptances = self.db.query(MLFeedback).filter(MLFeedback.feedback_type == 'acceptance').count()
        manual_entries = self.db.query(MLFeedback).filter(MLFeedback.feedback_type == 'manual').count()
        patterns_learned = self.db.query(MLFeedback).filter(MLFeedback.pattern_learned == True).count()
        
        # Most corrected tags
        most_corrected = self.db.query(
            MLFeedback.original_tag,
            func.count(MLFeedback.id).label('correction_count')
        ).filter(
            and_(
                MLFeedback.feedback_type == 'correction',
                MLFeedback.original_tag.isnot(None)
            )
        ).group_by(MLFeedback.original_tag).order_by(desc('correction_count')).limit(10).all()
        
        most_corrected_tags = [
            {"tag": tag.original_tag, "corrections": tag.correction_count}
            for tag in most_corrected
        ]
        
        # Calculate average confidence improvement
        confidence_improvements = self.db.query(
            MLFeedback.confidence_before
        ).filter(
            and_(
                MLFeedback.confidence_before.isnot(None),
                MLFeedback.feedback_type == 'correction'
            )
        ).all()
        
        avg_confidence_improvement = 0.0
        if confidence_improvements:
            # Assume improvement is the difference between target confidence (0.8) and before
            improvements = [max(0, 0.8 - c.confidence_before) for c in confidence_improvements if c.confidence_before]
            avg_confidence_improvement = sum(improvements) / len(improvements) if improvements else 0.0
        
        # Learning success rate (patterns that are being used vs total patterns)
        total_patterns = self.db.query(MLFeedback).filter(MLFeedback.pattern_learned == True).count()
        used_patterns = self.db.query(MLFeedback).filter(
            and_(MLFeedback.pattern_learned == True, MLFeedback.times_pattern_used > 0)
        ).count()
        
        learning_success_rate = (used_patterns / total_patterns) if total_patterns > 0 else 0.0
        
        return MLFeedbackStats(
            total_feedback_entries=total_feedback,
            corrections_count=corrections,
            acceptances_count=acceptances,
            manual_entries_count=manual_entries,
            patterns_learned=patterns_learned,
            average_confidence_improvement=avg_confidence_improvement,
            most_corrected_tags=most_corrected_tags,
            learning_success_rate=learning_success_rate
        )


@router.post("/", response_model=MLFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def save_ml_feedback(
    feedback: MLFeedbackCreate,
    db: Session = Depends(get_db),
    user_id: str = "system"  # TODO: Get from authentication
):
    """
    Save user feedback for ML model improvement
    
    This endpoint collects user corrections and acceptance/rejection of ML suggestions
    to continuously improve the classification accuracy.
    """
    try:
        service = MLFeedbackService(db)
        saved_feedback = service.save_feedback(feedback, user_id)
        
        return MLFeedbackResponse.from_orm(saved_feedback)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving ML feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save feedback: {str(e)}"
        )


@router.get("/patterns", response_model=List[MLLearningPattern])
async def get_learned_patterns(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of patterns to return"),
    db: Session = Depends(get_db)
):
    """
    Retrieve learned patterns from user feedback
    
    Returns patterns that the ML system has learned from user corrections,
    ordered by usage count and confidence score.
    """
    try:
        service = MLFeedbackService(db)
        patterns = service.get_learned_patterns(limit)
        
        logger.info(f"Retrieved {len(patterns)} learned patterns")
        return patterns
        
    except Exception as e:
        logger.error(f"Error retrieving learned patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve patterns: {str(e)}"
        )


@router.get("/stats", response_model=MLFeedbackStats)
async def get_feedback_statistics(db: Session = Depends(get_db)):
    """
    Get comprehensive ML feedback statistics
    
    Provides insights into feedback quality, learning progress, and areas needing improvement.
    """
    try:
        service = MLFeedbackService(db)
        stats = service.get_feedback_stats()
        
        logger.info("Retrieved ML feedback statistics")
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving feedback statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


@router.get("/recent", response_model=List[MLFeedbackResponse])
async def get_recent_feedback(
    limit: int = Query(20, ge=1, le=100, description="Number of recent feedback entries"),
    feedback_type: Optional[str] = Query(None, description="Filter by feedback type"),
    db: Session = Depends(get_db)
):
    """
    Get recent feedback entries for monitoring and analysis
    """
    try:
        query = db.query(MLFeedback).order_by(desc(MLFeedback.created_at))
        
        if feedback_type:
            query = query.filter(MLFeedback.feedback_type == feedback_type)
        
        recent_feedback = query.limit(limit).all()
        
        return [MLFeedbackResponse.from_orm(feedback) for feedback in recent_feedback]
        
    except Exception as e:
        logger.error(f"Error retrieving recent feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recent feedback: {str(e)}"
        )


@router.post("/batch-update-patterns")
async def batch_update_patterns(db: Session = Depends(get_db)):
    """
    Manually trigger pattern learning update from accumulated feedback
    
    This endpoint forces a recalculation of learned patterns from all feedback data.
    Useful for testing or when patterns need to be refreshed.
    """
    try:
        service = MLFeedbackService(db)
        service._update_learned_patterns()
        
        # Get updated stats
        stats = service.get_feedback_stats()
        
        return {
            "message": "Pattern learning update completed",
            "patterns_learned": stats.patterns_learned,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update patterns: {str(e)}"
        )


@router.delete("/pattern/{merchant_pattern}")
async def delete_learned_pattern(
    merchant_pattern: str,
    db: Session = Depends(get_db)
):
    """
    Delete a learned pattern (for cleanup or correction)
    """
    try:
        # Mark feedback as not learned
        updated_count = db.query(MLFeedback).filter(
            MLFeedback.merchant_pattern == merchant_pattern
        ).update({
            'pattern_learned': False,
            'applied_at': None
        })
        
        # Remove from merchant knowledge base if it was auto-created
        db.query(MerchantKnowledgeBase).filter(
            and_(
                MerchantKnowledgeBase.normalized_name == merchant_pattern,
                MerchantKnowledgeBase.created_by == "feedback_learning"
            )
        ).delete()
        
        db.commit()
        
        return {
            "message": f"Deleted learned pattern for '{merchant_pattern}'",
            "feedback_entries_updated": updated_count
        }
        
    except Exception as e:
        logger.error(f"Error deleting pattern: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete pattern: {str(e)}"
        )


@router.get("/merchant-analysis/{merchant_pattern}")
async def analyze_merchant_feedback(
    merchant_pattern: str,
    db: Session = Depends(get_db)
):
    """
    Analyze feedback for a specific merchant pattern
    """
    try:
        feedback_entries = db.query(MLFeedback).filter(
            MLFeedback.merchant_pattern == merchant_pattern
        ).all()
        
        if not feedback_entries:
            raise HTTPException(
                status_code=404,
                detail=f"No feedback found for merchant pattern '{merchant_pattern}'"
            )
        
        # Analyze feedback patterns
        corrections = [f for f in feedback_entries if f.feedback_type == 'correction']
        acceptances = [f for f in feedback_entries if f.feedback_type == 'acceptance']
        
        tag_corrections = Counter([f.corrected_tag for f in corrections if f.corrected_tag])
        expense_type_corrections = Counter([f.corrected_expense_type for f in corrections if f.corrected_expense_type])
        
        avg_confidence_before = sum([f.confidence_before for f in corrections if f.confidence_before]) / len(corrections) if corrections else 0
        
        analysis = {
            "merchant_pattern": merchant_pattern,
            "total_feedback": len(feedback_entries),
            "corrections": len(corrections),
            "acceptances": len(acceptances),
            "most_common_tag_corrections": dict(tag_corrections.most_common(5)),
            "most_common_expense_type_corrections": dict(expense_type_corrections.most_common(3)),
            "average_confidence_before_correction": avg_confidence_before,
            "pattern_learned": any(f.pattern_learned for f in feedback_entries),
            "latest_feedback": max([f.created_at for f in feedback_entries]).isoformat() if feedback_entries else None
        }
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing merchant feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze merchant feedback: {str(e)}"
        )