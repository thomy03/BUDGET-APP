"""
Intelligent Tag Suggestion API Router
Revolutionary endpoints for ML-based tag suggestions using web research
"""

import logging
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from models.database import get_db, Transaction
from services.intelligent_tag_service import get_intelligent_tag_service, IntelligentTagResult

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/intelligent-tags",
    tags=["intelligent-tags"],
    responses={404: {"description": "Not found"}}
)

# Pydantic models for API requests/responses

class TagSuggestionRequest(BaseModel):
    """Request model for single tag suggestion"""
    transaction_label: str = Field(min_length=1, max_length=500, description="Transaction label/description")
    amount: Optional[float] = Field(None, description="Transaction amount for context")
    use_web_research: bool = Field(True, description="Enable web research for unknown merchants")

class BatchTagSuggestionRequest(BaseModel):
    """Request model for batch tag suggestions"""
    transactions: List[Dict[str, Any]] = Field(
        min_length=1,
        max_length=100,
        description="List of transactions with id, label, and amount"
    )
    use_web_research: bool = Field(False, description="Enable web research (slower, more accurate)")
    max_concurrent: int = Field(5, ge=1, le=10, description="Max concurrent web requests")

class LearningFeedbackRequest(BaseModel):
    """Request model for learning feedback"""
    transaction_label: str = Field(min_length=1, max_length=500)
    suggested_tag: str = Field(min_length=1, max_length=50)
    actual_tag: str = Field(min_length=1, max_length=50)
    confidence: float = Field(ge=0.0, le=1.0)
    user_comment: Optional[str] = Field(None, max_length=500)

class TagSuggestionResponse(BaseModel):
    """Response model for tag suggestions"""
    suggested_tag: str
    confidence: float
    explanation: str
    alternative_tags: List[str]
    merchant_name: Optional[str] = None
    business_category: Optional[str] = None
    web_research_used: bool = False
    research_quality: str
    amount_context: Optional[str] = None
    pattern_matches: List[str]
    processing_time_ms: int
    data_sources: List[str]
    
    # Legacy compatibility (deprecated)
    expense_type: Optional[str] = None  # For backward compatibility

    class Config:
        schema_extra = {
            "example": {
                "suggested_tag": "streaming",
                "confidence": 0.95,
                "explanation": "Marchand reconnu: Netflix → streaming",
                "alternative_tags": ["divertissement", "abonnement"],
                "merchant_name": "Netflix",
                "business_category": "entertainment",
                "web_research_used": False,
                "research_quality": "pattern_match",
                "processing_time_ms": 2,
                "data_sources": ["quick_patterns"]
            }
        }

class BatchTagSuggestionResponse(BaseModel):
    """Response model for batch tag suggestions"""
    results: Dict[int, TagSuggestionResponse]
    summary: Dict[str, Any]
    processing_time_seconds: float

class ServiceStatsResponse(BaseModel):
    """Response model for service statistics"""
    total_suggestions: int
    web_research_usage_rate: str
    quick_recognition_rate: str
    quick_patterns_count: int
    total_patterns: int
    service_capabilities: Dict[str, bool]
    performance_targets: Dict[str, str]
    service_version: str
    last_updated: str

# API Endpoints

