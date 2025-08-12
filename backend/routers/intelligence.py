"""
Intelligence API Router

This router provides endpoints for the dynamic knowledge base system,
including merchant intelligence, web research, and learning capabilities.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from models.database import (
    get_db, MerchantKnowledgeBase, ResearchCache, 
    Transaction, LabelTagMapping
)
from intelligence_system import (
    get_intelligence_engine, get_web_research_engine, 
    get_intelligence_analytics, KnowledgeScorer
)
from web_research_engine import create_web_researcher, research_unknown_merchants
from models.schemas import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


# Schema Models for API responses

class MerchantIntelligenceResponse(BaseResponse):
    """Response model for merchant intelligence data"""
    merchant: Dict[str, Any]
    confidence_score: float
    suggestions: Dict[str, Any]
    patterns: List[str]
    last_updated: str


class IntelligenceMetricsResponse(BaseResponse):
    """Response model for intelligence metrics"""
    metrics: Dict[str, Any]
    top_performers: List[Dict[str, Any]]
    needs_attention: Dict[str, Any]
    learning_efficiency: Dict[str, Any]


class ResearchResultsResponse(BaseResponse):
    """Response model for research results"""
    search_term: str
    results: Dict[str, Any]
    confidence: float
    cached: bool
    sources: List[str]


# Core Intelligence Endpoints

@router.get("/merchants/{merchant_name}", response_model=MerchantIntelligenceResponse)
async def get_merchant_intelligence(
    merchant_name: str,
    db: Session = Depends(get_db)
):
    """Get intelligence data for a specific merchant"""
    try:
        engine = get_intelligence_engine(db)
        scorer = KnowledgeScorer()
        
        # Normalize merchant name for search
        normalized_name = scorer.normalize_merchant_name(merchant_name)
        
        # Find merchant in knowledge base
        merchant = db.query(MerchantKnowledgeBase).filter(
            or_(
                MerchantKnowledgeBase.merchant_name.ilike(f"%{merchant_name}%"),
                MerchantKnowledgeBase.normalized_name.ilike(f"%{normalized_name}%")
            )
        ).first()
        
        if not merchant:
            # Create new merchant entry for learning
            merchant = engine.get_or_create_merchant(merchant_name)
        
        # Build response data
        merchant_data = {
            "id": merchant.id,
            "merchant_name": merchant.merchant_name,
            "normalized_name": merchant.normalized_name,
            "business_type": merchant.business_type,
            "category": merchant.category,
            "sub_category": merchant.sub_category,
            "expense_type": merchant.expense_type,
            "city": merchant.city,
            "country": merchant.country,
            "address": merchant.address,
            "website_url": merchant.website_url,
            "phone_number": merchant.phone_number,
            "description": merchant.description,
            "usage_count": merchant.usage_count,
            "accuracy_rating": merchant.accuracy_rating,
            "success_rate": merchant.success_rate,
            "is_verified": merchant.is_verified,
            "is_validated": merchant.is_validated,
            "needs_review": merchant.needs_review
        }
        
        # Parse data sources
        data_sources = {}
        try:
            if merchant.data_sources:
                data_sources = json.loads(merchant.data_sources)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Build suggestions
        suggestions = {
            "expense_type": merchant.suggested_expense_type or merchant.expense_type,
            "tags": merchant.suggested_tags.split(",") if merchant.suggested_tags else [],
            "business_type": merchant.business_type,
            "category": merchant.category
        }
        
        # Parse patterns
        patterns = []
        try:
            if merchant.label_patterns:
                patterns = json.loads(merchant.label_patterns)
        except (json.JSONDecodeError, TypeError):
            pass
        
        return MerchantIntelligenceResponse(
            success=True,
            message="Merchant intelligence retrieved successfully",
            merchant=merchant_data,
            confidence_score=merchant.confidence_score,
            suggestions=suggestions,
            patterns=patterns,
            last_updated=merchant.last_updated.isoformat() if merchant.last_updated else ""
        )
        
    except Exception as e:
        logger.error(f"Error getting merchant intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/merchants/{merchant_name}/correct")
async def apply_user_correction(
    merchant_name: str,
    correction: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Apply user correction to improve merchant intelligence"""
    try:
        engine = get_intelligence_engine(db)
        
        # Find merchant
        merchant = db.query(MerchantKnowledgeBase).filter(
            MerchantKnowledgeBase.merchant_name == merchant_name
        ).first()
        
        if not merchant:
            merchant = engine.get_or_create_merchant(merchant_name)
        
        # Apply correction
        updated_merchant = engine.update_merchant_intelligence(
            merchant=merchant,
            user_correction=correction
        )
        
        return {
            "success": True,
            "message": "User correction applied successfully",
            "merchant_name": updated_merchant.merchant_name,
            "new_confidence_score": updated_merchant.confidence_score,
            "new_success_rate": updated_merchant.success_rate
        }
        
    except Exception as e:
        logger.error(f"Error applying user correction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/research/{search_term}", response_model=ResearchResultsResponse)
