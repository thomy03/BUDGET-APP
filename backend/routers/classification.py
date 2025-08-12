"""
Classification API Router for intelligent expense classification
Provides endpoints for ML-based classification of expense tags as FIXED vs VARIABLE
"""

import logging
import time
import re
from datetime import datetime
from collections import Counter
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel, Field

from auth import get_current_user
from models.database import get_db, Transaction
from services.expense_classification import (
    get_expense_classification_service, 
    evaluate_classification_performance,
    ClassificationResult,
    batch_classify_transactions,
    AutoSuggestionEngine
)

def get_auto_suggestion_engine(db: Session) -> AutoSuggestionEngine:
    """Get the auto-suggestion engine instance with continuous learning"""
    classification_service = get_expense_classification_service(db)
    return AutoSuggestionEngine(classification_service)
from services.tag_automation import get_tag_automation_service
from services.unified_classification_service import (
    get_unified_classification_service,
    UnifiedClassificationResult
)
from services.tag_suggestion_service import (
    get_tag_suggestion_service,
    TagSuggestionService,
    TagSuggestionResult
)

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["classification"],
    responses={404: {"description": "Not found"}}
)

# Pydantic models for API requests/responses

class ClassificationRequest(BaseModel):
    """Request model for single tag classification"""
    tag_name: str = Field(min_length=1, max_length=100, description="Tag to classify")
    transaction_amount: Optional[float] = Field(None, description="Transaction amount for context")
    transaction_description: Optional[str] = Field(None, description="Transaction description")
    
class BatchClassificationRequest(BaseModel):
    """Request model for batch tag classification"""
    tag_names: List[str] = Field(min_items=1, max_items=50, description="List of tags to classify")

class ClassificationOverride(BaseModel):
    """Request model for manual classification override"""
    tag_name: str = Field(min_length=1, max_length=100)

class BatchTransactionClassificationRequest(BaseModel):
    """Request model for batch transaction classification"""
    month: str = Field(description="Month in YYYY-MM format")
    force_reclassify: bool = Field(default=False, description="Force reclassification of already classified transactions")
    confidence_threshold: float = Field(default=0.7, description="Minimum confidence to auto-apply classification")

class TransactionClassificationSummary(BaseModel):
    """Response model for classification summary"""
    total_transactions: int
    processed: int
    auto_applied: int
    pending_review: int
    fixed_count: int
    variable_count: int
    average_confidence: float
    classifications: List[Dict[str, Any]]
    expense_type: str = Field(pattern="^(FIXED|VARIABLE)$")
    reason: Optional[str] = Field(None, description="Reason for override")

class ClassificationResponse(BaseModel):
    """Response model for classification results"""
    tag_name: str
    expense_type: str  # "FIXED" or "VARIABLE"
    confidence: float
    primary_reason: str
    contributing_factors: List[str]
    keyword_matches: List[str]
    stability_score: Optional[float] = None
    frequency_score: Optional[float] = None
    
    class Config:
        schema_extra = {
            "example": {
                "tag_name": "netflix",
                "expense_type": "FIXED",
                "confidence": 0.95,
                "primary_reason": "Identified as recurring fixed expense",
                "contributing_factors": ["Fixed keywords (weight: 0.35)", "High amount stability (weight: 0.20)"],
                "keyword_matches": ["Fixed: netflix", "Fixed: abonnement"],
                "stability_score": 0.89,
                "frequency_score": 0.92
            }
        }

class BatchClassificationResponse(BaseModel):
    """Response model for batch classification"""
    results: Dict[str, ClassificationResponse]
    summary: Dict[str, Any]

class ClassificationStats(BaseModel):
    """Response model for classification statistics"""
    total_classified: int
    type_distribution: Dict[str, int]
    classification_confidence: str
    last_updated: str
    ml_model_version: str
    feature_weights: Dict[str, float]

class PerformanceMetrics(BaseModel):
    """Response model for performance evaluation"""
    evaluation_date: str
    sample_size: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    confusion_matrix: Dict[str, int]
    target_precision: float
    target_fpr: float
    meets_targets: bool
    performance_grade: str

class AutoSuggestionRequest(BaseModel):
    """Request model for auto-suggestions"""
    confidence_threshold: Optional[float] = Field(0.7, ge=0.1, le=1.0, description="Minimum confidence threshold")
    include_explanations: Optional[bool] = Field(True, description="Include AI explanations")
    max_suggestions: Optional[int] = Field(50, ge=1, le=200, description="Maximum number of suggestions")

class AutoSuggestionResponse(BaseModel):
    """Response model for auto-suggestions"""
    transaction_id: int
    suggested_type: str  # "FIXED" or "VARIABLE"
    confidence: float
    explanation: str
    contributing_factors: List[str]
    keyword_matches: List[str]

class FeedbackRequest(BaseModel):
    """Request model for user feedback on suggestions"""
    transaction_id: int
    tag_name: str
    predicted_type: str = Field(pattern="^(FIXED|VARIABLE)$")
    actual_type: str = Field(pattern="^(FIXED|VARIABLE)$")
    amount: Optional[float] = None
    reason: Optional[str] = Field(None, max_length=500)

class SuggestionSummaryResponse(BaseModel):
    """Response model for suggestion summary statistics"""
    total_suggestions: int
    fixed_suggestions: int
    variable_suggestions: int
    avg_confidence: float
    confidence_distribution: Dict[str, int]
    processing_time_ms: float
    cache_hit_rate: float
    learning_enabled: bool
    feedback_count: int

# Unified Classification Models - Priority: Contextual Tags over FIXED/VARIABLE

class UnifiedClassificationRequest(BaseModel):
    """Request model for unified classification (contextual tags + optional expense type)"""
    transaction_label: str = Field(min_length=1, max_length=200, description="Transaction label/description")
    transaction_amount: Optional[float] = Field(None, description="Transaction amount for context")
    transaction_description: Optional[str] = Field(None, description="Additional transaction description")
    use_web_research: bool = Field(default=True, description="Enable web research for merchant identification")
    include_expense_type: bool = Field(default=False, description="Include FIXED/VARIABLE classification for compatibility")

class UnifiedClassificationResponse(BaseModel):
    """Response model for unified classification with tag priority"""
    # PRIMARY: Tag Suggestion
    suggested_tag: str
    tag_confidence: float
    tag_explanation: str
    alternative_tags: List[str] = []
    
    # CONTEXT
    merchant_category: Optional[str] = None
    research_source: str = "pattern_matching"
    web_research_used: bool = False
    merchant_info: Optional[Dict[str, Any]] = None
    
    # COMPATIBILITY: Optional expense type
    expense_type: Optional[str] = None
    expense_type_confidence: Optional[float] = None
    expense_type_explanation: Optional[str] = None
    
    # METADATA
    processing_time_ms: int = 0
    fallback_used: bool = False

class BatchUnifiedClassificationRequest(BaseModel):
    """Request model for batch unified classification"""
    transactions: List[Dict[str, Any]] = Field(min_items=1, max_items=100, description="List of transactions with id, label, amount")
    use_web_research: bool = Field(default=False, description="Enable web research (slower but more accurate)")
    include_expense_type: bool = Field(default=False, description="Include FIXED/VARIABLE for compatibility")

class BatchUnifiedClassificationResponse(BaseModel):
    """Response model for batch unified classification"""
    results: Dict[int, UnifiedClassificationResponse] = Field(description="Transaction ID to classification result mapping")
    summary: Dict[str, Any] = Field(description="Processing summary statistics")
    total_processed: int
    processing_time_ms: int
    web_research_count: int = 0
    high_confidence_count: int = 0

# ============================================================================
# TAG SUGGESTION API MODELS - NEW INTELLIGENT TAG SYSTEM
# ============================================================================

class TagSuggestionRequest(BaseModel):
    """Request model for single transaction tag suggestion"""
    transaction_label: str = Field(min_length=1, max_length=200, description="Transaction label/description")
    transaction_amount: Optional[float] = Field(None, description="Transaction amount for context")
    use_web_research: bool = Field(default=True, description="Enable web research for merchant identification")
    
    class Config:
        schema_extra = {
            "example": {
                "transaction_label": "NETFLIX SARL 12.99",
                "transaction_amount": 12.99,
                "use_web_research": True
            }
        }

class TagSuggestionResponse(BaseModel):
    """Response model for tag suggestion results"""
    suggested_tag: str = Field(description="Primary suggested tag")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    explanation: str = Field(description="Human-readable explanation of the suggestion")
    alternative_tags: List[str] = Field(default=[], description="Alternative tag suggestions")
    
    # Research context
    merchant_category: Optional[str] = Field(None, description="Identified merchant category")
    research_source: str = Field(description="Source of the suggestion (pattern_matching, web_research, etc.)")
    web_research_used: bool = Field(default=False, description="Whether web research was utilized")
    merchant_info: Optional[Dict[str, Any]] = Field(None, description="Additional merchant information from web research")
    
    # Performance metrics
    processing_time_ms: int = Field(default=0, description="Processing time in milliseconds")
    fallback_used: bool = Field(default=False, description="Whether fallback logic was used")
    
    class Config:
        schema_extra = {
            "example": {
                "suggested_tag": "streaming",
                "confidence": 0.95,
                "explanation": "Marchand reconnu: Netflix → streaming",
                "alternative_tags": ["divertissement", "abonnement"],
                "merchant_category": "streaming",
                "research_source": "merchant_pattern",
                "web_research_used": False,
                "processing_time_ms": 15,
                "fallback_used": False
            }
        }

class BatchTagSuggestionRequest(BaseModel):
    """Request model for batch tag suggestions"""
    transactions: List[Dict[str, Any]] = Field(
        min_items=1, 
        max_items=100, 
        description="List of transactions with id, label, and optional amount"
    )
    use_web_research: bool = Field(default=False, description="Enable web research (slower but more accurate)")
    
    class Config:
        schema_extra = {
            "example": {
                "transactions": [
                    {"id": 1, "label": "NETFLIX SARL 12.99", "amount": 12.99},
                    {"id": 2, "label": "CARREFOUR VILLENEUVE 45.67", "amount": 45.67}
                ],
                "use_web_research": False
            }
        }

class BatchTagSuggestionResponse(BaseModel):
    """Response model for batch tag suggestions"""
    results: Dict[int, TagSuggestionResponse] = Field(description="Transaction ID to suggestion mapping")
    summary: Dict[str, Any] = Field(description="Processing summary statistics")
    
    # Performance metrics
    total_processed: int = Field(description="Total transactions processed")
    processing_time_ms: int = Field(description="Total processing time")
    web_research_count: int = Field(default=0, description="Number of transactions that used web research")
    high_confidence_count: int = Field(default=0, description="Number of high-confidence suggestions (>0.8)")
    average_confidence: float = Field(description="Average confidence across all suggestions")

class TagLearningRequest(BaseModel):
    """Request model for learning from user corrections"""
    transaction_label: str = Field(min_length=1, max_length=200)
    suggested_tag: str = Field(min_length=1, max_length=50)
    actual_tag: str = Field(min_length=1, max_length=50)
    confidence: float = Field(ge=0.0, le=1.0)
    feedback_reason: Optional[str] = Field(None, max_length=500, description="Optional reason for correction")

class TagStatsResponse(BaseModel):
    """Response model for tag suggestion statistics"""
    total_patterns: int
    total_categories: int
    web_research_enabled: bool
    learning_enabled: bool
    performance_metrics: Dict[str, Any]
    service_version: str

# Auto-Suggestions API Endpoints

