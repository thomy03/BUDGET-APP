"""
Revolutionary Research API Endpoints for Automatic Transaction Enrichment

This module provides REST API endpoints for the web research system that automatically
identifies merchant types and enriches transaction classification.

ENDPOINTS:
- POST /research/enrich/{transaction_id} - Enrich a specific transaction
- POST /research/batch-enrich - Batch enrich multiple transactions
- GET /research/knowledge-base - View merchant knowledge base
- POST /research/merchant - Research a merchant manually
- DELETE /research/knowledge-base/{merchant_id} - Remove merchant from KB
- PUT /research/knowledge-base/{merchant_id}/verify - Verify merchant info
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from models.database import get_db, Transaction, MerchantKnowledgeBase
from services.web_research_service import WebResearchService, MerchantInfo, get_merchant_from_transaction_label
# Authentication is optional for research endpoints
def get_current_user_optional():
    """Optional authentication dependency - always returns None for now"""
    return None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


# Pydantic models for API

class EnrichTransactionRequest(BaseModel):
    """Request model for transaction enrichment"""
    force_refresh: bool = Field(False, description="Force re-research even if merchant exists in KB")
    include_suggestions: bool = Field(True, description="Include tag and classification suggestions")


class BatchEnrichRequest(BaseModel):
    """Request model for batch enrichment"""
    transaction_ids: List[int] = Field(..., description="List of transaction IDs to enrich")
    force_refresh: bool = Field(False, description="Force re-research for all transactions")
    max_concurrent: int = Field(3, description="Maximum concurrent research operations", ge=1, le=10)


class ManualResearchRequest(BaseModel):
    """Request model for manual merchant research"""
    merchant_name: str = Field(..., min_length=1, max_length=200, description="Merchant name to research")
    city: Optional[str] = Field(None, max_length=100, description="Optional city information")
    amount: Optional[float] = Field(None, description="Optional transaction amount")


class MerchantKnowledgeResponse(BaseModel):
    """Response model for merchant knowledge base entries"""
    id: int
    merchant_name: str
    normalized_name: str
    business_type: Optional[str]
    category: Optional[str]
    sub_category: Optional[str]
    city: Optional[str]
    country: str
    confidence_score: float
    suggested_expense_type: Optional[str]
    suggested_tags: List[str]
    usage_count: int
    accuracy_rating: float
    is_verified: bool
    is_active: bool
    research_date: Optional[datetime]
    last_used: Optional[datetime]
    data_sources: List[str]


class EnrichmentResponse(BaseModel):
    """Response model for enrichment operations"""
    transaction_id: int
    merchant_name: str
    enrichment_successful: bool
    business_type: Optional[str]
    suggested_expense_type: Optional[str]
    suggested_tags: List[str]
    confidence_score: float
    research_duration_ms: int
    was_cached: bool
    error_message: Optional[str] = None


class BatchEnrichmentResponse(BaseModel):
    """Response model for batch enrichment"""
    total_transactions: int
    successful_enrichments: int
    failed_enrichments: int
    cached_results: int
    total_duration_ms: int
    results: List[EnrichmentResponse]


def merchant_info_to_db_model(merchant_info: MerchantInfo, db: Session) -> MerchantKnowledgeBase:
    """Convert MerchantInfo to database model"""
    return MerchantKnowledgeBase(
        merchant_name=merchant_info.merchant_name,
        normalized_name=merchant_info.normalized_name,
        business_type=merchant_info.business_type,
        category=merchant_info.category,
        sub_category=merchant_info.sub_category,
        city=merchant_info.city,
        country=merchant_info.country,
        address=merchant_info.address,
        confidence_score=merchant_info.confidence_score,
        data_sources=json.dumps(merchant_info.data_sources) if merchant_info.data_sources else None,
        research_keywords=",".join(merchant_info.research_keywords) if merchant_info.research_keywords else None,
        suggested_expense_type=merchant_info.suggested_expense_type,
        suggested_tags=",".join(merchant_info.suggested_tags) if merchant_info.suggested_tags else None,
        website_url=merchant_info.website_url,
        phone_number=merchant_info.phone_number,
        description=merchant_info.description,
        research_duration_ms=merchant_info.research_duration_ms,
        search_queries_used=json.dumps(merchant_info.search_queries_used) if merchant_info.search_queries_used else None,
        is_verified=False,
        is_active=True,
        needs_update=False
    )


def db_model_to_response(db_merchant: MerchantKnowledgeBase) -> MerchantKnowledgeResponse:
    """Convert database model to response model"""
    return MerchantKnowledgeResponse(
        id=db_merchant.id,
        merchant_name=db_merchant.merchant_name,
        normalized_name=db_merchant.normalized_name,
        business_type=db_merchant.business_type,
        category=db_merchant.category,
        sub_category=db_merchant.sub_category,
        city=db_merchant.city,
        country=db_merchant.country,
        confidence_score=db_merchant.confidence_score,
        suggested_expense_type=db_merchant.suggested_expense_type,
        suggested_tags=db_merchant.suggested_tags.split(",") if db_merchant.suggested_tags else [],
        usage_count=db_merchant.usage_count,
        accuracy_rating=db_merchant.accuracy_rating,
        is_verified=db_merchant.is_verified,
        is_active=db_merchant.is_active,
        research_date=db_merchant.research_date or datetime.now(),
        last_used=db_merchant.last_used,
        data_sources=json.loads(db_merchant.data_sources) if db_merchant.data_sources else []
    )


async def find_or_research_merchant(
    merchant_name: str, 
    amount: Optional[float],
    force_refresh: bool,
    db: Session
) -> Tuple[MerchantKnowledgeBase, bool]:
    """
    Find merchant in knowledge base or perform new research
    
    Returns:
        tuple: (MerchantKnowledgeBase entry, was_researched_now)
    """
    # Normalize merchant name for lookup
    normalized_name = ""
    async with WebResearchService() as research_service:
        normalized_name = research_service.normalize_merchant_name(merchant_name)
    
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Invalid merchant name")
    
    # Check if merchant exists in knowledge base
    existing_merchant = None
    if not force_refresh:
        existing_merchant = db.query(MerchantKnowledgeBase).filter(
            MerchantKnowledgeBase.normalized_name == normalized_name,
            MerchantKnowledgeBase.is_active == True
        ).first()
    
    if existing_merchant and not force_refresh:
        # Update usage statistics
        existing_merchant.usage_count += 1
        existing_merchant.last_used = datetime.now()
        db.commit()
        db.refresh(existing_merchant)
        return existing_merchant, False
    
    # Perform new research
    async with WebResearchService() as research_service:
        merchant_info = await research_service.research_merchant(merchant_name, amount)
    
    if existing_merchant and force_refresh:
        # Update existing entry
        existing_merchant.business_type = merchant_info.business_type
        existing_merchant.category = merchant_info.category
        existing_merchant.sub_category = merchant_info.sub_category
        existing_merchant.city = merchant_info.city
        existing_merchant.address = merchant_info.address
        existing_merchant.confidence_score = merchant_info.confidence_score
        existing_merchant.data_sources = json.dumps(merchant_info.data_sources) if merchant_info.data_sources else None
        existing_merchant.research_keywords = ",".join(merchant_info.research_keywords) if merchant_info.research_keywords else None
        existing_merchant.suggested_expense_type = merchant_info.suggested_expense_type
        existing_merchant.suggested_tags = ",".join(merchant_info.suggested_tags) if merchant_info.suggested_tags else None
        existing_merchant.website_url = merchant_info.website_url
        existing_merchant.phone_number = merchant_info.phone_number
        existing_merchant.description = merchant_info.description
        existing_merchant.research_duration_ms = merchant_info.research_duration_ms
        existing_merchant.search_queries_used = json.dumps(merchant_info.search_queries_used) if merchant_info.search_queries_used else None
        existing_merchant.last_verified = datetime.now()
        existing_merchant.needs_update = False
        existing_merchant.usage_count += 1
        existing_merchant.last_used = datetime.now()
        
        db.commit()
        db.refresh(existing_merchant)
        return existing_merchant, True
    else:
        # Create new entry
        db_merchant = merchant_info_to_db_model(merchant_info, db)
        db_merchant.usage_count = 1
        db_merchant.last_used = datetime.now()
        
        db.add(db_merchant)
        db.commit()
        db.refresh(db_merchant)
        return db_merchant, True


@router.post("/enrich/{transaction_id}", response_model=EnrichmentResponse)
async def enrich_transaction(
    transaction_id: int,
    request: EnrichTransactionRequest = EnrichTransactionRequest(),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Enrich a specific transaction with web research data
    
    This endpoint performs automatic web research to identify the merchant type
    and provides intelligent suggestions for expense classification and tags.
    """
    # Get transaction
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Extract merchant name from transaction label
    merchant_name = get_merchant_from_transaction_label(transaction.label)
    if not merchant_name:
        raise HTTPException(status_code=400, detail="Cannot extract merchant name from transaction")
    
    try:
        start_time = datetime.now()
        
        # Find or research merchant
        merchant_kb, was_researched = await find_or_research_merchant(
            merchant_name, 
            transaction.amount,
            request.force_refresh,
            db
        )
        
        # Calculate total duration
        total_duration = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Apply suggestions if requested
        if request.include_suggestions and merchant_kb.suggested_expense_type:
            # Update transaction with suggestions (optional)
            if not transaction.expense_type or transaction.expense_type == "VARIABLE":
                transaction.expense_type = merchant_kb.suggested_expense_type
                
            # Add suggested tags
            if merchant_kb.suggested_tags and not transaction.tags:
                transaction.tags = merchant_kb.suggested_tags
                
            db.commit()
        
        return EnrichmentResponse(
            transaction_id=transaction_id,
            merchant_name=merchant_name,
            enrichment_successful=True,
            business_type=merchant_kb.business_type,
            suggested_expense_type=merchant_kb.suggested_expense_type,
            suggested_tags=merchant_kb.suggested_tags.split(",") if merchant_kb.suggested_tags else [],
            confidence_score=merchant_kb.confidence_score,
            research_duration_ms=merchant_kb.research_duration_ms if was_researched else 0,
            was_cached=not was_researched
        )
        
    except Exception as e:
        logger.error(f"Error enriching transaction {transaction_id}: {e}")
        return EnrichmentResponse(
            transaction_id=transaction_id,
            merchant_name=merchant_name,
            enrichment_successful=False,
            business_type=None,
            suggested_expense_type=None,
            suggested_tags=[],
            confidence_score=0.0,
            research_duration_ms=0,
            was_cached=False,
            error_message=str(e)
        )