async def get_research_results(
    search_term: str,
    force_refresh: bool = Query(False, description="Force refresh cached results"),
    db: Session = Depends(get_db)
):
    """Get or perform research for a merchant"""
    try:
        research_engine = get_web_research_engine(db)
        
        # Check cache first unless force refresh
        cached_results = None
        if not force_refresh:
            cached_results = research_engine.get_cached_research(search_term)
        
        if cached_results:
            return ResearchResultsResponse(
                success=True,
                message="Research results retrieved from cache",
                search_term=search_term,
                results=cached_results,
                confidence=cached_results.get('confidence', 0.5),
                cached=True,
                sources=cached_results.get('sources', [])
            )
        
        # Perform intelligent web research
        web_researcher = create_web_researcher(db)
        research_result = await web_researcher.research_merchant(search_term, force_refresh)
        
        # Convert research result to response format
        results_data = {
            "business_type": research_result.business_type,
            "category": research_result.category,
            "location": research_result.location or {},
            "contact_info": research_result.contact_info or {},
            "confidence": research_result.confidence_score,
            "quality_score": research_result.quality_score
        }
        
        return ResearchResultsResponse(
            success=True,
            message="Research completed successfully",
            search_term=search_term,
            results=results_data,
            confidence=research_result.confidence_score,
            cached=False,
            sources=research_result.sources
        )
        
    except Exception as e:
        logger.error(f"Error performing research: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research/batch")