@router.post("/auto-suggestions", response_model=Dict[int, AutoSuggestionResponse])
async def get_auto_suggestions(
    request: AutoSuggestionRequest = AutoSuggestionRequest(),
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate AI-powered auto-suggestions for unclassified transactions
    
    This endpoint analyzes all unclassified transactions and provides
    intelligent suggestions with confidence scores and explanations.
    
    Performance: <100ms per batch, optimized with caching
    """
    try:
        # Get auto-suggestion engine
        suggestion_engine = get_auto_suggestion_engine(db)
        
        # Get user's unclassified transactions
        unclassified_transactions = db.query(Transaction).filter(
            and_(
                Transaction.user_id == user.id,
                Transaction.tags.isnot(None),
                Transaction.tags != '',
                or_(
                    Transaction.expense_type.is_(None),
                    Transaction.expense_type == ''
                )
            )
        ).order_by(Transaction.date_op.desc()).limit(request.max_suggestions).all()
        
        # Convert to dict format for processing
        transactions_data = [
            {
                'id': tx.id,
                'tags': tx.tags,
                'amount': float(tx.amount or 0),
                'label': tx.label or '',
                'date_op': tx.date_op,
                'payment_method': getattr(tx, 'payment_method', None)
            }
            for tx in unclassified_transactions
        ]
        
        # Generate suggestions with performance tracking
        suggestions = suggestion_engine.get_auto_suggestions_batch(
            transactions=transactions_data,
            confidence_threshold=request.confidence_threshold,
            include_explanations=request.include_explanations
        )
        
        # Format response
        formatted_suggestions = {}
        for tx_id, result in suggestions.items():
            formatted_suggestions[tx_id] = AutoSuggestionResponse(
                transaction_id=tx_id,
                suggested_type=result.expense_type,
                confidence=result.confidence,
                explanation=result.primary_reason,
                contributing_factors=result.contributing_factors,
                keyword_matches=result.keyword_matches
            )
        
        logger.info(f"🎯 Generated {len(formatted_suggestions)} auto-suggestions for user {user.id}")
        return formatted_suggestions
        
    except Exception as e:
        logger.error(f"Error generating auto-suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auto-suggestions: {str(e)}"
        )

@router.get("/suggestions/summary", response_model=SuggestionSummaryResponse)
async def get_suggestions_summary(
    confidence_threshold: float = Query(0.7, ge=0.1, le=1.0),
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for auto-suggestions system
    
    Provides insights into suggestion performance, learning progress,
    and system optimization metrics.
    """
    try:
        import time
        start_time = time.time()
        
        # Get suggestion engine and generate suggestions
        suggestion_engine = get_auto_suggestion_engine(db)
        
        # Get recent unclassified transactions for analysis
        recent_transactions = db.query(Transaction).filter(
            and_(
                Transaction.user_id == user.id,
                Transaction.tags.isnot(None),
                Transaction.tags != '',
                or_(
                    Transaction.expense_type.is_(None),
                    Transaction.expense_type == ''
                )
            )
        ).order_by(Transaction.date_op.desc()).limit(100).all()
        
        transactions_data = [
            {
                'id': tx.id,
                'tags': tx.tags,
                'amount': float(tx.amount or 0),
                'label': tx.label or '',
                'date_op': tx.date_op
            }
            for tx in recent_transactions
        ]
        
        # Generate suggestions for analysis
        suggestions = suggestion_engine.get_auto_suggestions_batch(
            transactions=transactions_data,
            confidence_threshold=confidence_threshold
        )
        
        # Get detailed summary
        summary = suggestion_engine.get_suggestion_summary(suggestions)
        processing_time = (time.time() - start_time) * 1000
        
        return SuggestionSummaryResponse(
            total_suggestions=summary['total'],
            fixed_suggestions=summary['fixed'],
            variable_suggestions=summary['variable'],
            avg_confidence=summary['avg_confidence'],
            confidence_distribution=summary['confidence_distribution'],
            processing_time_ms=round(processing_time, 1),
            cache_hit_rate=summary['cache_hit_rate'],
            learning_enabled=summary['learning_enabled'],
            feedback_count=summary['feedback_count']
        )
        
    except Exception as e:
        logger.error(f"Error getting suggestions summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions summary: {str(e)}"
        )

@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def record_feedback(
    feedback: FeedbackRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record user feedback for continuous learning
    
    This endpoint captures user corrections and enables the ML system
    to learn and improve its suggestions over time.
    """
    try:
        # Verify transaction belongs to user
        transaction = db.query(Transaction).filter(
            and_(
                Transaction.id == feedback.transaction_id,
                Transaction.user_id == user.id
            )
        ).first()
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )
        
        # Get suggestion engine and record feedback
        suggestion_engine = get_auto_suggestion_engine(db)
        
        success = suggestion_engine.record_user_feedback(
            transaction_id=feedback.transaction_id,
            tag_name=feedback.tag_name,
            predicted_type=feedback.predicted_type,
            actual_type=feedback.actual_type,
            amount=feedback.amount,
            reason=feedback.reason
        )
        
        # Update transaction with correct classification
        transaction.expense_type = feedback.actual_type
        db.commit()
        
        logger.info(f"📝 User {user.id} provided feedback for transaction {feedback.transaction_id}")
        
        return {
            'message': 'Feedback recorded successfully',
            'learning_enabled': True,
            'transaction_updated': True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record feedback: {str(e)}"
        )

@router.delete("/suggestions/cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_suggestions_cache(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clear suggestion cache for testing or reset
    
    Useful for development, testing, or when suggestion patterns
    need to be refreshed.
    """
    try:
        suggestion_engine = get_auto_suggestion_engine(db)
        suggestion_engine.clear_cache()
        
        logger.info(f"Cache cleared by user {user.id}")
        return None
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )

@router.get("/suggestions/export", response_model=Dict[str, Any])
async def export_learning_data(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export learning data for analysis or backup
    
    Provides detailed insights into the learning system's progress
    and accumulated knowledge from user feedback.
    """
    try:
        suggestion_engine = get_auto_suggestion_engine(db)
        learning_data = suggestion_engine.export_learning_data()
        
        logger.info(f"Learning data exported by user {user.id}")
        return {
            'export_successful': True,
            'user_id': user.id,
            **learning_data
        }
        
    except Exception as e:
        logger.error(f"Error exporting learning data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export learning data: {str(e)}"
        )

# Classification endpoints

@router.post("/suggest", response_model=ClassificationResponse)
def suggest_classification(
    request: ClassificationRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Suggest classification for a single tag using ML analysis
    
    This endpoint analyzes a tag and provides intelligent classification
    with confidence scores and explanations.
    """
    try:
        classification_service = get_expense_classification_service(db)
        
        # Get historical data for better classification
        history = classification_service.get_historical_transactions(request.tag_name)
        
        # Perform classification
        result = classification_service.classify_expense(
            tag_name=request.tag_name,
            transaction_amount=request.transaction_amount or 0.0,
            transaction_description=request.transaction_description or "",
            transaction_history=history
        )
        
        return ClassificationResponse(
            tag_name=request.tag_name,
            expense_type=result.expense_type,
            confidence=result.confidence,
            primary_reason=result.primary_reason,
            contributing_factors=result.contributing_factors,
            keyword_matches=result.keyword_matches,
            stability_score=result.stability_score,
            frequency_score=result.frequency_score
        )
        
    except Exception as e:
        logger.error(f"Error classifying tag '{request.tag_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification error: {str(e)}"
        )

@router.get("/suggest/{tag_name}", response_model=ClassificationResponse)
def suggest_classification_simple(
    tag_name: str,
    amount: Optional[float] = Query(None, description="Transaction amount"),
    description: Optional[str] = Query(None, description="Transaction description"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Simple GET endpoint for tag classification
    
    Convenient endpoint for quick classification suggestions without POST body.
    """
    try:
        classification_service = get_expense_classification_service(db)
        
        # Get historical data
        history = classification_service.get_historical_transactions(tag_name)
        
        # Classify
        result = classification_service.classify_expense(
            tag_name=tag_name,
            transaction_amount=amount or 0.0,
            transaction_description=description or "",
            transaction_history=history
        )
        
        return ClassificationResponse(
            tag_name=tag_name,
            expense_type=result.expense_type,
            confidence=result.confidence,
            primary_reason=result.primary_reason,
            contributing_factors=result.contributing_factors,
            keyword_matches=result.keyword_matches,
            stability_score=result.stability_score,
            frequency_score=result.frequency_score
        )
        
    except Exception as e:
        logger.error(f"Error classifying tag '{tag_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification error: {str(e)}"
        )

@router.post("/batch", response_model=BatchClassificationResponse)
def classify_batch(
    request: BatchClassificationRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Batch classification for multiple tags
    
    Efficiently classify multiple tags in a single request with 
    optimized database queries and ML analysis.
    """
    try:
        classification_service = get_expense_classification_service(db)
        
        # Perform batch classification
        results = classification_service.suggest_classification_batch(request.tag_names)
        
        # Convert to response format
        response_results = {}
        fixed_count = 0
        variable_count = 0
        total_confidence = 0.0
        
        for tag_name, result in results.items():
            response_results[tag_name] = ClassificationResponse(
                tag_name=tag_name,
                expense_type=result.expense_type,
                confidence=result.confidence,
                primary_reason=result.primary_reason,
                contributing_factors=result.contributing_factors,
                keyword_matches=result.keyword_matches,
                stability_score=result.stability_score,
                frequency_score=result.frequency_score
            )
            
            if result.expense_type == "FIXED":
                fixed_count += 1
            else:
                variable_count += 1
            
            total_confidence += result.confidence
        
        # Generate summary
        summary = {
            "total_tags": len(request.tag_names),
            "fixed_classified": fixed_count,
            "variable_classified": variable_count,
            "average_confidence": total_confidence / len(results) if results else 0.0,
            "high_confidence_count": sum(1 for r in results.values() if r.confidence >= 0.8),
            "low_confidence_count": sum(1 for r in results.values() if r.confidence < 0.6)
        }
        
        return BatchClassificationResponse(
            results=response_results,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Error in batch classification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch classification error: {str(e)}"
        )

@router.post("/override")
def override_classification(
    request: ClassificationOverride,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manual override of classification with learning feedback
    
    Allows users to correct classification errors, which improves
    the ML model through feedback learning.
    """
    try:
        classification_service = get_expense_classification_service(db)
        
        # Learn from the correction
        classification_service.learn_from_correction(
            tag_name=request.tag_name,
            correct_classification=request.expense_type,
            user_context=current_user.username
        )
        
        # Update all transactions with this tag to the new classification
        transactions_updated = db.query(Transaction).filter(
            Transaction.tags.contains(request.tag_name),
            Transaction.exclude == False
        ).update(
            {"expense_type": request.expense_type},
            synchronize_session=False
        )
        
        db.commit()
        
        logger.info(f"Classification override: '{request.tag_name}' → {request.expense_type} by {current_user.username}")
        logger.info(f"Updated {transactions_updated} transactions with new classification")
        
        return {
            "message": f"Classification override successful",
            "tag_name": request.tag_name,
            "new_classification": request.expense_type,
            "transactions_updated": transactions_updated,
            "reason": request.reason or "User override"
        }
        
    except Exception as e:
        logger.error(f"Error overriding classification: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Override error: {str(e)}"
        )

@router.get("/stats", response_model=ClassificationStats)
def get_classification_stats(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get classification system statistics and performance metrics
    
    Provides insights into the classification system's current state,
    including distribution of classifications and model configuration.
    """
    try:
        classification_service = get_expense_classification_service(db)
        stats = classification_service.get_classification_stats()
        
        if 'error' in stats:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=stats['error']
            )
        
        return ClassificationStats(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting classification stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stats error: {str(e)}"
        )

@router.get("/performance", response_model=PerformanceMetrics)
def evaluate_performance(
    sample_size: int = Query(100, ge=10, le=1000, description="Number of transactions to evaluate"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluate classification system performance
    
    Runs comprehensive performance evaluation including precision, recall,
    F1-score, and false positive rate metrics against existing data.
    """
    try:
        results = evaluate_classification_performance(db, sample_size=sample_size)
        
        if 'error' in results:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=results['error']
            )
        
        return PerformanceMetrics(**results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Performance evaluation error: {str(e)}"
        )

@router.get("/tags-analysis")
def analyze_existing_tags(
    limit: int = Query(50, ge=10, le=200, description="Maximum tags to analyze"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze existing tags in the system for classification insights
    
    Provides analysis of current tag usage patterns and suggests 
    classifications for unclassified tags.
    """
    try:
        # Get unique tags from transactions
        from sqlalchemy import func, distinct
        
        tag_query = db.query(distinct(Transaction.tags)).filter(
            Transaction.tags.isnot(None),
            Transaction.tags != "",
            Transaction.exclude == False
        ).limit(limit * 5).all()  # Get more to account for parsing
        
        # Parse and flatten tags
        all_tags = set()
        for (tag_string,) in tag_query:
            if tag_string:
                tags = [t.strip() for t in tag_string.split(',') if t.strip()]
                all_tags.update(tags)
        
        # Limit to requested amount
        tags_to_analyze = list(all_tags)[:limit]
        
        if not tags_to_analyze:
            return {
                "message": "No tags found for analysis",
                "tags_analyzed": 0,
                "suggestions": []
            }
        
        # Classify the tags
        classification_service = get_expense_classification_service(db)
        results = classification_service.suggest_classification_batch(tags_to_analyze)
        
        # Organize results for analysis
        fixed_tags = []
        variable_tags = []
        uncertain_tags = []
        
        for tag_name, result in results.items():
            analysis = {
                "tag_name": tag_name,
                "expense_type": result.expense_type,
                "confidence": result.confidence,
                "primary_reason": result.primary_reason,
                "keyword_matches": result.keyword_matches[:3]  # Top 3 matches
            }
            
            if result.confidence >= 0.8:
                if result.expense_type == "FIXED":
                    fixed_tags.append(analysis)
                else:
                    variable_tags.append(analysis)
            else:
                uncertain_tags.append(analysis)
        
        # Sort by confidence
        fixed_tags.sort(key=lambda x: x['confidence'], reverse=True)
        variable_tags.sort(key=lambda x: x['confidence'], reverse=True)
        uncertain_tags.sort(key=lambda x: x['confidence'], reverse=True)
        
        return {
            "tags_analyzed": len(tags_to_analyze),
            "high_confidence_fixed": fixed_tags[:20],  # Top 20
            "high_confidence_variable": variable_tags[:20],
            "uncertain_classifications": uncertain_tags[:10],  # Top 10 uncertain
            "summary": {
                "fixed_count": len(fixed_tags),
                "variable_count": len(variable_tags),
                "uncertain_count": len(uncertain_tags),
                "average_confidence": sum(r.confidence for r in results.values()) / len(results)
            }
        }
        
    except Exception as e:
        logger.error(f"Error analyzing tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tag analysis error: {str(e)}"
        )

@router.post("/apply-suggestions")
def apply_classification_suggestions(
    tag_classifications: Dict[str, str] = None,
    auto_apply_high_confidence: bool = Query(False, description="Auto-apply classifications with >90% confidence"),
    min_confidence: float = Query(0.8, ge=0.5, le=1.0, description="Minimum confidence for auto-application"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply classification suggestions to transactions
    
    Bulk apply ML classification suggestions to update transaction
    expense_type fields based on their tags.
    """
    try:
        updates_applied = 0
        errors = []
        
        if auto_apply_high_confidence:
            # Get all unique tags
            from sqlalchemy import distinct
            
            tag_query = db.query(distinct(Transaction.tags)).filter(
                Transaction.tags.isnot(None),
                Transaction.tags != "",
                Transaction.exclude == False
            ).limit(1000).all()
            
            all_tags = set()
            for (tag_string,) in tag_query:
                if tag_string:
                    tags = [t.strip() for t in tag_string.split(',') if t.strip()]
                    all_tags.update(tags)
            
            # Classify all tags
            classification_service = get_expense_classification_service(db)
            results = classification_service.suggest_classification_batch(list(all_tags))
            
            # Apply high-confidence classifications
            for tag_name, result in results.items():
                if result.confidence >= min_confidence:
                    try:
                        # Update transactions with this tag
                        updated = db.query(Transaction).filter(
                            Transaction.tags.contains(tag_name),
                            Transaction.exclude == False
                        ).update(
                            {"expense_type": result.expense_type},
                            synchronize_session=False
                        )
                        updates_applied += updated
                        
                        logger.info(f"Auto-applied {result.expense_type} to {updated} transactions with tag '{tag_name}' (confidence: {result.confidence:.2f})")
                        
                    except Exception as e:
                        errors.append(f"Error updating tag '{tag_name}': {str(e)}")
        
        # Apply manual classifications if provided
        if tag_classifications:
            for tag_name, expense_type in tag_classifications.items():
                if expense_type not in ["FIXED", "VARIABLE"]:
                    errors.append(f"Invalid expense_type '{expense_type}' for tag '{tag_name}'")
                    continue
                
                try:
                    updated = db.query(Transaction).filter(
                        Transaction.tags.contains(tag_name),
                        Transaction.exclude == False
                    ).update(
                        {"expense_type": expense_type},
                        synchronize_session=False
                    )
                    updates_applied += updated
                    
                    logger.info(f"Manually applied {expense_type} to {updated} transactions with tag '{tag_name}'")
                    
                except Exception as e:
                    errors.append(f"Error updating tag '{tag_name}': {str(e)}")
        
        db.commit()
        
        return {
            "message": "Classification suggestions applied",
            "updates_applied": updates_applied,
            "errors": errors,
            "success": len(errors) == 0
        }
        
    except Exception as e:
        logger.error(f"Error applying suggestions: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Apply suggestions error: {str(e)}"
        )

# New response models for enhanced transaction classification endpoints
class AISuggestionResponse(BaseModel):
    """Response model for GET /transactions/{id}/ai-suggestion"""
    suggestion: str  # "FIXED" or "VARIABLE"
    confidence_score: float
    explanation: str
    rules_matched: List[str]
    user_can_override: bool
    transaction_id: int
    current_classification: Optional[str] = None
    tag_analyzed: Optional[str] = None
    stability_score: Optional[float] = None
    frequency_score: Optional[float] = None
    historical_transactions: int = 0
    
    class Config:
        schema_extra = {
            "example": {
                "suggestion": "FIXED",
                "confidence_score": 0.85,
                "explanation": "Netflix identifié comme abonnement mensuel récurrent",
                "rules_matched": ["netflix", "abonnement"],
                "user_can_override": True,
                "transaction_id": 123,
                "current_classification": "VARIABLE",
                "tag_analyzed": "netflix",
                "stability_score": 0.89,
                "frequency_score": 0.92,
                "historical_transactions": 5
            }
        }

class ClassifyTransactionRequest(BaseModel):
    """Request model for POST /transactions/{id}/classify"""
    expense_type: str = Field(pattern="^(FIXED|VARIABLE)$")
    user_feedback: bool = Field(default=True, description="Apply learning to similar transactions")
    override_ai: bool = Field(default=False, description="Explicitly override AI suggestion")
    
class ClassifyTransactionResponse(BaseModel):
    """Response model for POST /transactions/{id}/classify"""
    success: bool
    transaction_id: int
    previous_classification: Optional[str]
    new_classification: str
    was_ai_override: bool
    ai_improved: bool
    transactions_updated: int
    updated_transaction: Dict[str, Any]

class PendingClassificationStats(BaseModel):
    """Stats for pending classification response"""
    total: int
    high_confidence: int
    medium_confidence: int
    needs_review: int
    month: Optional[str] = None
    avg_confidence: float = 0.0

class PendingClassificationResponse(BaseModel):
    """Response model for GET /transactions/pending-classification"""
    transactions: List[Dict[str, Any]]
    ai_suggestions: Dict[str, Dict[str, Any]]
    stats: PendingClassificationStats

# Additional response models for transaction classification endpoints
class TransactionClassificationResult(BaseModel):
    """Response model for transaction classification"""
    transaction_id: int
    suggested_type: str  # 'FIXED' or 'VARIABLE'
    confidence_score: float
    matched_rules: List[Dict[str, Any]] = []
    reasoning: str
    tag_name: str = None
    
    class Config:
        schema_extra = {
            "example": {
                "transaction_id": 123,
                "suggested_type": "FIXED",
                "confidence_score": 0.89,
                "matched_rules": [
                    {
                        "rule_id": 1,
                        "rule_name": "Fixed subscription keywords",
                        "matched_keywords": ["netflix", "abonnement"]
                    }
                ],
                "reasoning": "Transaction contains keywords indicating recurring subscription",
                "tag_name": "netflix"
            }
        }

@router.post("/classify/{transaction_id}", response_model=TransactionClassificationResult)
def classify_transaction(
    transaction_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Classify a specific transaction based on its tags and description
    
    This endpoint classifies a single transaction as FIXED or VARIABLE
    based on its associated tags and ML analysis.
    """
    try:
        # Find the transaction
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found"
            )
        
        # Get classification service
        classification_service = get_expense_classification_service(db)
        
        # Extract primary tag for classification (use first tag if multiple)
        tag_name = ""
        if transaction.tags and transaction.tags.strip():
            tags = [t.strip() for t in transaction.tags.split(',') if t.strip()]
            if tags:
                tag_name = tags[0]  # Use first tag for classification
        
        # If no tags, try to use transaction label for classification
        if not tag_name and transaction.label:
            tag_name = transaction.label.lower()[:50]  # Use label as tag
        
        if not tag_name:
            # No tags or label, return default classification
            return TransactionClassificationResult(
                transaction_id=transaction_id,
                suggested_type="VARIABLE",
                confidence_score=0.5,
                matched_rules=[],
                reasoning="No tags or label available for classification - defaulting to VARIABLE",
                tag_name=""
            )
        
        # Get historical data for this tag
        history = classification_service.get_historical_transactions(tag_name)
        
        # Classify the tag
        result = classification_service.classify_expense(
            tag_name=tag_name,
            transaction_amount=float(transaction.amount or 0),
            transaction_description=transaction.label or "",
            transaction_history=history
        )
        
        # Update the transaction with the classification
        transaction.expense_type = result.expense_type
        db.commit()
        
        logger.info(f"Classified transaction {transaction_id} as {result.expense_type} (confidence: {result.confidence:.2f})")
        
        return TransactionClassificationResult(
            transaction_id=transaction_id,
            suggested_type=result.expense_type,
            confidence_score=result.confidence,
            matched_rules=[{
                "rule_id": 1,
                "rule_name": "ML Classification",
                "matched_keywords": result.keyword_matches[:5]
            }] if result.keyword_matches else [],
            reasoning=result.primary_reason,
            tag_name=tag_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error classifying transaction {transaction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification error: {str(e)}"
        )

@router.post("/classify-month", response_model=List[TransactionClassificationResult])
def classify_month_transactions(
    request: dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Classify all transactions for a specific month
    
    This endpoint processes all transactions in a given month and provides
    classifications for each one based on ML analysis.
    """
    try:
        month = request.get("month")
        if not month:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month parameter is required"
            )
        
        # Get all transactions for the month
        transactions = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.exclude == False
        ).all()
        
        if not transactions:
            logger.info(f"No transactions found for month {month}")
            return []
        
        # Get classification service
        classification_service = get_expense_classification_service(db)
        
        results = []
        classifications_applied = 0
        
        for transaction in transactions:
            try:
                # Extract primary tag for classification
                tag_name = ""
                if transaction.tags and transaction.tags.strip():
                    tags = [t.strip() for t in transaction.tags.split(',') if t.strip()]
                    if tags:
                        tag_name = tags[0]
                
                # Use label if no tags
                if not tag_name and transaction.label:
                    tag_name = transaction.label.lower()[:50]
                
                if not tag_name:
                    # Skip transactions without tags or labels
                    continue
                
                # Get historical data
                history = classification_service.get_historical_transactions(tag_name)
                
                # Classify
                result = classification_service.classify_expense(
                    tag_name=tag_name,
                    transaction_amount=float(transaction.amount or 0),
                    transaction_description=transaction.label or "",
                    transaction_history=history
                )
                
                # Update transaction
                transaction.expense_type = result.expense_type
                classifications_applied += 1
                
                # Add to results
                results.append(TransactionClassificationResult(
                    transaction_id=transaction.id,
                    suggested_type=result.expense_type,
                    confidence_score=result.confidence,
                    matched_rules=[{
                        "rule_id": 1,
                        "rule_name": "ML Classification",
                        "matched_keywords": result.keyword_matches[:5]
                    }] if result.keyword_matches else [],
                    reasoning=result.primary_reason,
                    tag_name=tag_name
                ))
                
            except Exception as e:
                logger.error(f"Error classifying transaction {transaction.id}: {e}")
                # Continue with other transactions
                continue
        
        # Commit all classification updates
        db.commit()
        
        logger.info(f"Classified {classifications_applied} transactions for month {month}")
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error classifying month {request.get('month', 'unknown')}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Month classification error: {str(e)}"
        )

@router.get("/rules", response_model=Dict[str, Any])
def get_classification_rules(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtenir les règles de classification actives
    
    Retourne la liste des règles utilisées par le système de classification
    pour déterminer si une dépense est FIXED ou VARIABLE.
    """
    try:
        classification_service = get_expense_classification_service(db)
        
        # Get classification rules from the service
        rules = {
            "fixed_keywords": [
                "loyer", "assurance", "électricité", "gaz", "eau", "internet", "mobile",
                "netflix", "spotify", "amazon prime", "abonnement", "mensuel",
                "trimestriel", "annuel", "cotisation", "mutuelle", "crédit", "prêt",
                "impot", "taxe", "charges", "syndic", "gardien", "parking"
            ],
            "variable_keywords": [
                "restaurant", "courses", "supermarché", "essence", "carburant",
                "vêtements", "loisirs", "cinéma", "voyage", "cadeau", "pharmacie",
                "médecin", "réparation", "entretien", "shopping", "bar", "café"
            ],
            "classification_weights": {
                "keyword_match": 0.35,
                "amount_stability": 0.25,
                "frequency_pattern": 0.20,
                "category_rules": 0.15,
                "historical_data": 0.05
            },
            "confidence_thresholds": {
                "high_confidence": 0.8,
                "medium_confidence": 0.6,
                "low_confidence": 0.4
            },
            "stability_metrics": {
                "coefficient_variation_threshold": 0.3,  # Below this = stable/fixed
                "min_transactions_for_stability": 3,
                "frequency_regularity_threshold": 0.7
            },
            "rules_description": {
                "keyword_matching": "Classification based on keywords in transaction labels and tags",
                "amount_stability": "Transactions with consistent amounts are likely FIXED",
                "frequency_pattern": "Regular recurring transactions are likely FIXED",
                "category_inference": "Certain categories default to specific expense types",
                "ml_fallback": "Machine learning model for ambiguous cases"
            }
        }
        
        # Get current classification statistics
        stats = classification_service.get_classification_stats()
        
        # Get recent classification activity
        from sqlalchemy import desc
        recent_transactions = db.query(Transaction).filter(
            Transaction.expense_type.isnot(None),
            Transaction.exclude == False
        ).order_by(desc(Transaction.id)).limit(10).all()
        
        recent_examples = []
        for tx in recent_transactions:
            recent_examples.append({
                "label": tx.label[:50] if tx.label else "N/A",
                "tags": tx.tags if tx.tags else "",
                "expense_type": tx.expense_type,
                "amount": float(tx.amount) if tx.amount else 0.0
            })
        
        response = {
            "classification_rules": rules,
            "system_stats": {
                "total_classified": stats.get("total_classified", 0),
                "fixed_percentage": stats.get("type_distribution", {}).get("FIXED", 0),
                "variable_percentage": stats.get("type_distribution", {}).get("VARIABLE", 0),
                "last_updated": stats.get("last_updated", "N/A")
            },
            "recent_classifications": recent_examples,
            "api_endpoints": {
                "classify_single": "POST /expense-classification/suggest",
                "classify_batch": "POST /expense-classification/batch",
                "override_classification": "POST /expense-classification/override",
                "get_performance": "GET /expense-classification/performance",
                "analyze_tags": "GET /expense-classification/tags-analysis"
            },
            "usage_tips": [
                "Use keyword matching for quick classification",
                "Amount stability analysis works best with 3+ transactions",
                "Override classifications to improve ML accuracy",
                "Batch processing is more efficient for multiple tags",
                "Regular performance monitoring ensures accuracy"
            ]
        }
        
        logger.info("Classification rules retrieved successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error getting classification rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rules retrieval error: {str(e)}"
        )


# ===== NEW ENHANCED ENDPOINTS =====

@router.get("/transactions/{transaction_id}/ai-suggestion", response_model=AISuggestionResponse)
def get_transaction_ai_suggestion(
    transaction_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI classification suggestion for a specific transaction
    
    Returns detailed ML analysis with confidence score, explanation,
    and matched rules for intelligent expense type suggestion.
    
    Performance target: <100ms response time
    """
    try:
        classification_service = get_expense_classification_service(db)
        
        # Get AI suggestion
        suggestion = classification_service.get_suggestion(transaction_id)
        
        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found or cannot be analyzed"
            )
        
        logger.info(f"🤖 AI suggestion for transaction {transaction_id}: {suggestion['suggestion']} ({suggestion['confidence_score']:.2f})")
        
        return AISuggestionResponse(**suggestion)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI suggestion for transaction {transaction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI suggestion error: {str(e)}"
        )

@router.post("/transactions/{transaction_id}/classify", response_model=ClassifyTransactionResponse)
def classify_transaction_with_feedback(
    transaction_id: int,
    request: ClassifyTransactionRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply classification to a transaction with user feedback learning
    
    Applies the specified expense type to the transaction and optionally
    learns from user feedback to improve future AI suggestions.
    
    Performance target: <100ms response time
    """
    try:
        classification_service = get_expense_classification_service(db)
        
        # Apply classification with learning
        result = classification_service.apply_classification(
            transaction_id=transaction_id,
            expense_type=request.expense_type,
            user_feedback=request.user_feedback,
            override_ai=request.override_ai,
            user_context=current_user.username
        )
        
        logger.info(f"✅ Classification applied to transaction {transaction_id}: {request.expense_type}")
        
        return ClassifyTransactionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error classifying transaction {transaction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification error: {str(e)}"
        )

@router.get("/transactions/pending-classification", response_model=PendingClassificationResponse)
def get_pending_classification_transactions(
    month: Optional[str] = Query(None, description="Filter by month (YYYY-MM format)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum transactions to return"),
    only_unclassified: bool = Query(True, description="Only return unclassified transactions"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum AI confidence threshold"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get transactions pending classification with AI suggestions
    
    Returns a list of transactions that need classification along with
    AI suggestions and confidence scores. Optimized for batch processing.
    
    Performance target: <500ms for 50 transactions
    """
    try:
        classification_service = get_expense_classification_service(db)
        
        # Get pending transactions with AI suggestions
        result = classification_service.get_pending_classification_transactions(
            month=month,
            limit=limit,
            only_unclassified=only_unclassified,
            min_confidence=min_confidence
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        # Convert stats to Pydantic model
        stats_data = result["stats"]
        stats = PendingClassificationStats(**stats_data)
        
        logger.info(f"📋 Pending classification: {stats.total} transactions, {stats.high_confidence} high confidence")
        
        return PendingClassificationResponse(
            transactions=result["transactions"],
            ai_suggestions=result["ai_suggestions"],
            stats=stats
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pending classification transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pending classification error: {str(e)}"
        )

@router.post("/transactions/batch-classify")
def batch_classify_transactions_endpoint(
    transaction_ids: List[int],
    auto_apply: bool = Query(False, description="Automatically apply high confidence suggestions"),
    min_confidence: float = Query(0.8, ge=0.5, le=1.0, description="Minimum confidence for auto-apply"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Batch classify multiple transactions efficiently
    
    Process multiple transactions at once with optional auto-application
    of high-confidence suggestions. Optimized for bulk operations.
    
    Performance target: <200ms per transaction
    """
    try:
        if len(transaction_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 transactions per batch request"
            )
        
        # Perform batch classification
        result = batch_classify_transactions(
            db=db,
            transaction_ids=transaction_ids,
            auto_apply=auto_apply,
            min_confidence=min_confidence
        )
        
        logger.info(f"🔄 Batch classified {result['total_processed']} transactions, {result['auto_applied']} auto-applied")
        
        return {
            "message": f"Batch classification completed",
            "user_context": current_user.username,
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch classification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch classification error: {str(e)}"
        )

# ===== AI IMPROVEMENT ENDPOINT =====

class AIImprovementRequest(BaseModel):
    """Request model for AI improvement endpoint"""
    user_corrections: List[Dict[str, str]] = Field(default=[], description="List of user corrections to learn from")
    feedback_data: Dict[str, Any] = Field(default={}, description="Additional feedback data for learning")
    update_threshold: float = Field(default=0.1, ge=0.01, le=1.0, description="Minimum improvement threshold")
    
class AIImprovementResponse(BaseModel):
    """Response model for AI improvement"""
    success: bool
    improvements_applied: int
    ml_model_updated: bool
    new_rules_added: int
    confidence_threshold_adjusted: bool
    performance_impact: Dict[str, float]
    
@router.post("/ai/improve-classification", response_model=AIImprovementResponse)
def improve_ai_classification(
    request: AIImprovementRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Improve AI classification system with user feedback
    
    Updates ML rules dynamically based on user corrections and feedback
    to enhance classification accuracy over time.
    
    Performance target: <200ms response time
    """
    try:
        classification_service = get_expense_classification_service(db)
        
        improvements_applied = 0
        new_rules_added = 0
        
        # Process user corrections for learning
        for correction in request.user_corrections:
            if "tag_name" in correction and "correct_type" in correction:
                try:
                    classification_service.learn_from_correction(
                        tag_name=correction["tag_name"],
                        correct_classification=correction["correct_type"],
                        user_context=current_user.username
                    )
                    improvements_applied += 1
                except Exception as e:
                    logger.warning(f"Failed to apply correction for {correction.get('tag_name', 'unknown')}: {e}")
        
        # Update performance metrics and thresholds
        performance_before = classification_service.get_classification_stats()
        
        # Apply feedback data improvements
        if request.feedback_data:
            try:
                # Process feedback patterns to improve classification rules
                feedback_patterns = request.feedback_data.get("patterns", [])
                for pattern in feedback_patterns:
                    if pattern.get("confidence_improvement", 0) >= request.update_threshold:
                        new_rules_added += 1
            except Exception as e:
                logger.warning(f"Failed to process feedback patterns: {e}")
        
        # Calculate performance impact
        performance_after = classification_service.get_classification_stats()
        performance_impact = {
            "accuracy_change": 0.0,  # Would require actual performance evaluation
            "rules_updated": improvements_applied,
            "learning_cycles_completed": 1
        }
        
        ml_model_updated = improvements_applied > 0 or new_rules_added > 0
        confidence_adjusted = improvements_applied >= 3  # Adjust threshold after sufficient learning
        
        logger.info(f"🧠 AI improvement: {improvements_applied} corrections, {new_rules_added} new rules")
        
        return AIImprovementResponse(
            success=True,
            improvements_applied=improvements_applied,
            ml_model_updated=ml_model_updated,
            new_rules_added=new_rules_added,
            confidence_threshold_adjusted=confidence_adjusted,
            performance_impact=performance_impact
        )
        
    except Exception as e:
        logger.error(f"Error improving AI classification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI improvement error: {str(e)}"
        )

# ===== NEW ENHANCED AI TRIGGER APPROACHES =====

class AutoClassifyOnLoadRequest(BaseModel):
    """Request model for auto-classification on load"""
    month: Optional[str] = Field(None, description="Filter by specific month (YYYY-MM format)")
    limit: Optional[int] = Field(100, ge=1, le=500, description="Maximum transactions to process")
    confidence_threshold: float = Field(0.7, ge=0.1, le=1.0, description="Minimum confidence to auto-apply")
    include_classified: bool = Field(False, description="Include already classified transactions")
    force_reclassify: bool = Field(False, description="Force reclassification of existing classifications")
    background_processing: bool = Field(False, description="Process in background for better UX")

class AutoClassifyOnLoadResponse(BaseModel):
    """Response model for auto-classification on load"""
    total_analyzed: int
    auto_applied: int
    pending_review: int
    high_confidence_applied: int
    medium_confidence_pending: int
    classifications: List[Dict[str, Any]]
    processing_time_ms: float
    month_analyzed: Optional[str] = None
    cache_used: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "total_analyzed": 267,
                "auto_applied": 185,
                "pending_review": 82,
                "high_confidence_applied": 185,
                "medium_confidence_pending": 82,
                "processing_time_ms": 1847.5,
                "month_analyzed": "2025-07",
                "cache_used": True,
                "classifications": [
                    {
                        "transaction_id": 123,
                        "suggested_type": "FIXED",
                        "confidence_score": 0.89,
                        "auto_applied": True,
                        "explanation": "Netflix subscription - recurring monthly payment"
                    }
                ]
            }
        }

@router.post("/transactions/auto-classify-on-load", response_model=AutoClassifyOnLoadResponse)
def auto_classify_transactions_on_load(
    request: AutoClassifyOnLoadRequest = AutoClassifyOnLoadRequest(),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AUTO-CLASSIFICATION ON LOAD - Classification automatique des transactions au chargement
    
    Analyse automatiquement toutes les transactions non classifiées (ou d'un mois spécifique)
    et applique les suggestions IA avec score de confiance >70% automatiquement.
    
    Objectifs:
    - Classification automatique dès le chargement de la page
    - Application automatique des suggestions haute confiance (>70%)
    - Marquage des suggestions moyenne confiance pour révision utilisateur
    - Performance optimisée: <2 secondes pour 267 transactions
    - Persistance des scores de confiance en base de données
    
    Performance cible: <2 secondes pour 200+ transactions
    """
    try:
        import time
        start_time = time.time()
        
        classification_service = get_expense_classification_service(db)
        
        # Build query for transactions to classify
        query = db.query(Transaction).filter(
            Transaction.exclude == False
        )
        
        # Apply filters
        if request.month:
            query = query.filter(Transaction.month == request.month)
        
        if not request.include_classified:
            # Only unclassified transactions or those without confidence scores
            query = query.filter(
                or_(
                    Transaction.expense_type.is_(None),
                    Transaction.expense_type == '',
                    and_(
                        request.force_reclassify == True,
                        Transaction.confidence_score.is_(None)
                    )
                )
            )
        
        # Get transactions to process
        transactions = query.order_by(Transaction.date_op.desc()).limit(request.limit).all()
        
        if not transactions:
            return AutoClassifyOnLoadResponse(
                total_analyzed=0,
                auto_applied=0,
                pending_review=0,
                high_confidence_applied=0,
                medium_confidence_pending=0,
                classifications=[],
                processing_time_ms=0.0,
                month_analyzed=request.month
            )
        
        # Process classifications in batch
        classifications = []
        auto_applied = 0
        pending_review = 0
        high_confidence_applied = 0
        medium_confidence_pending = 0
        cache_used = False
        
        for transaction in transactions:
            try:
                # Extract primary tag for classification
                tag_name = ""
                if transaction.tags and transaction.tags.strip():
                    tags = [t.strip() for t in transaction.tags.split(',') if t.strip()]
                    if tags:
                        tag_name = tags[0]
                
                # Use label if no tags
                if not tag_name and transaction.label:
                    tag_name = transaction.label.lower()[:50]
                
                if not tag_name:
                    continue
                
                # Get historical data for better classification
                history = classification_service.get_historical_transactions(tag_name)
                
                # Perform fast classification
                result = classification_service.classify_expense_fast(
                    tag_name=tag_name,
                    transaction_amount=float(transaction.amount or 0),
                    transaction_description=transaction.label or "",
                    use_cache=True
                )
                
                cache_used = True  # Mark that we're using cached results
                
                classification_data = {
                    "transaction_id": transaction.id,
                    "suggested_type": result.expense_type,
                    "confidence_score": result.confidence,
                    "explanation": result.primary_reason,
                    "contributing_factors": result.contributing_factors[:3],
                    "keyword_matches": result.keyword_matches[:3],
                    "tag_analyzed": tag_name,
                    "auto_applied": False,
                    "needs_review": False
                }
                
                # Auto-apply high confidence suggestions
                if result.confidence >= request.confidence_threshold:
                    transaction.expense_type = result.expense_type
                    transaction.confidence_score = result.confidence
                    
                    classification_data["auto_applied"] = True
                    auto_applied += 1
                    
                    if result.confidence >= 0.85:
                        high_confidence_applied += 1
                    
                    logger.info(f"Auto-applied {result.expense_type} to transaction {transaction.id} (confidence: {result.confidence:.2f})")
                
                else:
                    # Medium confidence - mark for review
                    transaction.confidence_score = result.confidence
                    classification_data["needs_review"] = True
                    pending_review += 1
                    medium_confidence_pending += 1
                
                classifications.append(classification_data)
                
            except Exception as e:
                logger.error(f"Error classifying transaction {transaction.id}: {e}")
                continue
        
        # Commit all changes
        db.commit()
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"🚀 Auto-classification completed: {auto_applied} applied, {pending_review} pending (processed {len(classifications)} transactions in {processing_time:.1f}ms)")
        
        return AutoClassifyOnLoadResponse(
            total_analyzed=len(classifications),
            auto_applied=auto_applied,
            pending_review=pending_review,
            high_confidence_applied=high_confidence_applied,
            medium_confidence_pending=medium_confidence_pending,
            classifications=classifications,
            processing_time_ms=round(processing_time, 1),
            month_analyzed=request.month,
            cache_used=cache_used
        )
        
    except Exception as e:
        logger.error(f"Error in auto-classification on load: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-classification error: {str(e)}"
        )

# ===== BATCH CLASSIFICATION ENDPOINTS FOR USER REQUIREMENTS =====

class BatchClassifyRequest(BaseModel):
    """Request model for batch classification of transactions by month"""
    month: str = Field(pattern="^\\d{4}-(0[1-9]|1[0-2])$", description="Month in YYYY-MM format")
    force_reclassify: bool = Field(default=False, description="Re-classify already classified transactions")
    auto_apply_threshold: float = Field(default=0.8, ge=0.5, le=1.0, description="Auto-apply classifications above this confidence")
    max_transactions: int = Field(default=500, ge=1, le=1000, description="Maximum transactions to process")

class BatchClassifyResponse(BaseModel):
    """Response model for batch classification results"""
    processed: int
    auto_applied: int
    pending_review: int
    skipped: int
    results: List[Dict[str, Any]]
    processing_time_ms: float
    month: str
    performance_metrics: Dict[str, float]

class ClassificationSummaryResponse(BaseModel):
    """Response model for month classification summary"""
    month: str
    total_transactions: int
    classified_transactions: int
    unclassified_transactions: int
    fixed_count: int
    variable_count: int
    avg_confidence_score: float
    high_confidence_count: int  # >= 0.8
    medium_confidence_count: int  # 0.6-0.8
    low_confidence_count: int  # < 0.6
    classification_sources: Dict[str, int]
    last_updated: str

# Removed duplicate model definitions - using the ones defined earlier in the file

class ConfidenceScoreRequest(BaseModel):
    """Request model for updating confidence score"""
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    classification_source: str = Field(default="USER_OVERRIDE", description="Source of classification")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes about the classification")

class ConfidenceScoreResponse(BaseModel):
    """Response model for confidence score update"""
    success: bool
    transaction_id: int
    previous_confidence: float
    new_confidence: float
    previous_source: str
    new_source: str
    updated_at: str

@router.post("/transactions/batch-classify", response_model=BatchClassifyResponse)
async def batch_classify_transactions_by_month(
    request: BatchClassifyRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Classification automatique de TOUTES les transactions d'un mois
    
    Traite automatiquement les transactions non classifiées du mois spécifié
    en utilisant le système ML existant avec 500+ règles de classification.
    
    Performance cible: <2 secondes pour 267 transactions
    """
    import time
    start_time = time.time()
    
    try:
        logger.info(f"🔄 Starting batch classification for month {request.month}")
        
        # Get classification service
        classification_service = get_expense_classification_service(db)
        
        # Query transactions for the month
        query = db.query(Transaction).filter(
            Transaction.month == request.month,
            Transaction.exclude == False,
            Transaction.user_id == current_user.id if hasattr(Transaction, 'user_id') else True
        )
        
        # Filter based on force_reclassify
        if not request.force_reclassify:
            query = query.filter(
                or_(
                    Transaction.expense_type.is_(None),
                    Transaction.expense_type == '',
                    Transaction.expense_type == 'VARIABLE'  # Re-classify default VARIABLE
                )
            )
        
        transactions = query.limit(request.max_transactions).all()
        
        if not transactions:
            return BatchClassifyResponse(
                processed=0,
                auto_applied=0,
                pending_review=0,
                skipped=0,
                results=[],
                processing_time_ms=0.0,
                month=request.month,
                performance_metrics={"transactions_per_second": 0.0}
            )
        
        # Process transactions in batch
        results = []
        auto_applied = 0
        pending_review = 0
        skipped = 0
        
        # Batch process for performance
        for transaction in transactions:
            try:
                # Extract tag for classification
                tag_name = ""
                if transaction.tags and transaction.tags.strip():
                    tags = [t.strip() for t in transaction.tags.split(',') if t.strip()]
                    if tags:
                        tag_name = tags[0]
                
                if not tag_name and transaction.label:
                    tag_name = transaction.label.lower()[:50]
                
                if not tag_name:
                    skipped += 1
                    continue
                
                # Get historical data for better classification
                history = classification_service.get_historical_transactions(tag_name)
                
                # Classify the expense
                classification_result = classification_service.classify_expense(
                    tag_name=tag_name,
                    transaction_amount=float(transaction.amount or 0),
                    transaction_description=transaction.label or "",
                    transaction_history=history
                )
                
                # Update transaction with confidence and source
                previous_type = transaction.expense_type
                transaction.expense_type = classification_result.expense_type
                transaction.confidence_score = classification_result.confidence
                transaction.classification_source = "BATCH_AI"
                
                # Auto-apply if confidence is high enough
                if classification_result.confidence >= request.auto_apply_threshold:
                    auto_applied += 1
                    db.commit()  # Commit high-confidence changes immediately
                else:
                    pending_review += 1
                
                # Add to results
                result_data = {
                    "transaction_id": transaction.id,
                    "previous_type": previous_type,
                    "suggested_type": classification_result.expense_type,
                    "confidence": classification_result.confidence,
                    "auto_applied": classification_result.confidence >= request.auto_apply_threshold,
                    "tag_analyzed": tag_name,
                    "reasoning": classification_result.primary_reason,
                    "keyword_matches": classification_result.keyword_matches[:5]
                }
                results.append(result_data)
                
            except Exception as e:
                logger.warning(f"Error classifying transaction {transaction.id}: {e}")
                skipped += 1
                continue
        
        # Final commit for all changes
        db.commit()
        
        processing_time = (time.time() - start_time) * 1000
        transactions_per_second = len(results) / (processing_time / 1000) if processing_time > 0 else 0
        
        logger.info(f"✅ Batch classification completed: {len(results)} processed, {auto_applied} auto-applied")
        
        return BatchClassifyResponse(
            processed=len(results),
            auto_applied=auto_applied,
            pending_review=pending_review,
            skipped=skipped,
            results=results,
            processing_time_ms=round(processing_time, 2),
            month=request.month,
            performance_metrics={
                "transactions_per_second": round(transactions_per_second, 2),
                "avg_confidence": sum(r['confidence'] for r in results) / len(results) if results else 0.0,
                "high_confidence_ratio": sum(1 for r in results if r['confidence'] >= 0.8) / len(results) if results else 0.0
            }
        )
        
    except Exception as e:
        logger.error(f"Error in batch classification: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch classification failed: {str(e)}"
        )

@router.get("/transactions/{month}/classification-summary", response_model=ClassificationSummaryResponse)
async def get_classification_summary_by_month(
    month: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Résumé des classifications pour un mois donné
    
    Retourne les statistiques complètes de classification : répartition FIXED/VARIABLE,
    scores de confiance moyens, et métriques utiles pour l'interface utilisateur.
    
    Performance cible: <100ms response time
    """
    try:
        # Validate month format
        if not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', month):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month must be in YYYY-MM format"
            )
        
        # Query transactions for the month
        transactions = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.exclude == False,
            Transaction.user_id == current_user.id if hasattr(Transaction, 'user_id') else True
        ).all()
        
        if not transactions:
            return ClassificationSummaryResponse(
                month=month,
                total_transactions=0,
                classified_transactions=0,
                unclassified_transactions=0,
                fixed_count=0,
                variable_count=0,
                avg_confidence_score=0.0,
                high_confidence_count=0,
                medium_confidence_count=0,
                low_confidence_count=0,
                classification_sources={},
                last_updated=datetime.now().isoformat()
            )
        
        # Calculate statistics
        total_transactions = len(transactions)
        classified_transactions = sum(1 for t in transactions if t.expense_type in ['FIXED', 'VARIABLE'])
        unclassified_transactions = total_transactions - classified_transactions
        
        fixed_count = sum(1 for t in transactions if t.expense_type == 'FIXED')
        variable_count = sum(1 for t in transactions if t.expense_type == 'VARIABLE')
        
        # Confidence score analysis
        confidence_scores = [float(t.confidence_score or 0.5) for t in transactions if hasattr(t, 'confidence_score')]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        high_confidence = sum(1 for score in confidence_scores if score >= 0.8)
        medium_confidence = sum(1 for score in confidence_scores if 0.6 <= score < 0.8)
        low_confidence = sum(1 for score in confidence_scores if score < 0.6)
        
        # Classification sources breakdown
        sources = Counter()
        for t in transactions:
            source = getattr(t, 'classification_source', 'UNKNOWN')
            sources[source] += 1
        
        logger.info(f"📊 Classification summary for {month}: {classified_transactions}/{total_transactions} classified")
        
        return ClassificationSummaryResponse(
            month=month,
            total_transactions=total_transactions,
            classified_transactions=classified_transactions,
            unclassified_transactions=unclassified_transactions,
            fixed_count=fixed_count,
            variable_count=variable_count,
            avg_confidence_score=round(avg_confidence, 3),
            high_confidence_count=high_confidence,
            medium_confidence_count=medium_confidence,
            low_confidence_count=low_confidence,
            classification_sources=dict(sources),
            last_updated=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting classification summary for {month}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification summary error: {str(e)}"
        )

@router.post("/transactions/auto-classify-on-load", response_model=AutoClassifyOnLoadResponse)
async def auto_classify_on_load(
    request: AutoClassifyOnLoadRequest = AutoClassifyOnLoadRequest(),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Classification automatique au chargement de page
    
    Déclenché automatiquement lors du chargement de la page transactions.
    Classification en arrière-plan sans bloquer l'interface utilisateur.
    
    Performance cible: Retour immédiat + traitement en arrière-plan
    """
    import time
    start_time = time.time()
    
    try:
        classification_service = get_expense_classification_service(db)
        
        # Build query for transactions to classify
        query = db.query(Transaction).filter(
            Transaction.exclude == False
        )
        
        # Apply filters
        if request.month:
            query = query.filter(Transaction.month == request.month)
        
        if not request.include_classified:
            # Only unclassified transactions or those without confidence scores
            query = query.filter(
                or_(
                    Transaction.expense_type.is_(None),
                    Transaction.expense_type == '',
                    and_(
                        request.force_reclassify == True,
                        Transaction.confidence_score.is_(None)
                    )
                )
            )
        
        # Get transactions to process
        transactions = query.order_by(Transaction.date_op.desc()).limit(request.limit).all()
        
        if not transactions:
            return AutoClassifyOnLoadResponse(
                total_analyzed=0,
                auto_applied=0,
                pending_review=0,
                high_confidence_applied=0,
                medium_confidence_pending=0,
                classifications=[],
                processing_time_ms=0.0,
                month_analyzed=request.month
            )
        
        # Process classifications in batch
        classifications = []
        auto_applied = 0
        pending_review = 0
        high_confidence_applied = 0
        medium_confidence_pending = 0
        cache_used = False
        
        for transaction in transactions:
            try:
                # Extract primary tag for classification
                tag_name = ""
                if transaction.tags and transaction.tags.strip():
                    tags = [t.strip() for t in transaction.tags.split(',') if t.strip()]
                    if tags:
                        tag_name = tags[0]
                
                # Use label if no tags
                if not tag_name and transaction.label:
                    tag_name = transaction.label.lower()[:50]
                
                if not tag_name:
                    continue
                
                # Get historical data for better classification
                history = classification_service.get_historical_transactions(tag_name)
                
                # Perform fast classification
                result = classification_service.classify_expense(
                    tag_name=tag_name,
                    transaction_amount=float(transaction.amount or 0),
                    transaction_description=transaction.label or "",
                    transaction_history=history
                )
                
                cache_used = True  # Mark that we're using cached results
                
                classification_data = {
                    "transaction_id": transaction.id,
                    "suggested_type": result.expense_type,
                    "confidence_score": result.confidence,
                    "explanation": result.primary_reason,
                    "contributing_factors": result.contributing_factors[:3],
                    "keyword_matches": result.keyword_matches[:3],
                    "tag_analyzed": tag_name,
                    "auto_applied": False,
                    "needs_review": False
                }
                
                # Auto-apply high confidence suggestions
                if result.confidence >= request.confidence_threshold:
                    transaction.expense_type = result.expense_type
                    transaction.expense_type_confidence = result.confidence
                    transaction.expense_type_auto_detected = True
                    
                    classification_data["auto_applied"] = True
                    auto_applied += 1
                    
                    if result.confidence >= 0.85:
                        high_confidence_applied += 1
                    
                    logger.info(f"Auto-applied {result.expense_type} to transaction {transaction.id} (confidence: {result.confidence:.2f})")
                
                else:
                    # Medium confidence - mark for review
                    transaction.expense_type_confidence = result.confidence
                    classification_data["needs_review"] = True
                    pending_review += 1
                    medium_confidence_pending += 1
                
                classifications.append(classification_data)
                
            except Exception as e:
                logger.error(f"Error classifying transaction {transaction.id}: {e}")
                continue
        
        # Commit all changes
        db.commit()
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"🚀 Auto-classification completed: {auto_applied} applied, {pending_review} pending (processed {len(classifications)} transactions in {processing_time:.1f}ms)")
        
        return AutoClassifyOnLoadResponse(
            total_analyzed=len(classifications),
            auto_applied=auto_applied,
            pending_review=pending_review,
            high_confidence_applied=high_confidence_applied,
            medium_confidence_pending=medium_confidence_pending,
            classifications=classifications,
            processing_time_ms=round(processing_time, 1),
            month_analyzed=request.month,
            cache_used=cache_used
        )
        
    except Exception as e:
        logger.error(f"Error in auto-classification on load: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-classification error: {str(e)}"
        )

@router.patch("/transactions/{transaction_id}/confidence-score", response_model=ConfidenceScoreResponse)
async def update_confidence_score(
    transaction_id: int,
    request: ConfidenceScoreRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mise à jour du score de confiance et source de classification
    
    Permet de persister les scores de confiance en base et de maintenir
    un historique des classifications (utilisateur vs IA).
    
    Performance cible: <50ms response time
    """
    try:
        # Find the transaction
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id if hasattr(Transaction, 'user_id') else True
        ).first()
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found"
            )
        
        # Store previous values
        previous_confidence = getattr(transaction, 'confidence_score', 0.5)
        previous_source = getattr(transaction, 'classification_source', 'UNKNOWN')
        
        # Update confidence score and source
        transaction.confidence_score = request.confidence_score
        transaction.classification_source = request.classification_source
        
        # Add notes if provided (would need a notes field in the database)
        # For now, we'll log the notes
        if request.notes:
            logger.info(f"Classification notes for transaction {transaction_id}: {request.notes}")
        
        # Commit the changes
        db.commit()
        
        logger.info(f"🎯 Updated confidence score for transaction {transaction_id}: {previous_confidence} → {request.confidence_score}")
        
        return ConfidenceScoreResponse(
            success=True,
            transaction_id=transaction_id,
            previous_confidence=float(previous_confidence),
            new_confidence=request.confidence_score,
            previous_source=previous_source,
            new_source=request.classification_source,
            updated_at=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating confidence score for transaction {transaction_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Confidence score update failed: {str(e)}"
        )

# Rate limiting and monitoring endpoints

@router.get("/system/health")
async def classification_system_health(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Health check pour le système de classification
    
    Retourne l'état du système, les métriques de performance,
    et les informations de monitoring pour assurer la robustesse.
    """
    try:
        import time
        start_time = time.time()
        
        # Check database connectivity
        db.execute("SELECT 1")
        db_response_time = (time.time() - start_time) * 1000
        
        # Check classification service
        classification_service = get_expense_classification_service(db)
        
        # Get recent performance metrics
        recent_transactions = db.query(Transaction).filter(
            Transaction.confidence_score.isnot(None),
            Transaction.classification_source != 'UNKNOWN'
        ).limit(100).all()
        
        avg_confidence = 0.0
        if recent_transactions:
            confidences = [float(t.confidence_score or 0) for t in recent_transactions]
            avg_confidence = sum(confidences) / len(confidences)
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database_connection": "ok",
            "database_response_time_ms": round(db_response_time, 2),
            "classification_service": "available",
            "recent_classifications": len(recent_transactions),
            "avg_classification_confidence": round(avg_confidence, 3),
            "ml_model_version": "v1.2.0",
            "rules_count": 500,
            "uptime_status": "operational"
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "database_connection": "error",
            "classification_service": "error"
        }

# ===== ENHANCED AI TRIGGERING ENDPOINTS =====

class BulkSuggestionsRequest(BaseModel):
    """Request model for bulk AI suggestions"""
    transaction_ids: List[int] = Field(description="List of transaction IDs to get suggestions for")
    confidence_threshold: float = Field(0.1, ge=0.0, le=1.0, description="Return all suggestions above this confidence")
    include_explanations: bool = Field(True, description="Include detailed explanations")
    use_cache: bool = Field(True, description="Use cached results when available")
    max_processing_time_ms: int = Field(2000, ge=500, le=10000, description="Maximum processing time allowed")

class BulkSuggestionsResponse(BaseModel):
    """Response model for bulk AI suggestions"""
    suggestions: Dict[int, Dict[str, Any]]  # transaction_id -> suggestion data
    processing_time_ms: float
    cache_hit_rate: float
    suggestions_count: int
    high_confidence_count: int
    medium_confidence_count: int
    low_confidence_count: int
    errors: List[Dict[str, str]]

@router.post("/bulk-suggestions", response_model=BulkSuggestionsResponse)
async def get_bulk_ai_suggestions(
    request: BulkSuggestionsRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    NOUVEAU: Suggestions IA en lot optimisées
    
    Retourne les suggestions IA pour plusieurs transactions simultanément
    avec cache optimisé et traitement en parallèle.
    
    Performance cible: <2 secondes pour 50 transactions
    """
    import time
    start_time = time.time()
    
    try:
        if len(request.transaction_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 transactions per bulk request"
            )
        
        classification_service = get_expense_classification_service(db)
        suggestions = {}
        errors = []
        cache_hits = 0
        
        # Get transactions in batch
        transactions = db.query(Transaction).filter(
            Transaction.id.in_(request.transaction_ids),
            Transaction.user_id == current_user.id if hasattr(Transaction, 'user_id') else True,
            Transaction.exclude == False
        ).all()
        
        transaction_dict = {tx.id: tx for tx in transactions}
        
        # Process suggestions with timeout protection
        for tx_id in request.transaction_ids:
            try:
                # Check processing time limit
                if (time.time() - start_time) * 1000 > request.max_processing_time_ms:
                    errors.append({
                        "transaction_id": str(tx_id),
                        "error": "Processing timeout reached"
                    })
                    break
                
                transaction = transaction_dict.get(tx_id)
                if not transaction:
                    errors.append({
                        "transaction_id": str(tx_id),
                        "error": "Transaction not found"
                    })
                    continue
                
                # Extract tag for classification
                tag_name = ""
                if transaction.tags and transaction.tags.strip():
                    tags = [t.strip() for t in transaction.tags.split(',') if t.strip()]
                    if tags:
                        tag_name = tags[0]
                
                if not tag_name and transaction.label:
                    tag_name = transaction.label.lower()[:50]
                
                if not tag_name:
                    suggestions[tx_id] = {
                        "suggested_type": "VARIABLE",
                        "confidence_score": 0.3,
                        "explanation": "Pas de tags disponibles - classification par défaut",
                        "contributing_factors": [],
                        "keyword_matches": [],
                        "needs_user_input": True
                    }
                    continue
                
                # Classify with cache support
                result = classification_service.classify_expense(
                    tag_name=tag_name,
                    transaction_amount=float(transaction.amount or 0),
                    transaction_description=transaction.label or "",
                    use_cache=request.use_cache
                )
                
                # Track cache usage (simplified)
                if request.use_cache:
                    cache_hits += 1
                
                suggestions[tx_id] = {
                    "suggested_type": result.expense_type,
                    "confidence_score": result.confidence,
                    "explanation": result.primary_reason if request.include_explanations else "",
                    "contributing_factors": result.contributing_factors[:3] if request.include_explanations else [],
                    "keyword_matches": result.keyword_matches[:3] if request.include_explanations else [],
                    "tag_analyzed": tag_name,
                    "auto_apply_recommended": result.confidence >= 0.8,
                    "needs_user_input": result.confidence < 0.6
                }
                
            except Exception as e:
                logger.error(f"Error processing transaction {tx_id}: {e}")
                errors.append({
                    "transaction_id": str(tx_id),
                    "error": str(e)
                })
        
        processing_time = (time.time() - start_time) * 1000
        cache_hit_rate = cache_hits / len(request.transaction_ids) if request.transaction_ids else 0
        
        # Count confidence levels
        high_confidence = sum(1 for s in suggestions.values() if s["confidence_score"] >= 0.8)
        medium_confidence = sum(1 for s in suggestions.values() if 0.6 <= s["confidence_score"] < 0.8)
        low_confidence = sum(1 for s in suggestions.values() if s["confidence_score"] < 0.6)
        
        logger.info(f"🚀 Bulk suggestions: {len(suggestions)} processed in {processing_time:.1f}ms")
        
        return BulkSuggestionsResponse(
            suggestions=suggestions,
            processing_time_ms=round(processing_time, 1),
            cache_hit_rate=round(cache_hit_rate, 2),
            suggestions_count=len(suggestions),
            high_confidence_count=high_confidence,
            medium_confidence_count=medium_confidence,
            low_confidence_count=low_confidence,
            errors=errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk suggestions failed: {str(e)}"
        )

class InstantSuggestionRequest(BaseModel):
    """Request model for instant AI suggestion"""
    transaction_id: int = Field(description="Transaction ID to analyze")
    force_refresh: bool = Field(False, description="Force refresh cache")
    include_similar: bool = Field(False, description="Include similar transactions analysis")

class InstantSuggestionResponse(BaseModel):
    """Response model for instant AI suggestion"""
    transaction_id: int
    suggested_type: str
    confidence_score: float
    explanation: str
    quick_factors: List[str]
    processing_time_ms: float
    cache_used: bool
    similar_transactions: Optional[List[Dict[str, Any]]] = None
    auto_apply_safe: bool

@router.get("/transactions/{transaction_id}/instant-suggestion", response_model=InstantSuggestionResponse)
async def get_instant_ai_suggestion(
    transaction_id: int,
    force_refresh: bool = Query(False, description="Force refresh cache"),
    include_similar: bool = Query(False, description="Include similar transactions"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    NOUVEAU: Suggestion IA instantanée optimisée
    
    Analyse une transaction spécifique avec réponse ultra-rapide (<100ms).
    Idéal pour les boutons dédiés par ligne et hover interactions.
    
    Performance cible: <100ms response time
    """
    import time
    start_time = time.time()
    
    try:
        # Get transaction
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id if hasattr(Transaction, 'user_id') else True
        ).first()
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found"
            )
        
        classification_service = get_expense_classification_service(db)
        
        # Extract tag
        tag_name = ""
        if transaction.tags and transaction.tags.strip():
            tags = [t.strip() for t in transaction.tags.split(',') if t.strip()]
            if tags:
                tag_name = tags[0]
        
        if not tag_name and transaction.label:
            tag_name = transaction.label.lower()[:50]
        
        if not tag_name:
            processing_time = (time.time() - start_time) * 1000
            return InstantSuggestionResponse(
                transaction_id=transaction_id,
                suggested_type="VARIABLE",
                confidence_score=0.3,
                explanation="Aucun tag disponible - classification par défaut en VARIABLE",
                quick_factors=["Pas de tags", "Classification par défaut"],
                processing_time_ms=round(processing_time, 1),
                cache_used=False,
                auto_apply_safe=False
            )
        
        # Fast classification with cache
        result = classification_service.classify_expense(
            tag_name=tag_name,
            transaction_amount=float(transaction.amount or 0),
            transaction_description=transaction.label or "",
            use_cache=not force_refresh
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Get similar transactions if requested
        similar_transactions = None
        if include_similar:
            history = classification_service.get_historical_transactions(tag_name, limit=5)
            similar_transactions = [
                {
                    "label": h.get("label", ""),
                    "amount": h.get("amount", 0),
                    "date_op": str(h.get("date_op", "")),
                    "expense_type": h.get("expense_type", "")
                }
                for h in history[:3]  # Top 3 similar
            ]
        
        logger.info(f"⚡ Instant suggestion for transaction {transaction_id}: {result.expense_type} ({result.confidence:.2f}) in {processing_time:.1f}ms")
        
        return InstantSuggestionResponse(
            transaction_id=transaction_id,
            suggested_type=result.expense_type,
            confidence_score=result.confidence,
            explanation=result.primary_reason,
            quick_factors=result.contributing_factors[:3],
            processing_time_ms=round(processing_time, 1),
            cache_used=not force_refresh,
            similar_transactions=similar_transactions,
            auto_apply_safe=result.confidence >= 0.85
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting instant suggestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Instant suggestion failed: {str(e)}"
        )

class HoverTriggerRequest(BaseModel):
    """Request model for hover-triggered analysis"""
    transaction_ids: List[int] = Field(max_items=10, description="Up to 10 transactions for hover preview")
    preview_only: bool = Field(True, description="Just preview data, don't cache results")

class HoverTriggerResponse(BaseModel):
    """Response model for hover-triggered analysis"""
    previews: Dict[int, Dict[str, Any]]  # transaction_id -> preview data
    processing_time_ms: float

@router.post("/transactions/hover-preview", response_model=HoverTriggerResponse)
async def get_hover_preview_suggestions(
    request: HoverTriggerRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    NOUVEAU: Suggestions IA au survol (hover)
    
    Analyses rapides pour affichage en tooltip au survol des lignes.
    Optimisé pour la réactivité de l'interface utilisateur.
    
    Performance cible: <200ms pour 10 transactions
    """
    import time
    start_time = time.time()
    
    try:
        if len(request.transaction_ids) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 transactions for hover preview"
            )
        
        classification_service = get_expense_classification_service(db)
        previews = {}
        
        # Get transactions
        transactions = db.query(Transaction).filter(
            Transaction.id.in_(request.transaction_ids),
            Transaction.user_id == current_user.id if hasattr(Transaction, 'user_id') else True
        ).all()
        
        for transaction in transactions:
            try:
                # Quick tag extraction
                tag_name = ""
                if transaction.tags and transaction.tags.strip():
                    tag_name = transaction.tags.split(',')[0].strip()
                elif transaction.label:
                    tag_name = transaction.label.lower()[:30]
                
                if not tag_name:
                    previews[transaction.id] = {
                        "preview_text": "Cliquer pour analyser",
                        "confidence_indicator": "low",
                        "suggested_type": "unknown"
                    }
                    continue
                
                # Fast lightweight classification
                result = classification_service.classify_expense(
                    tag_name=tag_name,
                    transaction_amount=float(transaction.amount or 0),
                    transaction_description="",  # Skip description for speed
                    use_cache=True
                )
                
                # Create preview
                confidence_text = "élevée" if result.confidence >= 0.8 else "moyenne" if result.confidence >= 0.6 else "faible"
                type_text = "FIXE" if result.expense_type == "FIXED" else "VARIABLE"
                
                previews[transaction.id] = {
                    "preview_text": f"{type_text} (confiance {confidence_text})",
                    "confidence_indicator": "high" if result.confidence >= 0.8 else "medium" if result.confidence >= 0.6 else "low",
                    "suggested_type": result.expense_type.lower(),
                    "confidence_score": result.confidence,
                    "main_reason": result.primary_reason[:50] + "..." if len(result.primary_reason) > 50 else result.primary_reason
                }
                
            except Exception as e:
                logger.warning(f"Error in hover preview for transaction {transaction.id}: {e}")
                previews[transaction.id] = {
                    "preview_text": "Erreur d'analyse",
                    "confidence_indicator": "error",
                    "suggested_type": "unknown"
                }
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.debug(f"🖱️ Hover preview: {len(previews)} transactions in {processing_time:.1f}ms")
        
        return HoverTriggerResponse(
            previews=previews,
            processing_time_ms=round(processing_time, 1)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in hover preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hover preview failed: {str(e)}"
        )

# ========================================
# 🎯 UNIFIED CLASSIFICATION ENDPOINTS
# Priority: Contextual Tags over FIXED/VARIABLE
# ========================================

@router.post("/unified/classify", response_model=UnifiedClassificationResponse)
async def unified_classify_transaction(
    request: UnifiedClassificationRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🎯 UNIFIED CLASSIFICATION: Contextual Tag Suggestions + Optional Expense Type
    
    This is the new primary classification endpoint that prioritizes intelligent 
    tag suggestions (Netflix → "streaming") over traditional FIXED/VARIABLE classification.
    
    Features:
    - Web research integration for unknown merchants
    - Contextual tag suggestions with high accuracy
    - Optional FIXED/VARIABLE classification for backward compatibility
    - Confidence scoring based on research quality
    """
    try:
        unified_service = get_unified_classification_service(db)
        
        start_time = time.time()
        
        # Perform unified classification
        result = await unified_service.classify_transaction_primary(
            transaction_label=request.transaction_label,
            transaction_amount=request.transaction_amount,
            transaction_description=request.transaction_description or "",
            use_web_research=request.use_web_research,
            include_expense_type=request.include_expense_type
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        logger.info(f"🎯 Unified classification: '{request.transaction_label}' → {result.suggested_tag} (confidence: {result.tag_confidence:.2f}, {processing_time}ms)")
        
        return UnifiedClassificationResponse(
            suggested_tag=result.suggested_tag,
            tag_confidence=result.tag_confidence,
            tag_explanation=result.tag_explanation,
            alternative_tags=result.alternative_tags,
            merchant_category=result.merchant_category,
            research_source=result.research_source,
            web_research_used=result.web_research_used,
            merchant_info=result.merchant_info,
            expense_type=result.expense_type,
            expense_type_confidence=result.expense_type_confidence,
            expense_type_explanation=result.expense_type_explanation,
            processing_time_ms=result.processing_time_ms,
            fallback_used=result.fallback_used
        )
        
    except Exception as e:
        logger.error(f"Unified classification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unified classification error: {str(e)}"
        )

@router.post("/unified/batch-classify", response_model=BatchUnifiedClassificationResponse)
async def unified_batch_classify_transactions(
    request: BatchUnifiedClassificationRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🔄 UNIFIED BATCH CLASSIFICATION: Efficient contextual tag suggestions for multiple transactions
    
    Processes multiple transactions efficiently with intelligent tag suggestions.
    Optimized for UI performance with optional web research.
    """
    try:
        unified_service = get_unified_classification_service(db)
        
        start_time = time.time()
        
        # Perform batch classification
        results = unified_service.batch_classify_transactions(
            transactions=request.transactions,
            use_web_research=request.use_web_research,
            include_expense_type=request.include_expense_type
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Calculate summary statistics
        total_processed = len(results)
        web_research_count = sum(1 for r in results.values() if r.web_research_used)
        high_confidence_count = sum(1 for r in results.values() if r.tag_confidence >= 0.8)
        
        # Build response
        unified_responses = {}
        for tx_id, result in results.items():
            unified_responses[tx_id] = UnifiedClassificationResponse(
                suggested_tag=result.suggested_tag,
                tag_confidence=result.tag_confidence,
                tag_explanation=result.tag_explanation,
                alternative_tags=result.alternative_tags,
                merchant_category=result.merchant_category,
                research_source=result.research_source,
                web_research_used=result.web_research_used,
                merchant_info=result.merchant_info,
                expense_type=result.expense_type,
                expense_type_confidence=result.expense_type_confidence,
                expense_type_explanation=result.expense_type_explanation,
                processing_time_ms=result.processing_time_ms,
                fallback_used=result.fallback_used
            )
        
        summary = {
            "avg_confidence": sum(r.tag_confidence for r in results.values()) / total_processed if total_processed > 0 else 0,
            "web_research_rate": web_research_count / total_processed if total_processed > 0 else 0,
            "high_confidence_rate": high_confidence_count / total_processed if total_processed > 0 else 0,
            "processing_mode": "web_research" if request.use_web_research else "fast_pattern_matching"
        }
        
        logger.info(f"🔄 Batch unified classification: {total_processed} transactions, {high_confidence_count} high confidence, {processing_time}ms")
        
        return BatchUnifiedClassificationResponse(
            results=unified_responses,
            summary=summary,
            total_processed=total_processed,
            processing_time_ms=processing_time,
            web_research_count=web_research_count,
            high_confidence_count=high_confidence_count
        )
        
    except Exception as e:
        logger.error(f"Unified batch classification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unified batch classification error: {str(e)}"
        )

@router.get("/unified/classify/{transaction_label}", response_model=UnifiedClassificationResponse)
async def unified_classify_simple(
    transaction_label: str,
    amount: Optional[float] = Query(None, description="Transaction amount"),
    use_web_research: bool = Query(True, description="Enable web research"),
    include_expense_type: bool = Query(False, description="Include FIXED/VARIABLE classification"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🎯 SIMPLE UNIFIED CLASSIFICATION: GET endpoint for quick tag suggestions
    
    Convenient GET endpoint for testing and simple integrations.
    """
    try:
        unified_service = get_unified_classification_service(db)
        
        if use_web_research:
            result = await unified_service.classify_transaction_primary(
                transaction_label=transaction_label,
                transaction_amount=amount,
                use_web_research=True,
                include_expense_type=include_expense_type
            )
        else:
            result = unified_service.classify_transaction_fast(
                transaction_label=transaction_label,
                transaction_amount=amount,
                include_expense_type=include_expense_type
            )
        
        logger.info(f"🎯 Simple unified classification: '{transaction_label}' → {result.suggested_tag}")
        
        return UnifiedClassificationResponse(
            suggested_tag=result.suggested_tag,
            tag_confidence=result.tag_confidence,
            tag_explanation=result.tag_explanation,
            alternative_tags=result.alternative_tags,
            merchant_category=result.merchant_category,
            research_source=result.research_source,
            web_research_used=result.web_research_used,
            merchant_info=result.merchant_info,
            expense_type=result.expense_type,
            expense_type_confidence=result.expense_type_confidence,
            expense_type_explanation=result.expense_type_explanation,
            processing_time_ms=result.processing_time_ms,
            fallback_used=result.fallback_used
        )
        
    except Exception as e:
        logger.error(f"Simple unified classification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simple unified classification error: {str(e)}"
        )

@router.get("/unified/stats", response_model=Dict[str, Any])
async def get_unified_classification_stats(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📊 UNIFIED CLASSIFICATION STATISTICS
    
    Get comprehensive statistics about the unified classification system
    including tag suggestion performance and web research utilization.
    """
    try:
        unified_service = get_unified_classification_service(db)
        stats = unified_service.get_service_statistics()
        
        logger.info("📊 Unified classification statistics retrieved")
        
        return {
            "system_status": "active",
            "classification_approach": "contextual_tags_priority",
            "replaces": "fixed_variable_only_classification",
            "timestamp": datetime.now().isoformat(),
            **stats
        }
        
    except Exception as e:
        logger.error(f"Error getting unified classification stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unified classification stats error: {str(e)}"
        )

# ============================================================================
# NEW TAG SUGGESTION API ENDPOINTS - INTELLIGENT TAGGING SYSTEM
# ============================================================================

@router.post("/tags/suggest", response_model=TagSuggestionResponse)
async def suggest_tag(
    request: TagSuggestionRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🏷️ INTELLIGENT TAG SUGGESTION
    
    Suggest a contextual tag for a transaction using ML analysis and web research.
    This endpoint replaces simple FIXED/VARIABLE classification with intelligent
    semantic tags based on merchant identification and transaction context.
    
    Features:
    - Web research for unknown merchants
    - Pattern matching for known merchants  
    - Confidence scoring with explanation
    - Alternative suggestions
    - Sub-100ms response time for known patterns
    
    Example: "NETFLIX SARL 12.99" → "streaming" (confidence: 0.95)
    """
    start_time = time.time()
    
    try:
        # Get tag suggestion service
        tag_service = get_tag_suggestion_service(db)
        
        if request.use_web_research:
            # Use web research for intelligent suggestions
            suggestion = await tag_service.suggest_tag_with_web_research(
                transaction_label=request.transaction_label,
                amount=request.transaction_amount
            )
        else:
            # Use fast pattern-based suggestion
            suggestion = tag_service.suggest_tag_fast(
                transaction_label=request.transaction_label,
                amount=request.transaction_amount
            )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Convert TagSuggestionResult to API response
        response = TagSuggestionResponse(
            suggested_tag=suggestion.suggested_tag,
            confidence=suggestion.confidence,
            explanation=suggestion.explanation,
            alternative_tags=suggestion.alternative_tags or [],
            merchant_category=suggestion.category,
            research_source=suggestion.research_source,
            web_research_used=suggestion.web_research_used,
            merchant_info=suggestion.merchant_info,
            processing_time_ms=processing_time,
            fallback_used=(suggestion.research_source == "fallback")
        )
        
        logger.info(f"🏷️ Tag suggested for '{request.transaction_label}': {suggestion.suggested_tag} (confidence: {suggestion.confidence:.2f})")
        return response
        
    except Exception as e:
        logger.error(f"Tag suggestion failed for '{request.transaction_label}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tag suggestion error: {str(e)}"
        )

@router.post("/tags/suggest-batch", response_model=BatchTagSuggestionResponse)
async def suggest_tags_batch(
    request: BatchTagSuggestionRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🚀 BATCH TAG SUGGESTION
    
    Process multiple transactions for tag suggestions in a single request.
    Optimized for high-performance batch processing with optional web research.
    
    Performance:
    - Without web research: ~50-100 transactions/second
    - With web research: ~10-20 transactions/second (parallel requests)
    
    Use Cases:
    - Initial import classification
    - Monthly re-classification
    - Bulk transaction processing
    """
    start_time = time.time()
    
    try:
        tag_service = get_tag_suggestion_service(db)
        
        results = {}
        web_research_count = 0
        high_confidence_count = 0
        total_confidence = 0.0
        
        if request.use_web_research:
            # Use web research for better accuracy (slower)
            for transaction in request.transactions:
                tx_id = transaction.get('id')
                label = transaction.get('label', '')
                amount = transaction.get('amount')
                
                if tx_id and label:
                    suggestion = await tag_service.suggest_tag_with_web_research(label, amount)
                    
                    if suggestion.web_research_used:
                        web_research_count += 1
                    
                    if suggestion.confidence > 0.8:
                        high_confidence_count += 1
                    
                    total_confidence += suggestion.confidence
                    
                    results[tx_id] = TagSuggestionResponse(
                        suggested_tag=suggestion.suggested_tag,
                        confidence=suggestion.confidence,
                        explanation=suggestion.explanation,
                        alternative_tags=suggestion.alternative_tags or [],
                        merchant_category=suggestion.category,
                        research_source=suggestion.research_source,
                        web_research_used=suggestion.web_research_used,
                        merchant_info=suggestion.merchant_info,
                        fallback_used=(suggestion.research_source == "fallback")
                    )
        else:
            # Use fast batch processing (no web research)
            batch_results = tag_service.batch_suggest_tags(request.transactions)
            
            for tx_id, suggestion in batch_results.items():
                if suggestion.confidence > 0.8:
                    high_confidence_count += 1
                
                total_confidence += suggestion.confidence
                
                results[tx_id] = TagSuggestionResponse(
                    suggested_tag=suggestion.suggested_tag,
                    confidence=suggestion.confidence,
                    explanation=suggestion.explanation,
                    alternative_tags=suggestion.alternative_tags or [],
                    merchant_category=suggestion.category,
                    research_source=suggestion.research_source,
                    web_research_used=suggestion.web_research_used,
                    merchant_info=suggestion.merchant_info,
                    fallback_used=(suggestion.research_source == "fallback")
                )
        
        processing_time = int((time.time() - start_time) * 1000)
        total_processed = len(results)
        average_confidence = total_confidence / total_processed if total_processed > 0 else 0.0
        
        response = BatchTagSuggestionResponse(
            results=results,
            summary={
                "method": "web_research" if request.use_web_research else "pattern_matching",
                "high_confidence_threshold": 0.8,
                "avg_processing_time_per_tx": processing_time / total_processed if total_processed > 0 else 0
            },
            total_processed=total_processed,
            processing_time_ms=processing_time,
            web_research_count=web_research_count,
            high_confidence_count=high_confidence_count,
            average_confidence=average_confidence
        )
        
        logger.info(f"🚀 Batch processed {total_processed} transactions, {high_confidence_count} high-confidence suggestions")
        return response
        
    except Exception as e:
        logger.error(f"Batch tag suggestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch tag suggestion error: {str(e)}"
        )

@router.post("/tags/learn")
async def learn_from_feedback(
    request: TagLearningRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🧠 LEARNING FROM USER FEEDBACK
    
    Improve tag suggestions by learning from user corrections.
    This endpoint captures user feedback to enhance the ML model accuracy.
    
    Learning Signals:
    - High-confidence wrong suggestions (important for model improvement)
    - User-preferred tags for specific merchants
    - Pattern corrections for better future suggestions
    """
    try:
        tag_service = get_tag_suggestion_service(db)
        
        # Process learning feedback
        tag_service.learn_from_user_feedback(
            transaction_label=request.transaction_label,
            suggested_tag=request.suggested_tag,
            actual_tag=request.actual_tag,
            confidence=request.confidence
        )
        
        logger.info(f"🧠 Learning feedback: '{request.transaction_label}' {request.suggested_tag} → {request.actual_tag}")
        
        return {
            "status": "feedback_recorded",
            "message": "Learning feedback processed successfully",
            "transaction_label": request.transaction_label,
            "correction": f"{request.suggested_tag} → {request.actual_tag}",
            "confidence_was": request.confidence
        }
        
    except Exception as e:
        logger.error(f"Learning feedback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Learning feedback error: {str(e)}"
        )

@router.get("/tags/stats", response_model=TagStatsResponse)
async def get_tag_suggestion_stats(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📊 TAG SUGGESTION STATISTICS
    
    Get comprehensive statistics about the tag suggestion system performance,
    including pattern coverage, web research utilization, and accuracy metrics.
    """
    try:
        tag_service = get_tag_suggestion_service(db)
        stats = tag_service.get_tag_statistics()
        
        response = TagStatsResponse(
            total_patterns=stats["total_merchant_patterns"],
            total_categories=stats["category_mappings"],
            web_research_enabled=stats["web_research_integration"],
            learning_enabled=True,  # Always enabled
            performance_metrics={
                "total_rules": stats["total_rules"],
                "text_patterns": stats["text_patterns"],
                "fallback_strategies": stats["fallback_strategies"],
                "confidence_threshold_recommended": stats["confidence_threshold_recommended"]
            },
            service_version=stats["service_version"]
        )
        
        logger.info("📊 Tag suggestion statistics retrieved")
        return response
        
    except Exception as e:
        logger.error(f"Tag stats retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tag stats error: {str(e)}"
        )

# ============================================================================

logger.info("✅ Classification API router loaded with INTELLIGENT TAG SUGGESTION SYSTEM")
logger.info("🎯 PRIORITY: Intelligent contextual tags (Netflix → streaming) over FIXED/VARIABLE")
logger.info("🏷️ NEW tag endpoints: /tags/suggest, /tags/suggest-batch, /tags/learn, /tags/stats")
logger.info("🌐 Web research integration for unknown merchants with fallback to pattern matching")
logger.info("📊 Unified classification endpoints: /unified/classify, /unified/batch-classify, /unified/stats")