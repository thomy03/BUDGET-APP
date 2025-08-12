"""
ML Tagging API Router
Production-ready endpoints for ML-based transaction tagging

This router provides:
1. Single transaction tag suggestion with confidence scoring
2. Batch tag suggestions with pattern detection
3. User feedback processing for continuous learning
4. Recurring pattern detection for fixed expenses
5. Service statistics and performance metrics

Author: Claude Code - ML Operations Engineer
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator

from models.database import get_db, Transaction
from services.unified_ml_tagging_service import (
    UnifiedMLTaggingService,
    UnifiedTagSuggestion,
    get_unified_ml_tagging_service
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ml-tagging",
    tags=["ML Tagging"],
    responses={404: {"description": "Not found"}}
)


# Request/Response Models

class TagSuggestionRequest(BaseModel):
    """Request for single tag suggestion"""
    transaction_label: str = Field(..., description="Transaction description/label")
    amount: Optional[float] = Field(None, description="Transaction amount")
    date: Optional[datetime] = Field(None, description="Transaction date")
    use_web_research: bool = Field(True, description="Enable web research for unknown merchants")
    include_history: bool = Field(False, description="Include transaction history for pattern detection")
    
    @validator('transaction_label')
    def validate_label(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Transaction label cannot be empty")
        return v.strip()


class BatchTagRequest(BaseModel):
    """Request for batch tag suggestions"""
    transactions: List[Dict[str, Any]] = Field(..., description="List of transactions")
    use_web_research: bool = Field(False, description="Enable web research (slower)")
    detect_patterns: bool = Field(True, description="Detect recurring patterns")
    
    @validator('transactions')
    def validate_transactions(cls, v):
        if not v:
            raise ValueError("Transactions list cannot be empty")
        if len(v) > 100:
            raise ValueError("Maximum 100 transactions per batch")
        return v


class UserFeedbackRequest(BaseModel):
    """User feedback for learning"""
    transaction_label: str = Field(..., description="Original transaction label")
    suggested_tag: str = Field(..., description="Tag that was suggested")
    actual_tag: str = Field(..., description="Tag selected by user")
    was_accepted: bool = Field(..., description="Whether suggestion was accepted")


class TagSuggestionResponse(BaseModel):
    """Response with tag suggestion and confidence"""
    tag: str
    confidence: float
    should_auto_apply: bool
    expense_type: str
    explanation: str
    alternatives: List[str]
    merchant: Dict[str, Optional[str]]
    confidence_breakdown: Dict[str, float]
    metadata: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "tag": "streaming",
                "confidence": 0.95,
                "should_auto_apply": True,
                "expense_type": "FIXED",
                "explanation": "Haute confiance (95%) - Marchand: NETFLIX",
                "alternatives": ["divertissement", "abonnement"],
                "merchant": {
                    "name": "NETFLIX SARL",
                    "category": "entertainment",
                    "business_type": "streaming"
                },
                "confidence_breakdown": {
                    "pattern": 0.98,
                    "web": 0.0,
                    "learning": 0.15,
                    "context": 0.10
                },
                "metadata": {
                    "sources": ["ml_patterns"],
                    "web_research": False,
                    "cached": False,
                    "processing_ms": 45,
                    "recurring": True
                }
            }
        }


# API Endpoints

@router.post("/suggest", response_model=TagSuggestionResponse)
async def suggest_tag(
    request: TagSuggestionRequest,
    db: Session = Depends(get_db)
):
    """
    Get ML-based tag suggestion for a single transaction
    
    Features:
    - Multi-factor confidence scoring
    - Web research for unknown merchants (optional)
    - Pattern detection from history (optional)
    - Fixed vs Variable expense classification
    """
    try:
        service = get_unified_ml_tagging_service(db)
        
        # Get transaction history if requested
        transaction_history = None
        if request.include_history and request.transaction_label:
            # Extract merchant name for history lookup
            from services.ml_tagging_engine import MLTaggingEngine
            ml_engine = MLTaggingEngine(db)
            merchant_clean = ml_engine._clean_merchant_name(request.transaction_label)
            
            if merchant_clean:
                # Find similar transactions
                similar_txs = db.query(Transaction).filter(
                    Transaction.label.ilike(f"%{merchant_clean[:10]}%")
                ).limit(10).all()
                
                if similar_txs:
                    transaction_history = [
                        {
                            'label': tx.label,
                            'amount': tx.amount,
                            'date': tx.date
                        }
                        for tx in similar_txs
                    ]
        
        # Get suggestion
        result = await service.suggest_tag_unified(
            transaction_label=request.transaction_label,
            amount=request.amount,
            transaction_date=request.date,
            transaction_history=transaction_history,
            use_web_research=request.use_web_research
        )
        
        # Convert to response format
        return TagSuggestionResponse(**result.to_dict())
        
    except Exception as e:
        logger.error(f"Error in tag suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-suggest")
async def batch_suggest_tags(
    request: BatchTagRequest,
    db: Session = Depends(get_db)
):
    """
    Get ML-based tag suggestions for multiple transactions
    
    Features:
    - Batch processing for efficiency
    - Recurring pattern detection
    - Optional web research
    - Optimized for performance
    """
    try:
        service = get_unified_ml_tagging_service(db)
        
        # Process batch
        results = await service.batch_suggest_tags(
            transactions=request.transactions,
            use_web_research=request.use_web_research,
            detect_patterns=request.detect_patterns
        )
        
        # Convert results to response format
        response = {}
        for tx_id, suggestion in results.items():
            response[tx_id] = suggestion.to_dict()
        
        return {
            "status": "success",
            "transactions_processed": len(results),
            "results": response
        }
        
    except Exception as e:
        logger.error(f"Error in batch tag suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def process_user_feedback(
    request: UserFeedbackRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Process user feedback to improve ML model
    
    The system learns from:
    - Accepted suggestions (reinforcement)
    - Corrections (pattern updates)
    - New merchant-tag associations
    """
    try:
        service = get_unified_ml_tagging_service(db)
        
        # Process feedback in background for better performance
        background_tasks.add_task(
            service.learn_from_feedback,
            transaction_label=request.transaction_label,
            suggested_tag=request.suggested_tag,
            actual_tag=request.actual_tag,
            was_accepted=request.was_accepted
        )
        
        return {
            "status": "success",
            "message": "Feedback processed for learning",
            "feedback": {
                "transaction": request.transaction_label,
                "correction": f"{request.suggested_tag} -> {request.actual_tag}",
                "accepted": request.was_accepted
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing user feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detect-recurring")
async def detect_recurring_patterns(
    days: int = 90,
    db: Session = Depends(get_db)
):
    """
    Detect recurring payment patterns for fixed expense identification
    
    Analyzes transaction history to find:
    - Monthly subscriptions
    - Quarterly payments
    - Annual fees
    - Other recurring patterns
    """
    try:
        service = get_unified_ml_tagging_service(db)
        
        # Get recent transactions
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        transactions = db.query(Transaction).filter(
            Transaction.date >= cutoff_date
        ).all()
        
        if not transactions:
            return {
                "status": "success",
                "message": "No transactions found in the specified period",
                "patterns": []
            }
        
        # Convert to dict format
        tx_data = [
            {
                'label': tx.label,
                'amount': tx.amount,
                'date': tx.date
            }
            for tx in transactions
        ]
        
        # Detect patterns
        from services.ml_tagging_engine import MLTaggingEngine
        ml_engine = MLTaggingEngine(db)
        patterns = ml_engine.detect_recurring_patterns(tx_data)
        
        # Format response
        recurring_expenses = []
        for merchant, pattern in patterns.items():
            if pattern.get('is_fixed'):
                recurring_expenses.append({
                    'merchant': merchant,
                    'frequency': pattern['frequency'],
                    'average_amount': round(pattern['average_amount'], 2),
                    'consistency_score': round(pattern['consistency_score'], 2),
                    'next_expected_date': pattern['next_expected_date'],
                    'transaction_count': pattern['transaction_count']
                })
        
        return {
            "status": "success",
            "period_days": days,
            "patterns_found": len(recurring_expenses),
            "recurring_expenses": recurring_expenses
        }
        
    except Exception as e:
        logger.error(f"Error detecting recurring patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_ml_statistics(db: Session = Depends(get_db)):
    """
    Get ML tagging service statistics and performance metrics
    
    Returns:
    - Pattern database size
    - Accuracy metrics
    - Performance statistics
    - Learning progress
    """
    try:
        service = get_unified_ml_tagging_service(db)
        stats = service.get_statistics()
        
        return {
            "status": "success",
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/confidence-thresholds")
async def get_confidence_thresholds():
    """
    Get current confidence thresholds for auto-tagging
    
    Returns the thresholds used for:
    - Auto-apply (high confidence)
    - Suggestions (medium confidence)
    - No suggestion (low confidence)
    """
    return {
        "thresholds": {
            "auto_apply": {
                "value": 0.80,
                "description": "Minimum confidence for automatic tag application"
            },
            "medium_confidence": {
                "value": 0.60,
                "description": "Minimum confidence for tag suggestions"
            },
            "low_confidence": {
                "value": 0.50,
                "description": "Below this threshold, no tags are suggested"
            }
        },
        "recommendation": "Tags with confidence >= 80% can be safely auto-applied"
    }


@router.post("/test")
async def test_ml_tagging(db: Session = Depends(get_db)):
    """
    Test endpoint for ML tagging with sample transactions
    
    Useful for:
    - Verifying service functionality
    - Testing accuracy
    - Performance benchmarking
    """
    test_transactions = [
        {"label": "NETFLIX SARL 12.99", "amount": 12.99},
        {"label": "CARREFOUR MARKET", "amount": 67.45},
        {"label": "MCDONALDS PARIS", "amount": 15.50},
        {"label": "EDF ENERGIE", "amount": 89.00},
        {"label": "UNKNOWN SHOP XYZ", "amount": 25.00}
    ]
    
    service = get_unified_ml_tagging_service(db)
    results = []
    
    for tx in test_transactions:
        suggestion = await service.suggest_tag_unified(
            transaction_label=tx["label"],
            amount=tx["amount"],
            use_web_research=False
        )
        
        results.append({
            "transaction": tx["label"],
            "amount": tx["amount"],
            "suggested_tag": suggestion.tag,
            "confidence": round(suggestion.confidence, 2),
            "expense_type": suggestion.expense_type,
            "auto_apply": suggestion.should_auto_apply
        })
    
    return {
        "status": "success",
        "test_results": results,
        "summary": {
            "total_tested": len(results),
            "high_confidence": sum(1 for r in results if r["confidence"] >= 0.80),
            "medium_confidence": sum(1 for r in results if 0.60 <= r["confidence"] < 0.80),
            "low_confidence": sum(1 for r in results if r["confidence"] < 0.60)
        }
    }


# Export router
__all__ = ['router']