async def batch_research_merchants(
    limit: int = Query(10, description="Number of merchants to research"),
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Perform batch web research on merchants needing intelligence"""
    try:
        # Queue background task for batch research
        background_tasks.add_task(
            _batch_research_task,
            limit,
            db
        )
        
        return {
            "success": True,
            "message": f"Batch research queued for up to {limit} merchants",
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error queuing batch research: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research/auto-enrich")
async def auto_enrich_merchants(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Automatically enrich merchants with low confidence scores"""
    try:
        # Queue background task for auto-enrichment
        background_tasks.add_task(
            _auto_enrich_task,
            db
        )
        
        return {
            "success": True,
            "message": "Auto-enrichment process started",
            "description": "Merchants with low confidence will be researched and updated"
        }
        
    except Exception as e:
        logger.error(f"Error starting auto-enrichment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=IntelligenceMetricsResponse)
async def get_intelligence_metrics(db: Session = Depends(get_db)):
    """Get comprehensive intelligence system metrics"""
    try:
        analytics = get_intelligence_analytics(db)
        report = analytics.generate_intelligence_report()
        
        return IntelligenceMetricsResponse(
            success=True,
            message="Intelligence metrics retrieved successfully",
            metrics=report['metrics'],
            top_performers=report['top_performers'],
            needs_attention=report['needs_attention'],
            learning_efficiency=report['learning_efficiency']
        )
        
    except Exception as e:
        logger.error(f"Error getting intelligence metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns")
async def get_merchant_patterns(db: Session = Depends(get_db)):
    """Get merchant pattern analysis"""
    try:
        analytics = get_intelligence_analytics(db)
        patterns = analytics.get_merchant_patterns()
        
        return {
            "success": True,
            "message": "Merchant patterns retrieved successfully",
            "patterns": patterns
        }
        
    except Exception as e:
        logger.error(f"Error getting merchant patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Learning and Training Endpoints

@router.post("/learn/transaction")
async def learn_from_transaction(
    transaction_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Learn from a transaction to improve merchant intelligence"""
    try:
        merchant_name = transaction_data.get('label', '').strip()
        if not merchant_name:
            raise HTTPException(status_code=400, detail="Transaction label is required")
        
        # Add background task for learning
        background_tasks.add_task(
            _process_transaction_learning,
            merchant_name,
            transaction_data,
            db
        )
        
        return {
            "success": True,
            "message": "Transaction learning queued successfully",
            "merchant_name": merchant_name
        }
        
    except Exception as e:
        logger.error(f"Error learning from transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learn/correction")
async def learn_from_user_correction(
    correction_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Learn from user correction to improve future predictions"""
    try:
        merchant_name = correction_data.get('merchant_name', '').strip()
        original_prediction = correction_data.get('original_prediction', {})
        user_correction = correction_data.get('user_correction', {})
        
        if not merchant_name:
            raise HTTPException(status_code=400, detail="Merchant name is required")
        
        engine = get_intelligence_engine(db)
        
        # Get or create merchant
        merchant = engine.get_or_create_merchant(merchant_name)
        
        # Apply correction and learn from it
        learning_data = {
            'accuracy_rating': correction_data.get('accuracy_rating', 0.8),
            'business_type': user_correction.get('business_type'),
            'category': user_correction.get('category'),
            'expense_type': user_correction.get('expense_type'),
            'tags': user_correction.get('tags', '')
        }
        
        # Update merchant intelligence
        updated_merchant = engine.update_merchant_intelligence(
            merchant=merchant,
            user_correction=learning_data
        )
        
        # Learn pattern for future predictions
        _learn_prediction_pattern(
            merchant_name=merchant_name,
            original=original_prediction,
            corrected=user_correction,
            db=db
        )
        
        return {
            "success": True,
            "message": "User correction processed and learned successfully",
            "merchant_name": merchant_name,
            "new_confidence": updated_merchant.confidence_score,
            "learning_applied": True
        }
        
    except Exception as e:
        logger.error(f"Error learning from user correction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learn/feedback")
async def process_user_feedback(
    feedback_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Process user feedback on automatic classifications"""
    try:
        merchant_name = feedback_data.get('merchant_name', '').strip()
        feedback_type = feedback_data.get('feedback_type')  # 'correct', 'incorrect', 'partial'
        accuracy_score = feedback_data.get('accuracy_score', 0.5)  # 0.0 to 1.0
        
        if not merchant_name or feedback_type not in ['correct', 'incorrect', 'partial']:
            raise HTTPException(
                status_code=400, 
                detail="Merchant name and valid feedback type required"
            )
        
        # Find merchant
        merchant = db.query(MerchantKnowledgeBase).filter(
            MerchantKnowledgeBase.merchant_name == merchant_name
        ).first()
        
        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant not found")
        
        # Update accuracy metrics
        if feedback_type == 'correct':
            merchant.auto_classifications += 1
            merchant.accuracy_rating = min(merchant.accuracy_rating + 0.1, 1.0)
        elif feedback_type == 'incorrect':
            merchant.user_corrections += 1
            merchant.accuracy_rating = max(merchant.accuracy_rating - 0.2, 0.0)
        else:  # partial
            merchant.auto_classifications += 1
            merchant.user_corrections += 1
            merchant.accuracy_rating = (merchant.accuracy_rating + accuracy_score) / 2
        
        # Recalculate success rate
        total = merchant.auto_classifications + merchant.user_corrections
        if total > 0:
            merchant.success_rate = merchant.auto_classifications / total
        
        # Update confidence based on feedback
        from intelligence_system import KnowledgeScorer
        scorer = KnowledgeScorer()
        merchant.confidence_score = scorer.calculate_confidence_score(
            web_confidence=merchant.research_quality or 0.0,
            user_feedback_score=merchant.accuracy_rating,
            usage_frequency=merchant.usage_count,
            data_sources_count=len(json.loads(merchant.data_sources or "{}")),
            research_quality=merchant.research_quality or 0.0
        )
        
        merchant.last_updated = datetime.now()
        db.commit()
        
        return {
            "success": True,
            "message": "User feedback processed successfully",
            "merchant_name": merchant_name,
            "new_confidence": merchant.confidence_score,
            "new_success_rate": merchant.success_rate,
            "feedback_type": feedback_type
        }
        
    except Exception as e:
        logger.error(f"Error processing user feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-learn")
async def batch_learn_from_transactions(
    limit: int = Query(100, description="Number of transactions to process"),
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process batch learning from recent transactions"""
    try:
        # Get recent transactions without merchant intelligence
        recent_transactions = db.query(Transaction).filter(
            Transaction.is_expense == True,
            Transaction.exclude == False,
            Transaction.label.isnot(None),
            Transaction.label != ""
        ).order_by(desc(Transaction.date_op)).limit(limit).all()
        
        # Queue background learning tasks
        processed_count = 0
        for transaction in recent_transactions:
            if transaction.label and transaction.label.strip():
                background_tasks.add_task(
                    _process_transaction_learning,
                    transaction.label.strip(),
                    {
                        "amount": transaction.amount,
                        "category": transaction.category,
                        "date": transaction.date_op.isoformat() if transaction.date_op else None,
                        "expense_type": transaction.expense_type
                    },
                    db
                )
                processed_count += 1
        
        return {
            "success": True,
            "message": f"Batch learning queued for {processed_count} transactions",
            "processed_count": processed_count
        }
        
    except Exception as e:
        logger.error(f"Error in batch learning: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cache Management Endpoints

@router.get("/cache/stats")
async def get_cache_statistics(db: Session = Depends(get_db)):
    """Get research cache statistics"""
    try:
        total_entries = db.query(ResearchCache).count()
        
        # Get cache usage statistics
        cache_stats = db.query(
            func.sum(ResearchCache.usage_count).label('total_usage'),
            func.avg(ResearchCache.confidence_score).label('avg_confidence'),
            func.avg(ResearchCache.result_quality).label('avg_quality')
        ).first()
        
        # Get stale cache entries
        stale_threshold = datetime.now() - timedelta(days=30)
        stale_entries = db.query(ResearchCache).filter(
            ResearchCache.created_at < stale_threshold
        ).count()
        
        # Get top cached searches
        top_searches = db.query(ResearchCache).order_by(
            desc(ResearchCache.usage_count)
        ).limit(10).all()
        
        return {
            "success": True,
            "message": "Cache statistics retrieved successfully",
            "statistics": {
                "total_entries": total_entries,
                "total_usage": cache_stats.total_usage or 0,
                "average_confidence": round(cache_stats.avg_confidence or 0, 3),
                "average_quality": round(cache_stats.avg_quality or 0, 3),
                "stale_entries": stale_entries,
                "hit_rate": round((cache_stats.total_usage or 0) / max(total_entries, 1), 3)
            },
            "top_searches": [
                {
                    "search_term": entry.search_term,
                    "usage_count": entry.usage_count,
                    "confidence": entry.confidence_score,
                    "last_used": entry.last_used.isoformat() if entry.last_used else None
                }
                for entry in top_searches
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache/cleanup")
async def cleanup_cache(
    max_age_days: int = Query(30, description="Maximum age of cache entries to keep"),
    db: Session = Depends(get_db)
):
    """Clean up old cache entries"""
    try:
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        # Delete old cache entries
        deleted_count = db.query(ResearchCache).filter(
            ResearchCache.created_at < cutoff_date,
            ResearchCache.usage_count < 2  # Keep frequently used entries
        ).delete()
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Cache cleanup completed",
            "deleted_entries": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up cache: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# Utility Functions

async def _process_transaction_learning(
    merchant_name: str, 
    transaction_data: Dict[str, Any], 
    db: Session
):
    """Background task to process transaction learning"""
    try:
        engine = get_intelligence_engine(db)
        
        # Get or create merchant
        merchant = engine.get_or_create_merchant(merchant_name)
        
        # Update with transaction patterns
        if merchant.transaction_patterns:
            patterns = json.loads(merchant.transaction_patterns)
        else:
            patterns = {"amounts": [], "categories": [], "frequency": 0}
        
        # Add transaction data to patterns
        if transaction_data.get('amount'):
            patterns["amounts"].append(float(transaction_data['amount']))
            # Keep only last 50 amounts
            patterns["amounts"] = patterns["amounts"][-50:]
        
        if transaction_data.get('category'):
            if transaction_data['category'] not in patterns.get("categories", []):
                patterns.setdefault("categories", []).append(transaction_data['category'])
        
        patterns["frequency"] = patterns.get("frequency", 0) + 1
        patterns["last_seen"] = datetime.now().isoformat()
        
        merchant.transaction_patterns = json.dumps(patterns)
        merchant.usage_count += 1
        merchant.last_used = datetime.now()
        
        db.commit()
        
        logger.info(f"Processed learning for merchant: {merchant_name}")
        
    except Exception as e:
        logger.error(f"Error in background learning task: {e}")
        db.rollback()


async def _batch_research_task(limit: int, db: Session):
    """Background task for batch research"""
    try:
        # Find merchants needing research
        merchants = db.query(MerchantKnowledgeBase).filter(
            MerchantKnowledgeBase.confidence_score < 0.5,
            MerchantKnowledgeBase.needs_review == True
        ).limit(limit).all()
        
        if not merchants:
            logger.info("No merchants need research")
            return
        
        # Research merchants using web research engine
        web_researcher = create_web_researcher(db)
        merchant_names = [m.merchant_name for m in merchants]
        
        results = await web_researcher.batch_research_merchants(merchant_names)
        
        # Update merchants with results
        for result in results:
            merchant = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.merchant_name == result.merchant_name
            ).first()
            
            if merchant:
                merchant.business_type = result.business_type
                merchant.category = result.category
                merchant.confidence_score = result.confidence_score
                merchant.research_quality = result.quality_score
                merchant.research_date = datetime.now()
                merchant.research_duration_ms = result.research_duration_ms
                merchant.needs_review = result.confidence_score < 0.5
                
                # Update location
                if result.location:
                    merchant.city = result.location.get('city')
                    merchant.country = result.location.get('country', 'France')
                
                # Update contact info
                if result.contact_info:
                    merchant.website_url = result.contact_info.get('website')
                    merchant.phone_number = result.contact_info.get('phone')
                
                # Update data sources
                sources_data = {source: 0.7 for source in result.sources}
                merchant.data_sources = json.dumps(sources_data)
        
        db.commit()
        logger.info(f"Batch research completed for {len(results)} merchants")
        
    except Exception as e:
        logger.error(f"Error in batch research task: {e}")
        db.rollback()


async def _auto_enrich_task(db: Session):
    """Background task for auto-enrichment"""
    try:
        result = await research_unknown_merchants(db, limit=20)
        logger.info(f"Auto-enrichment completed: {result['message']}")
        
    except Exception as e:
        logger.error(f"Error in auto-enrichment task: {e}")


def _learn_prediction_pattern(
    merchant_name: str,
    original: Dict[str, Any],
    corrected: Dict[str, Any],
    db: Session
):
    """Learn from prediction corrections to improve future accuracy"""
    try:
        # Create or update label-tag mapping if tags were corrected
        if corrected.get('tags') and original.get('tags') != corrected.get('tags'):
            # Check for existing mapping
            existing_mapping = db.query(LabelTagMapping).filter(
                LabelTagMapping.label_pattern == merchant_name.lower()
            ).first()
            
            if existing_mapping:
                # Update existing mapping
                existing_mapping.suggested_tags = corrected['tags']
                existing_mapping.confidence_score = min(existing_mapping.confidence_score + 0.1, 1.0)
                existing_mapping.last_used = datetime.now()
                existing_mapping.accepted_count += 1
            else:
                # Create new mapping
                new_mapping = LabelTagMapping(
                    label_pattern=merchant_name.lower(),
                    suggested_tags=corrected['tags'],
                    confidence_score=0.8,
                    match_type="contains",
                    created_by="correction_learning",
                    created_at=datetime.now()
                )
                db.add(new_mapping)
        
        # Learn business type patterns
        if corrected.get('business_type') and original.get('business_type') != corrected.get('business_type'):
            # This could be extended to store business type patterns
            # For now, we rely on the merchant knowledge base update
            logger.info(f"Learning business type correction: {original.get('business_type')} -> {corrected.get('business_type')}")
        
        db.commit()
        logger.info(f"Pattern learning completed for {merchant_name}")
        
    except Exception as e:
        logger.error(f"Error in pattern learning: {e}")
        db.rollback()


# Health check endpoint
@router.get("/health")
async def intelligence_health_check(db: Session = Depends(get_db)):
    """Health check for intelligence system"""
    try:
        # Basic connectivity tests
        merchant_count = db.query(MerchantKnowledgeBase).count()
        cache_count = db.query(ResearchCache).count()
        
        return {
            "success": True,
            "message": "Intelligence system is healthy",
            "status": "operational",
            "statistics": {
                "merchants_in_kb": merchant_count,
                "cache_entries": cache_count,
                "last_check": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Intelligence health check failed: {e}")
        return {
            "success": False,
            "message": "Intelligence system health check failed",
            "status": "degraded",
            "error": str(e)
        }


logger.info("Intelligence API router initialized successfully")