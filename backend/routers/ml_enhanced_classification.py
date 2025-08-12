"""
ML Enhanced Classification Router
Integrates feedback learning with expense classification for improved accuracy

This router provides enhanced classification endpoints that:
1. Use feedback-learned patterns as primary source
2. Fall back to base classification with confidence adjustments
3. Provide multiple suggestions with confidence scores
4. Support batch classification with learning integration

Author: Claude Code - ML Backend Architect
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from models.database import get_db, Transaction
from models.schemas import MLTaggingResult, TransactionTagUpdate, TransactionExpenseTypeUpdate
from services.ml_feedback_learning import MLFeedbackLearningService
from services.expense_classification import ExpenseClassificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ml-classification", tags=["ML Enhanced Classification"])


class ClassificationRequest(BaseModel):
    """Request for transaction classification"""
    transaction_label: str = Field(description="Transaction label/description")
    amount: float = Field(default=0.0, description="Transaction amount")
    use_web_research: bool = Field(default=False, description="Enable web research for unknown merchants")
    include_alternatives: bool = Field(default=True, description="Include alternative suggestions")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum confidence threshold")


class BatchClassificationRequest(BaseModel):
    """Request for batch classification"""
    transactions: List[Dict[str, Any]] = Field(description="List of transactions to classify")
    use_feedback_learning: bool = Field(default=True, description="Use feedback learning patterns")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum confidence threshold")
    max_alternatives: int = Field(default=3, ge=1, le=10, description="Maximum alternative suggestions per transaction")


class ClassificationResponse(BaseModel):
    """Enhanced classification response"""
    suggested_tag: str = Field(description="Primary tag suggestion")
    expense_type: str = Field(description="Expense type classification")
    confidence: float = Field(description="Overall confidence score")
    explanation: str = Field(description="Human-readable explanation")
    source: str = Field(description="Source of classification (feedback/base/hybrid)")
    
    # Detailed confidence breakdown
    pattern_match_confidence: float = Field(default=0.0, description="Pattern matching confidence")
    web_research_confidence: float = Field(default=0.0, description="Web research confidence")
    user_feedback_confidence: float = Field(default=0.0, description="User feedback confidence")
    context_confidence: float = Field(default=0.0, description="Context analysis confidence")
    
    # Additional information
    merchant_category: Optional[str] = Field(None, description="Identified merchant category")
    merchant_name_clean: Optional[str] = Field(None, description="Cleaned merchant name")
    alternative_suggestions: List[Dict[str, Any]] = Field(default_factory=list, description="Alternative suggestions")
    contributing_factors: List[str] = Field(default_factory=list, description="Factors that influenced classification")
    keyword_matches: List[str] = Field(default_factory=list, description="Keywords that matched")
    
    # Processing metadata
    processing_time_ms: int = Field(description="Processing time in milliseconds")
    web_research_performed: bool = Field(default=False, description="Whether web research was performed")
    feedback_pattern_used: bool = Field(default=False, description="Whether feedback pattern was used")


class BatchClassificationResponse(BaseModel):
    """Response for batch classification"""
    results: List[ClassificationResponse] = Field(description="Classification results")
    summary: Dict[str, Any] = Field(description="Batch processing summary")
    processing_time_seconds: float = Field(description="Total processing time")
    

@router.post("/classify", response_model=ClassificationResponse)
async def classify_transaction(
    request: ClassificationRequest,
    db: Session = Depends(get_db)
):
    """
    Classify a single transaction with enhanced ML and feedback learning
    """
    start_time = datetime.now()
    
    try:
        # Initialize feedback-enhanced learning service
        ml_service = MLFeedbackLearningService(db)
        
        # Perform classification with feedback integration
        result = ml_service.classify_with_feedback(
            transaction_label=request.transaction_label,
            amount=request.amount,
            use_web_research=request.use_web_research
        )
        
        # Determine source and feedback usage
        source = "feedback" if "feedback" in result.primary_reason else "base"
        feedback_pattern_used = "feedback" in result.primary_reason
        
        # Get alternative suggestions if requested
        alternatives = []
        if request.include_alternatives:
            alt_suggestions = ml_service.get_feedback_enhanced_suggestions(
                request.transaction_label, 
                request.amount, 
                top_n=3
            )
            # Skip the primary suggestion in alternatives
            alternatives = [s for s in alt_suggestions[1:] if s['confidence'] >= request.confidence_threshold]
        
        # Build response
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        response = ClassificationResponse(
            suggested_tag=result.suggested_tag or "divers",
            expense_type=result.expense_type,
            confidence=result.confidence,
            explanation=result.tag_explanation or result.primary_reason,
            source=source,
            
            # Confidence breakdown
            pattern_match_confidence=result.confidence if "pattern" in result.primary_reason else 0.0,
            web_research_confidence=result.confidence if result.web_research_used else 0.0,
            user_feedback_confidence=result.confidence if feedback_pattern_used else 0.0,
            context_confidence=result.confidence * 0.3,  # Base context understanding
            
            # Additional information
            merchant_category=getattr(result.merchant_info, 'category', None) if result.merchant_info else None,
            merchant_name_clean=ml_service.normalize_merchant_name(request.transaction_label),
            alternative_suggestions=alternatives,
            contributing_factors=result.contributing_factors,
            keyword_matches=result.keyword_matches,
            
            # Processing metadata
            processing_time_ms=processing_time,
            web_research_performed=result.web_research_used,
            feedback_pattern_used=feedback_pattern_used
        )
        
        logger.info(f"Enhanced classification: {request.transaction_label[:50]} → {result.suggested_tag} ({result.confidence:.2f}) in {processing_time}ms")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in enhanced classification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification failed: {str(e)}"
        )


@router.post("/classify-batch", response_model=BatchClassificationResponse)
async def classify_transactions_batch(
    request: BatchClassificationRequest,
    db: Session = Depends(get_db)
):
    """
    Classify multiple transactions in batch with enhanced ML and feedback learning
    """
    start_time = datetime.now()
    
    try:
        # Initialize services
        ml_service = MLFeedbackLearningService(db) if request.use_feedback_learning else None
        base_service = ExpenseClassificationService()
        
        results = []
        processing_stats = {
            'total_processed': 0,
            'feedback_patterns_used': 0,
            'web_research_used': 0,
            'high_confidence_results': 0,
            'low_confidence_results': 0
        }
        
        for transaction_data in request.transactions:
            transaction_start = datetime.now()
            
            # Extract transaction info
            label = transaction_data.get('label', '')
            amount = float(transaction_data.get('amount', 0.0))
            use_web_research = transaction_data.get('use_web_research', False)
            
            # Classify with appropriate service
            if ml_service:
                result = ml_service.classify_with_feedback(label, amount, use_web_research)
                feedback_pattern_used = "feedback" in result.primary_reason
                source = "feedback" if feedback_pattern_used else "base"
            else:
                result = base_service.classify_expense_fast(
                    tag_name=label,
                    transaction_amount=amount,
                    transaction_description=label
                )
                feedback_pattern_used = False
                source = "base"
            
            # Skip low confidence results if threshold is set
            if result.confidence < request.confidence_threshold:
                processing_stats['low_confidence_results'] += 1
                continue
            
            # Get alternatives
            alternatives = []
            if ml_service and request.max_alternatives > 1:
                alt_suggestions = ml_service.get_feedback_enhanced_suggestions(
                    label, amount, top_n=request.max_alternatives
                )
                alternatives = [s for s in alt_suggestions[1:] if s['confidence'] >= request.confidence_threshold]
            
            # Create response
            processing_time = int((datetime.now() - transaction_start).total_seconds() * 1000)
            
            classification_response = ClassificationResponse(
                suggested_tag=result.suggested_tag or "divers",
                expense_type=result.expense_type,
                confidence=result.confidence,
                explanation=result.tag_explanation or result.primary_reason,
                source=source,
                
                pattern_match_confidence=result.confidence if "pattern" in result.primary_reason else 0.0,
                web_research_confidence=result.confidence if result.web_research_used else 0.0,
                user_feedback_confidence=result.confidence if feedback_pattern_used else 0.0,
                context_confidence=result.confidence * 0.3,
                
                merchant_name_clean=ml_service.normalize_merchant_name(label) if ml_service else label[:20],
                alternative_suggestions=alternatives,
                contributing_factors=result.contributing_factors,
                keyword_matches=result.keyword_matches,
                
                processing_time_ms=processing_time,
                web_research_performed=result.web_research_used,
                feedback_pattern_used=feedback_pattern_used
            )
            
            results.append(classification_response)
            
            # Update statistics
            processing_stats['total_processed'] += 1
            if feedback_pattern_used:
                processing_stats['feedback_patterns_used'] += 1
            if result.web_research_used:
                processing_stats['web_research_used'] += 1
            if result.confidence >= 0.8:
                processing_stats['high_confidence_results'] += 1
        
        total_processing_time = (datetime.now() - start_time).total_seconds()
        
        # Build summary
        summary = {
            **processing_stats,
            'average_confidence': sum(r.confidence for r in results) / len(results) if results else 0.0,
            'feedback_usage_rate': processing_stats['feedback_patterns_used'] / max(1, processing_stats['total_processed']),
            'high_confidence_rate': processing_stats['high_confidence_results'] / max(1, processing_stats['total_processed']),
            'transactions_below_threshold': processing_stats['low_confidence_results']
        }
        
        logger.info(f"Batch classification: {len(results)} transactions processed in {total_processing_time:.2f}s")
        
        return BatchClassificationResponse(
            results=results,
            summary=summary,
            processing_time_seconds=total_processing_time
        )
        
    except Exception as e:
        logger.error(f"Error in batch classification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch classification failed: {str(e)}"
        )


@router.post("/apply-classification/{transaction_id}")
async def apply_classification_to_transaction(
    transaction_id: int,
    apply_tag: bool = Query(True, description="Apply suggested tag"),
    apply_expense_type: bool = Query(True, description="Apply suggested expense type"),
    confidence_threshold: float = Query(0.6, description="Minimum confidence to apply"),
    db: Session = Depends(get_db)
):
    """
    Apply ML classification results directly to a transaction
    """
    try:
        # Get transaction
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise HTTPException(
                status_code=404,
                detail=f"Transaction {transaction_id} not found"
            )
        
        # Classify with feedback learning
        ml_service = MLFeedbackLearningService(db)
        result = ml_service.classify_with_feedback(
            transaction_label=transaction.label or "",
            amount=transaction.amount or 0.0,
            use_web_research=True
        )
        
        # Check confidence threshold
        if result.confidence < confidence_threshold:
            return {
                "message": f"Classification confidence ({result.confidence:.2f}) below threshold ({confidence_threshold})",
                "classification": {
                    "suggested_tag": result.suggested_tag,
                    "expense_type": result.expense_type,
                    "confidence": result.confidence,
                    "explanation": result.tag_explanation or result.primary_reason
                },
                "applied": False
            }
        
        # Apply changes
        changes_made = []
        
        if apply_tag and result.suggested_tag:
            # Add tag if not already present
            current_tags = set(tag.strip() for tag in (transaction.tags or "").split(",") if tag.strip())
            if result.suggested_tag not in current_tags:
                current_tags.add(result.suggested_tag)
                transaction.tags = ",".join(sorted(current_tags))
                changes_made.append(f"Added tag: {result.suggested_tag}")
        
        if apply_expense_type and result.expense_type:
            if transaction.expense_type != result.expense_type:
                old_type = transaction.expense_type
                transaction.expense_type = result.expense_type
                transaction.confidence_score = result.confidence
                changes_made.append(f"Changed expense type: {old_type} → {result.expense_type}")
        
        if changes_made:
            db.commit()
            db.refresh(transaction)
        
        return {
            "message": f"Classification applied successfully" if changes_made else "No changes needed",
            "classification": {
                "suggested_tag": result.suggested_tag,
                "expense_type": result.expense_type,
                "confidence": result.confidence,
                "explanation": result.tag_explanation or result.primary_reason
            },
            "changes_made": changes_made,
            "applied": len(changes_made) > 0,
            "feedback_pattern_used": "feedback" in result.primary_reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying classification to transaction {transaction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply classification: {str(e)}"
        )


@router.get("/feedback-stats")
async def get_feedback_learning_stats(db: Session = Depends(get_db)):
    """
    Get statistics about feedback learning system performance
    """
    try:
        ml_service = MLFeedbackLearningService(db)
        stats = ml_service.get_pattern_statistics()
        
        return {
            "feedback_patterns": stats,
            "system_status": "active" if stats['total_patterns'] > 0 else "learning",
            "recommendation": (
                "Feedback learning active with good pattern coverage" 
                if stats['total_patterns'] > 10 
                else "Continue providing feedback to improve accuracy"
            )
        }
        
    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feedback stats: {str(e)}"
        )


@router.post("/reload-patterns")
async def reload_feedback_patterns(db: Session = Depends(get_db)):
    """
    Reload feedback patterns from database (useful after manual feedback entry)
    """
    try:
        ml_service = MLFeedbackLearningService(db)
        ml_service.reload_patterns()
        
        stats = ml_service.get_pattern_statistics()
        
        return {
            "message": "Feedback patterns reloaded successfully",
            "patterns_loaded": stats['total_patterns'],
            "high_confidence_patterns": stats['high_confidence_patterns'],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error reloading patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload patterns: {str(e)}"
        )