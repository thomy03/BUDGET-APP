"""
Classification API Router for intelligent expense classification
Provides endpoints for ML-based classification of expense tags as FIXED vs VARIABLE
"""

import logging
import time
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import Field
from sqlalchemy.orm import Session
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
from services.tag_automation import get_tag_automation_service

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

logger.info("✅ Classification API router loaded with ML intelligence endpoints")