"""
Unified Tagging Router - Budget Famille v4.2
Consolidated endpoints for ML-based tag suggestions and classification

This router consolidates functionality from:
- ml_tagging.py (/api/ml-tagging/*)
- intelligent_tags.py (/api/intelligent-tags/*)
- classification.py (tag suggestion endpoints)
- auto_tagging.py (/api/auto-tag/*)

Maintains backward-compatible aliases for legacy endpoints.

Author: Claude Code - Backend API Architect
Version: 4.2.0 (Architecture Consolidation)
"""

import logging
import time
from datetime import datetime
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, BackgroundTasks
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from auth import get_current_user
from models.database import get_db, Transaction

logger = logging.getLogger(__name__)

# =============================================================================
# UNIFIED PYDANTIC MODELS
# =============================================================================

class UnifiedTagSuggestionRequest(BaseModel):
    """Unified request model for tag suggestions"""
    transaction_label: str = Field(..., min_length=1, max_length=500, description="Transaction label/description")
    amount: Optional[float] = Field(None, description="Transaction amount for context")
    date: Optional[datetime] = Field(None, description="Transaction date")
    use_web_research: bool = Field(False, description="Enable web research for unknown merchants")
    include_alternatives: bool = Field(True, description="Include alternative tag suggestions")
    include_expense_type: bool = Field(False, description="Include FIXED/VARIABLE classification")

    @validator('transaction_label')
    def validate_label(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Transaction label cannot be empty")
        return v.strip()


class BatchTagSuggestionRequest(BaseModel):
    """Request for batch tag suggestions"""
    transactions: List[Dict[str, Any]] = Field(..., min_length=1, max_length=100, description="List of transactions with id, label, amount")
    use_web_research: bool = Field(False, description="Enable web research (slower)")
    detect_patterns: bool = Field(True, description="Detect recurring patterns")
    max_concurrent: int = Field(5, ge=1, le=10, description="Max concurrent requests")

    @validator('transactions')
    def validate_transactions(cls, v):
        if not v:
            raise ValueError("Transactions list cannot be empty")
        for tx in v:
            if 'id' not in tx or 'label' not in tx:
                raise ValueError("Each transaction must have 'id' and 'label' fields")
        return v


class UserFeedbackRequest(BaseModel):
    """User feedback for continuous learning"""
    transaction_label: str = Field(..., min_length=1, max_length=500)
    suggested_tag: str = Field(..., min_length=1, max_length=50)
    actual_tag: str = Field(..., min_length=1, max_length=50)
    was_accepted: bool = Field(..., description="Whether suggestion was accepted")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    user_comment: Optional[str] = Field(None, max_length=500)


class UnifiedTagSuggestionResponse(BaseModel):
    """Unified response model for tag suggestions"""
    suggested_tag: str
    confidence: float
    should_auto_apply: bool
    explanation: str
    alternatives: List[str] = []

    # Merchant info
    merchant_name: Optional[str] = None
    merchant_category: Optional[str] = None

    # Classification
    expense_type: Optional[str] = None  # FIXED or VARIABLE

    # Metadata
    confidence_breakdown: Dict[str, float] = {}
    data_sources: List[str] = []
    web_research_used: bool = False
    processing_time_ms: int = 0
    pattern_matches: List[str] = []

    class Config:
        schema_extra = {
            "example": {
                "suggested_tag": "courses",
                "confidence": 0.92,
                "should_auto_apply": True,
                "explanation": "Marchand reconnu: CARREFOUR → courses",
                "alternatives": ["alimentation", "supermarche"],
                "merchant_name": "Carrefour",
                "merchant_category": "grocery",
                "expense_type": "VARIABLE",
                "confidence_breakdown": {"pattern": 0.95, "learning": 0.10},
                "data_sources": ["ml_patterns", "feedback_learning"],
                "web_research_used": False,
                "processing_time_ms": 15,
                "pattern_matches": ["carrefour"]
            }
        }


class BatchSuggestionResponse(BaseModel):
    """Response for batch suggestions"""
    results: Dict[str, UnifiedTagSuggestionResponse]
    summary: Dict[str, Any]
    processing_time_seconds: float


class ServiceStatisticsResponse(BaseModel):
    """Service statistics response"""
    total_suggestions: int
    patterns_count: int
    quick_recognition_rate: str
    average_confidence: float
    service_version: str
    last_updated: str
    capabilities: Dict[str, bool]


# =============================================================================
# MAIN ROUTER - /api/tags
# =============================================================================

router = APIRouter(
    prefix="/api/tags",
    tags=["tags-unified"],
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)


def _get_unified_service(db: Session):
    """Get the unified ML tagging service"""
    try:
        from services.unified_ml_tagging_service import get_unified_ml_tagging_service
        return get_unified_ml_tagging_service(db)
    except ImportError:
        # Fallback to intelligent tag service
        from services.intelligent_tag_service import get_intelligent_tag_service
        return get_intelligent_tag_service(db)


def _convert_to_unified_response(result: Any, start_time: float) -> UnifiedTagSuggestionResponse:
    """Convert various service results to unified response format"""
    processing_time = int((time.time() - start_time) * 1000)

    # Handle different result types
    if hasattr(result, 'to_dict'):
        data = result.to_dict()
        return UnifiedTagSuggestionResponse(
            suggested_tag=data.get('tag', data.get('suggested_tag', 'divers')),
            confidence=data.get('confidence', 0.5),
            should_auto_apply=data.get('should_auto_apply', data.get('confidence', 0) >= 0.80),
            explanation=data.get('explanation', ''),
            alternatives=data.get('alternatives', data.get('alternative_tags', [])),
            merchant_name=data.get('merchant', {}).get('name') if isinstance(data.get('merchant'), dict) else data.get('merchant_name'),
            merchant_category=data.get('merchant', {}).get('category') if isinstance(data.get('merchant'), dict) else data.get('business_category'),
            expense_type=data.get('expense_type'),
            confidence_breakdown=data.get('confidence_breakdown', {}),
            data_sources=data.get('metadata', {}).get('sources', data.get('data_sources', [])),
            web_research_used=data.get('metadata', {}).get('web_research', data.get('web_research_used', False)),
            processing_time_ms=processing_time,
            pattern_matches=data.get('pattern_matches', [])
        )
    elif hasattr(result, 'suggested_tag'):
        # IntelligentTagResult format
        return UnifiedTagSuggestionResponse(
            suggested_tag=result.suggested_tag,
            confidence=result.confidence,
            should_auto_apply=result.confidence >= 0.80,
            explanation=getattr(result, 'explanation', ''),
            alternatives=getattr(result, 'alternative_tags', []),
            merchant_name=getattr(result, 'merchant_name', None),
            merchant_category=getattr(result, 'business_category', None),
            expense_type=getattr(result, 'expense_type', None),
            confidence_breakdown={},
            data_sources=getattr(result, 'data_sources', []),
            web_research_used=getattr(result, 'web_research_used', False),
            processing_time_ms=processing_time,
            pattern_matches=getattr(result, 'pattern_matches', [])
        )
    else:
        # Fallback for dict results
        return UnifiedTagSuggestionResponse(
            suggested_tag=result.get('suggested_tag', result.get('tag', 'divers')),
            confidence=result.get('confidence', 0.5),
            should_auto_apply=result.get('confidence', 0) >= 0.80,
            explanation=result.get('explanation', ''),
            alternatives=result.get('alternatives', result.get('alternative_tags', [])),
            merchant_name=result.get('merchant_name'),
            merchant_category=result.get('merchant_category', result.get('business_category')),
            expense_type=result.get('expense_type'),
            confidence_breakdown=result.get('confidence_breakdown', {}),
            data_sources=result.get('data_sources', []),
            web_research_used=result.get('web_research_used', False),
            processing_time_ms=processing_time,
            pattern_matches=result.get('pattern_matches', [])
        )


# =============================================================================
# MAIN ENDPOINTS
# =============================================================================

@router.post("/suggest", response_model=UnifiedTagSuggestionResponse)
async def suggest_tag(
    request: UnifiedTagSuggestionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unified Tag Suggestion Endpoint

    Get an intelligent tag suggestion for a transaction using ML pattern matching
    and optional web research for unknown merchants.

    Features:
    - Multi-factor confidence scoring
    - Pattern-based quick recognition
    - Optional web research for unknown merchants
    - Continuous learning from feedback
    - FIXED/VARIABLE classification (optional)
    """
    start_time = time.time()

    try:
        service = _get_unified_service(db)

        # Use appropriate method based on web research flag
        if request.use_web_research:
            if hasattr(service, 'suggest_tag_unified'):
                result = await service.suggest_tag_unified(
                    transaction_label=request.transaction_label,
                    amount=request.amount,
                    transaction_date=request.date,
                    use_web_research=True
                )
            elif hasattr(service, 'suggest_tag_with_research'):
                result = await service.suggest_tag_with_research(
                    transaction_label=request.transaction_label,
                    amount=request.amount
                )
            else:
                result = service.suggest_tag_fast(request.transaction_label, request.amount)
        else:
            if hasattr(service, 'suggest_tag_unified'):
                result = await service.suggest_tag_unified(
                    transaction_label=request.transaction_label,
                    amount=request.amount,
                    transaction_date=request.date,
                    use_web_research=False
                )
            elif hasattr(service, 'suggest_tag_fast'):
                result = service.suggest_tag_fast(request.transaction_label, request.amount)
            else:
                result = await service.suggest_tag_unified(
                    transaction_label=request.transaction_label,
                    amount=request.amount,
                    use_web_research=False
                )

        response = _convert_to_unified_response(result, start_time)

        # Add expense type classification if requested
        if request.include_expense_type and not response.expense_type:
            try:
                from services.expense_classification import get_expense_classification_service
                classifier = get_expense_classification_service(db)
                classification = classifier.classify_tag(response.suggested_tag)
                response.expense_type = classification.expense_type
            except Exception as e:
                logger.warning(f"Could not add expense type: {e}")

        return response

    except Exception as e:
        logger.error(f"Tag suggestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tag suggestion failed: {str(e)}"
        )


@router.post("/suggest-batch", response_model=BatchSuggestionResponse)
async def suggest_tags_batch(
    request: BatchTagSuggestionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Batch Tag Suggestions

    Efficiently process multiple transactions for tag suggestions.
    Optimized for bulk operations with pattern detection.
    """
    start_time = time.time()

    try:
        service = _get_unified_service(db)
        results = {}

        for tx in request.transactions:
            tx_start = time.time()
            tx_id = tx['id']
            label = tx['label']
            amount = tx.get('amount')

            try:
                if hasattr(service, 'suggest_tag_unified'):
                    result = await service.suggest_tag_unified(
                        transaction_label=label,
                        amount=amount,
                        use_web_research=request.use_web_research
                    )
                elif hasattr(service, 'suggest_tag_fast'):
                    result = service.suggest_tag_fast(label, amount)
                else:
                    result = {'suggested_tag': 'divers', 'confidence': 0.3}

                results[str(tx_id)] = _convert_to_unified_response(result, tx_start)
            except Exception as e:
                logger.warning(f"Failed to process transaction {tx_id}: {e}")
                results[str(tx_id)] = UnifiedTagSuggestionResponse(
                    suggested_tag='divers',
                    confidence=0.0,
                    should_auto_apply=False,
                    explanation=f"Processing error: {str(e)}",
                    processing_time_ms=int((time.time() - tx_start) * 1000)
                )

        # Calculate summary
        total = len(results)
        high_confidence = sum(1 for r in results.values() if r.confidence >= 0.80)
        avg_confidence = sum(r.confidence for r in results.values()) / max(total, 1)

        processing_time = time.time() - start_time

        return BatchSuggestionResponse(
            results=results,
            summary={
                "total_processed": total,
                "high_confidence_count": high_confidence,
                "average_confidence": round(avg_confidence, 3),
                "web_research_used": request.use_web_research,
                "patterns_detected": request.detect_patterns
            },
            processing_time_seconds=round(processing_time, 2)
        )

    except Exception as e:
        logger.error(f"Batch suggestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch suggestion failed: {str(e)}"
        )


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def record_feedback(
    request: UserFeedbackRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record User Feedback

    Captures user corrections to improve ML model accuracy through
    continuous learning. Feedback is processed in background.
    """
    try:
        service = _get_unified_service(db)

        # Process feedback in background
        if hasattr(service, 'learn_from_feedback'):
            background_tasks.add_task(
                service.learn_from_feedback,
                transaction_label=request.transaction_label,
                suggested_tag=request.suggested_tag,
                actual_tag=request.actual_tag,
                was_accepted=request.was_accepted
            )

        logger.info(
            f"Feedback recorded: '{request.transaction_label[:30]}...' "
            f"suggested={request.suggested_tag} → actual={request.actual_tag} "
            f"(accepted: {request.was_accepted})"
        )

        return {
            "status": "success",
            "message": "Feedback recorded for learning",
            "feedback": {
                "transaction": request.transaction_label[:50],
                "correction": f"{request.suggested_tag} → {request.actual_tag}",
                "accepted": request.was_accepted
            }
        }

    except Exception as e:
        logger.error(f"Feedback recording failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feedback recording failed: {str(e)}"
        )


@router.get("/statistics", response_model=ServiceStatisticsResponse)
async def get_statistics(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Service Statistics

    Returns performance metrics, pattern coverage, and service capabilities.
    """
    try:
        service = _get_unified_service(db)

        if hasattr(service, 'get_statistics'):
            stats = service.get_statistics()
        elif hasattr(service, 'get_service_statistics'):
            stats = service.get_service_statistics()
        else:
            stats = {}

        return ServiceStatisticsResponse(
            total_suggestions=stats.get('total_suggestions', 0),
            patterns_count=stats.get('total_patterns', stats.get('quick_patterns_count', 0)),
            quick_recognition_rate=stats.get('quick_recognition_rate', 'N/A'),
            average_confidence=stats.get('average_confidence', 0.0),
            service_version=stats.get('service_version', '4.2.0'),
            last_updated=stats.get('last_updated', datetime.now().isoformat()),
            capabilities={
                "web_research": stats.get('web_research_enabled', True),
                "batch_processing": True,
                "feedback_learning": stats.get('learning_enabled', True),
                "pattern_detection": True
            }
        )

    except Exception as e:
        logger.error(f"Statistics retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Statistics retrieval failed: {str(e)}"
        )


@router.get("/confidence-thresholds")
async def get_confidence_thresholds():
    """
    Get Confidence Thresholds

    Returns the thresholds used for auto-tagging decisions.
    """
    return {
        "thresholds": {
            "auto_apply": {
                "value": 0.80,
                "description": "Minimum confidence for automatic tag application"
            },
            "suggest": {
                "value": 0.60,
                "description": "Minimum confidence for tag suggestions"
            },
            "low": {
                "value": 0.50,
                "description": "Below this, suggestions are not reliable"
            }
        },
        "recommendation": "Tags with confidence >= 80% can be safely auto-applied"
    }


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Service Health Check

    Verifies service availability and returns basic status.
    """
    try:
        service = _get_unified_service(db)

        return {
            "status": "healthy",
            "service": "unified-tagging",
            "version": "4.2.0",
            "timestamp": datetime.now().isoformat(),
            "endpoints": {
                "suggest": "/api/tags/suggest",
                "batch": "/api/tags/suggest-batch",
                "feedback": "/api/tags/feedback",
                "statistics": "/api/tags/statistics"
            }
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# These endpoints maintain compatibility with existing frontend code
# =============================================================================

# Alias for /api/ml-tagging/suggest
@router.post("/ml/suggest", response_model=UnifiedTagSuggestionResponse, include_in_schema=False)
async def ml_tagging_suggest_alias(
    request: UnifiedTagSuggestionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Backward compatibility alias for /api/ml-tagging/suggest"""
    return await suggest_tag(request, current_user, db)


# Alias for /api/intelligent-tags/suggest
@router.post("/intelligent/suggest", response_model=UnifiedTagSuggestionResponse, include_in_schema=False)
async def intelligent_tags_suggest_alias(
    request: UnifiedTagSuggestionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Backward compatibility alias for /api/intelligent-tags/suggest"""
    # Force web research for intelligent tags compatibility
    request.use_web_research = True
    return await suggest_tag(request, current_user, db)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'router',
    'UnifiedTagSuggestionRequest',
    'UnifiedTagSuggestionResponse',
    'BatchTagSuggestionRequest',
    'BatchSuggestionResponse',
    'UserFeedbackRequest',
    'ServiceStatisticsResponse'
]
