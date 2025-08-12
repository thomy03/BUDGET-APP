"""
Classification API Router for intelligent expense classification
Provides endpoints for ML-based classification of expense tags as FIXED vs VARIABLE
"""

import logging
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from auth import get_current_user
from models.database import get_db, Transaction
from services.expense_classification import (
    get_expense_classification_service, 
    evaluate_classification_performance,
    ClassificationResult
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


# API Endpoints

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


logger.info("✅ Classification API router loaded with ML intelligence endpoints")