@router.post("/batch-enrich", response_model=BatchEnrichmentResponse)
async def batch_enrich_transactions(
    request: BatchEnrichRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Enrich multiple transactions in batch with intelligent rate limiting
    
    This endpoint processes multiple transactions efficiently while respecting
    API rate limits and providing detailed progress information.
    """
    start_time = datetime.now()
    results = []
    successful = 0
    failed = 0
    cached = 0
    
    # Validate request
    if len(request.transaction_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 transactions per batch")
    
    # Get all transactions
    transactions = db.query(Transaction).filter(
        Transaction.id.in_(request.transaction_ids)
    ).all()
    
    transaction_dict = {t.id: t for t in transactions}
    
    # Process transactions in controlled batches
    semaphore = asyncio.Semaphore(request.max_concurrent)
    
    async def process_single_transaction(transaction_id: int) -> EnrichmentResponse:
        async with semaphore:
            transaction = transaction_dict.get(transaction_id)
            if not transaction:
                return EnrichmentResponse(
                    transaction_id=transaction_id,
                    merchant_name="",
                    enrichment_successful=False,
                    business_type=None,
                    suggested_expense_type=None,
                    suggested_tags=[],
                    confidence_score=0.0,
                    research_duration_ms=0,
                    was_cached=False,
                    error_message="Transaction not found"
                )
            
            merchant_name = get_merchant_from_transaction_label(transaction.label)
            if not merchant_name:
                return EnrichmentResponse(
                    transaction_id=transaction_id,
                    merchant_name="",
                    enrichment_successful=False,
                    business_type=None,
                    suggested_expense_type=None,
                    suggested_tags=[],
                    confidence_score=0.0,
                    research_duration_ms=0,
                    was_cached=False,
                    error_message="Cannot extract merchant name"
                )
            
            try:
                merchant_kb, was_researched = await find_or_research_merchant(
                    merchant_name,
                    transaction.amount,
                    request.force_refresh,
                    db
                )
                
                return EnrichmentResponse(
                    transaction_id=transaction_id,
                    merchant_name=merchant_name,
                    enrichment_successful=True,
                    business_type=merchant_kb.business_type,
                    suggested_expense_type=merchant_kb.suggested_expense_type,
                    suggested_tags=merchant_kb.suggested_tags.split(",") if merchant_kb.suggested_tags else [],
                    confidence_score=merchant_kb.confidence_score,
                    research_duration_ms=merchant_kb.research_duration_ms if was_researched else 0,
                    was_cached=not was_researched
                )
                
            except Exception as e:
                logger.error(f"Error in batch processing transaction {transaction_id}: {e}")
                return EnrichmentResponse(
                    transaction_id=transaction_id,
                    merchant_name=merchant_name,
                    enrichment_successful=False,
                    business_type=None,
                    suggested_expense_type=None,
                    suggested_tags=[],
                    confidence_score=0.0,
                    research_duration_ms=0,
                    was_cached=False,
                    error_message=str(e)
                )
    
    # Process all transactions
    tasks = [process_single_transaction(tid) for tid in request.transaction_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Count results
    for result in results:
        if isinstance(result, EnrichmentResponse):
            if result.enrichment_successful:
                successful += 1
                if result.was_cached:
                    cached += 1
            else:
                failed += 1
        else:
            failed += 1
            logger.error(f"Batch processing exception: {result}")
    
    total_duration = int((datetime.now() - start_time).total_seconds() * 1000)
    
    return BatchEnrichmentResponse(
        total_transactions=len(request.transaction_ids),
        successful_enrichments=successful,
        failed_enrichments=failed,
        cached_results=cached,
        total_duration_ms=total_duration,
        results=[r for r in results if isinstance(r, EnrichmentResponse)]
    )


@router.post("/merchant", response_model=MerchantKnowledgeResponse)
async def research_merchant_manually(
    request: ManualResearchRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Manually research a merchant and add to knowledge base
    
    This endpoint allows manual research of merchants for testing
    or when automatic enrichment needs manual verification.
    """
    try:
        merchant_kb, was_researched = await find_or_research_merchant(
            request.merchant_name,
            request.amount,
            force_refresh=True,  # Always research for manual requests
            db=db
        )
        
        return db_model_to_response(merchant_kb)
        
    except Exception as e:
        logger.error(f"Error in manual merchant research: {e}")
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@router.get("/knowledge-base", response_model=List[MerchantKnowledgeResponse])
async def get_knowledge_base(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    business_type: Optional[str] = Query(None, description="Filter by business type"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence score"),
    verified_only: bool = Query(False, description="Show only verified merchants"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Get merchant knowledge base with filtering options
    
    This endpoint provides access to the accumulated merchant knowledge
    with various filtering and pagination options.
    """
    query = db.query(MerchantKnowledgeBase).filter(
        MerchantKnowledgeBase.is_active == True
    )
    
    # Apply filters
    if business_type:
        query = query.filter(MerchantKnowledgeBase.business_type == business_type)
    
    if min_confidence > 0:
        query = query.filter(MerchantKnowledgeBase.confidence_score >= min_confidence)
    
    if verified_only:
        query = query.filter(MerchantKnowledgeBase.is_verified == True)
    
    # Order by usage and confidence
    query = query.order_by(
        MerchantKnowledgeBase.usage_count.desc(),
        MerchantKnowledgeBase.confidence_score.desc()
    )
    
    # Apply pagination
    merchants = query.offset(offset).limit(limit).all()
    
    return [db_model_to_response(merchant) for merchant in merchants]


@router.put("/knowledge-base/{merchant_id}/verify", response_model=MerchantKnowledgeResponse)
async def verify_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Verify a merchant entry in the knowledge base
    
    This endpoint allows manual verification of automatically researched merchants.
    """
    merchant = db.query(MerchantKnowledgeBase).filter(
        MerchantKnowledgeBase.id == merchant_id,
        MerchantKnowledgeBase.is_active == True
    ).first()
    
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    merchant.is_verified = True
    merchant.last_verified = datetime.now()
    merchant.accuracy_rating = 1.0  # Perfect rating for manually verified
    
    db.commit()
    db.refresh(merchant)
    
    return db_model_to_response(merchant)


@router.delete("/knowledge-base/{merchant_id}")
async def delete_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Remove a merchant from the knowledge base
    
    This endpoint allows removal of incorrect or outdated merchant information.
    """
    merchant = db.query(MerchantKnowledgeBase).filter(
        MerchantKnowledgeBase.id == merchant_id
    ).first()
    
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    # Soft delete - mark as inactive
    merchant.is_active = False
    
    db.commit()
    
    return {"message": "Merchant removed from knowledge base"}


@router.get("/stats")
async def get_research_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Get statistics about the web research system
    
    This endpoint provides insights into the research system performance
    and knowledge base quality.
    """
    # Total merchants in KB
    total_merchants = db.query(MerchantKnowledgeBase).filter(
        MerchantKnowledgeBase.is_active == True
    ).count()
    
    # Verified merchants
    verified_merchants = db.query(MerchantKnowledgeBase).filter(
        MerchantKnowledgeBase.is_active == True,
        MerchantKnowledgeBase.is_verified == True
    ).count()
    
    # High confidence merchants (>0.7)
    high_confidence = db.query(MerchantKnowledgeBase).filter(
        MerchantKnowledgeBase.is_active == True,
        MerchantKnowledgeBase.confidence_score > 0.7
    ).count()
    
    # Business type distribution (simplified)
    all_merchants = db.query(MerchantKnowledgeBase).filter(
        MerchantKnowledgeBase.is_active == True,
        MerchantKnowledgeBase.business_type.isnot(None)
    ).all()
    
    business_type_counts = {}
    for merchant in all_merchants:
        if merchant.business_type in business_type_counts:
            business_type_counts[merchant.business_type] += 1
        else:
            business_type_counts[merchant.business_type] = 1
    
    # Most used merchants
    top_merchants = db.query(MerchantKnowledgeBase).filter(
        MerchantKnowledgeBase.is_active == True
    ).order_by(MerchantKnowledgeBase.usage_count.desc()).limit(10).all()
    
    return {
        "total_merchants": total_merchants,
        "verified_merchants": verified_merchants,
        "high_confidence_merchants": high_confidence,
        "verification_rate": verified_merchants / total_merchants if total_merchants > 0 else 0,
        "high_confidence_rate": high_confidence / total_merchants if total_merchants > 0 else 0,
        "business_type_distribution": business_type_counts,
        "top_merchants": [
            {
                "name": m.merchant_name,
                "usage_count": m.usage_count,
                "confidence": m.confidence_score,
                "business_type": m.business_type
            }
            for m in top_merchants
        ]
    }