@router.post("/suggest", response_model=TagSuggestionResponse)
async def suggest_tag(
    request: TagSuggestionRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Suggest an intelligent tag for a transaction
    
    Uses pattern matching and optionally web research to suggest the most 
    appropriate tag for a transaction based on its label and amount.
    """
    try:
        service = get_intelligent_tag_service(db)
        
        if request.use_web_research:
            result = await service.suggest_tag_with_research(
                transaction_label=request.transaction_label,
                amount=request.amount
            )
        else:
            result = service.suggest_tag_fast(
                transaction_label=request.transaction_label,
                amount=request.amount
            )
        
        return TagSuggestionResponse(
            suggested_tag=result.suggested_tag,
            confidence=result.confidence,
            explanation=result.explanation,
            alternative_tags=result.alternative_tags,
            merchant_name=result.merchant_name,
            business_category=result.business_category,
            web_research_used=result.web_research_used,
            research_quality=result.research_quality,
            amount_context=result.amount_context,
            pattern_matches=result.pattern_matches,
            processing_time_ms=result.processing_time_ms,
            data_sources=result.data_sources,
            expense_type=None  # Deprecated field
        )
        
    except Exception as e:
        logger.error(f"Tag suggestion failed for '{request.transaction_label}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tag suggestion failed: {str(e)}"
        )

@router.get("/suggest/{transaction_label}", response_model=TagSuggestionResponse)
async def suggest_tag_simple(
    transaction_label: str,
    amount: Optional[float] = Query(None, description="Transaction amount"),
    use_web_research: bool = Query(True, description="Enable web research"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Simple endpoint to suggest tag from URL path
    """
    request = TagSuggestionRequest(
        transaction_label=transaction_label,
        amount=amount,
        use_web_research=use_web_research
    )
    
    return await suggest_tag(request, current_user, db)

@router.post("/suggest-batch", response_model=BatchTagSuggestionResponse)
async def suggest_tags_batch(
    request: BatchTagSuggestionRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Batch tag suggestions for multiple transactions
    
    Efficiently processes multiple transactions. Use web_research=False for
    faster processing with pattern-matching only, or web_research=True for
    slower but more accurate suggestions with web research.
    """
    try:
        start_time = time.time()
        service = get_intelligent_tag_service(db)
        
        # Validate transactions format
        for tx in request.transactions:
            if 'id' not in tx or 'label' not in tx:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each transaction must have 'id' and 'label' fields"
                )
        
        if request.use_web_research:
            results = await service.batch_suggest_tags_with_research(
                transactions=request.transactions,
                max_concurrent=request.max_concurrent
            )
        else:
            results = service.batch_suggest_tags(request.transactions)
        
        processing_time = time.time() - start_time
        
        # Convert results to response format
        response_results = {}
        for tx_id, result in results.items():
            response_results[tx_id] = TagSuggestionResponse(
                suggested_tag=result.suggested_tag,
                confidence=result.confidence,
                explanation=result.explanation,
                alternative_tags=result.alternative_tags,
                merchant_name=result.merchant_name,
                business_category=result.business_category,
                web_research_used=result.web_research_used,
                research_quality=result.research_quality,
                amount_context=result.amount_context,
                pattern_matches=result.pattern_matches,
                processing_time_ms=result.processing_time_ms,
                data_sources=result.data_sources
            )
        
        # Calculate summary statistics
        total_processed = len(results)
        web_research_count = sum(1 for r in results.values() if r.web_research_used)
        high_confidence_count = sum(1 for r in results.values() if r.confidence >= 0.80)
        avg_confidence = sum(r.confidence for r in results.values()) / max(total_processed, 1)
        
        summary = {
            "total_processed": total_processed,
            "web_research_used": web_research_count,
            "high_confidence_suggestions": high_confidence_count,
            "average_confidence": round(avg_confidence, 3),
            "processing_mode": "web_research" if request.use_web_research else "fast_pattern"
        }
        
        return BatchTagSuggestionResponse(
            results=response_results,
            summary=summary,
            processing_time_seconds=round(processing_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Batch tag suggestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch tag suggestion failed: {str(e)}"
        )

@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def record_learning_feedback(
    request: LearningFeedbackRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record user feedback for learning and improvement
    
    When users correct our tag suggestions, this endpoint records the 
    feedback to improve future suggestions.
    """
    try:
        service = get_intelligent_tag_service(db)
        
        service.learn_from_feedback(
            transaction_label=request.transaction_label,
            suggested_tag=request.suggested_tag,
            actual_tag=request.actual_tag,
            confidence=request.confidence
        )
        
        logger.info(
            f"Learning feedback recorded: '{request.transaction_label}' "
            f"suggested={request.suggested_tag} → actual={request.actual_tag} "
            f"(confidence: {request.confidence:.2f})"
        )
        
        return {"message": "Feedback recorded successfully"}
        
    except Exception as e:
        logger.error(f"Recording feedback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record feedback: {str(e)}"
        )

@router.get("/stats", response_model=ServiceStatsResponse)
async def get_service_statistics(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive service performance statistics
    
    Returns metrics about tag suggestion performance, pattern coverage,
    web research usage, and service capabilities.
    """
    try:
        service = get_intelligent_tag_service(db)
        stats = service.get_service_statistics()
        
        return ServiceStatsResponse(
            total_suggestions=stats["total_suggestions"],
            web_research_usage_rate=stats["web_research_usage_rate"],
            quick_recognition_rate=stats["quick_recognition_rate"],
            quick_patterns_count=stats["quick_patterns_count"],
            total_patterns=stats["total_patterns"],
            service_capabilities={
                "web_research_enabled": stats["web_research_enabled"],
                "batch_processing_enabled": stats["batch_processing_enabled"],
                "concurrent_research_enabled": stats["concurrent_research_enabled"],
                "learning_enabled": stats["learning_enabled"]
            },
            performance_targets={
                "precision": stats["target_precision"],
                "response_time_fast": stats["target_response_time_fast"],
                "response_time_research": stats["target_response_time_research"]
            },
            service_version=stats["service_version"],
            last_updated=stats["last_updated"]
        )
        
    except Exception as e:
        logger.error(f"Getting service statistics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )

@router.post("/transactions/{transaction_id}/suggest", response_model=TagSuggestionResponse)
async def suggest_tag_for_transaction(
    transaction_id: int,
    use_web_research: bool = Query(True, description="Enable web research"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Suggest tag for a specific transaction by ID
    
    Retrieves the transaction from the database and suggests an appropriate tag.
    """
    try:
        # Get transaction from database
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found"
            )
        
        # Use the transaction's label and amount for suggestion
        request = TagSuggestionRequest(
            transaction_label=transaction.label or "",
            amount=abs(float(transaction.amount)) if transaction.amount else None,
            use_web_research=use_web_research
        )
        
        return await suggest_tag(request, current_user, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transaction tag suggestion failed for ID {transaction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transaction tag suggestion failed: {str(e)}"
        )

@router.get("/health")
async def health_check(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Health check endpoint for the intelligent tag service
    """
    try:
        service = get_intelligent_tag_service(db)
        stats = service.get_service_statistics()
        
        return {
            "status": "healthy",
            "service": "intelligent_tag_service",
            "version": stats["service_version"],
            "total_patterns": stats["total_patterns"],
            "web_research_enabled": stats["web_research_enabled"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Test endpoint (for development only)
@router.post("/test", response_model=Dict[str, Any])
async def test_service(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test endpoint to verify service functionality with sample data
    """
    test_transactions = [
        {"transaction_label": "NETFLIX SARL 12.99", "amount": 12.99},
        {"transaction_label": "MCDONALDS PARIS 8.50", "amount": 8.50},
        {"transaction_label": "CARREFOUR VILLENEUVE 67.32", "amount": 67.32},
        {"transaction_label": "EDF ENERGIE FACTURE 89.34", "amount": 89.34},
        {"transaction_label": "TOTAL ACCESS PARIS 45.00", "amount": 45.00},
    ]
    
    try:
        service = get_intelligent_tag_service(db)
        results = []
        
        for tx in test_transactions:
            # Test fast suggestion
            fast_result = service.suggest_tag_fast(tx["transaction_label"], tx["amount"])
            
            results.append({
                "transaction": tx["transaction_label"],
                "amount": tx["amount"],
                "suggested_tag": fast_result.suggested_tag,
                "confidence": fast_result.confidence,
                "explanation": fast_result.explanation,
                "processing_time_ms": fast_result.processing_time_ms
            })
        
        stats = service.get_service_statistics()
        
        return {
            "status": "test_completed",
            "test_results": results,
            "service_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Service test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service test failed: {str(e)}"
        )