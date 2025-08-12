"""
Tag Automation router for Budget Famille v2.3
Handles tag-to-fixed-line mapping management
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from dependencies.database import get_db
from services.tag_automation import get_tag_automation_service
from models.schemas import (
    TagFixedLineMappingResponse, TagFixedLineMappingCreate,
    TagFixedLineMappingUpdate, TagAutomationStats
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tag-automation",
    tags=["tag-automation"],
    responses={404: {"description": "Not found"}}
)


@router.get("/mappings", response_model=List[TagFixedLineMappingResponse])
async def list_tag_mappings(
    tag_name: Optional[str] = Query(None, description="Filtrer par nom de tag"),
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    List all active tag-to-fixed-line mappings
    
    Returns all active mappings between tags and fixed lines, optionally
    filtered by tag name.
    """
    automation_service = get_tag_automation_service(db)
    
    if tag_name:
        mappings = automation_service.get_mappings_by_tag(tag_name)
        logger.info(f"Retrieved {len(mappings)} mappings for tag '{tag_name}' by user {current_user.username}")
    else:
        mappings = automation_service.get_all_active_mappings()
        logger.info(f"Retrieved {len(mappings)} total active mappings by user {current_user.username}")
    
    return mappings


@router.get("/stats", response_model=TagAutomationStats)
async def get_automation_statistics(
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Get statistics about the tag automation system
    
    Returns comprehensive statistics about tag usage, mappings,
    and automation effectiveness.
    """
    automation_service = get_tag_automation_service(db)
    stats = automation_service.get_automation_stats()
    
    logger.info(f"Tag automation stats requested by user {current_user.username}")
    return stats


@router.delete("/mappings/{mapping_id}")
async def deactivate_mapping(
    mapping_id: int,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Deactivate a tag-to-fixed-line mapping
    
    Deactivates the specified mapping, preventing future automatic
    fixed line creation for this tag.
    """
    automation_service = get_tag_automation_service(db)
    success = automation_service.deactivate_mapping(mapping_id, current_user.username)
    
    if not success:
        raise HTTPException(status_code=404, detail="Mapping introuvable ou déjà désactivé")
    
    logger.info(f"Mapping {mapping_id} deactivated by user {current_user.username}")
    return {"ok": True, "message": f"Mapping {mapping_id} désactivé avec succès"}


@router.post("/mappings", response_model=TagFixedLineMappingResponse)
async def create_manual_mapping(
    payload: TagFixedLineMappingCreate,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Create a manual tag-to-fixed-line mapping
    
    Creates a manual mapping between a tag and an existing fixed line.
    This allows users to set up custom automation rules.
    """
    try:
        from models.database import TagFixedLineMapping, FixedLine
        
        # Verify that the fixed line exists
        fixed_line = db.query(FixedLine).filter(
            FixedLine.id == payload.fixed_line_id,
            FixedLine.active == True
        ).first()
        
        if not fixed_line:
            raise HTTPException(status_code=404, detail="Ligne fixe introuvable ou inactive")
        
        # Check if mapping already exists
        existing = db.query(TagFixedLineMapping).filter(
            TagFixedLineMapping.tag_name == payload.tag_name,
            TagFixedLineMapping.fixed_line_id == payload.fixed_line_id,
            TagFixedLineMapping.is_active == True
        ).first()
        
        if existing:
            raise HTTPException(status_code=409, detail="Mapping déjà existant pour ce tag et cette ligne fixe")
        
        # Create new mapping
        mapping = TagFixedLineMapping(
            tag_name=payload.tag_name,
            fixed_line_id=payload.fixed_line_id,
            label_pattern=payload.label_pattern,
            auto_created=payload.auto_created or False,
            created_by=current_user.username,
            is_active=payload.is_active
        )
        
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        
        # Convert to response using automation service
        automation_service = get_tag_automation_service(db)
        response = automation_service._mapping_to_response(mapping)
        
        logger.info(f"Manual tag mapping created: {payload.tag_name} → {fixed_line.label} by {current_user.username}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating manual tag mapping: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la création du mapping")


@router.patch("/mappings/{mapping_id}", response_model=TagFixedLineMappingResponse)
async def update_mapping(
    mapping_id: int,
    payload: TagFixedLineMappingUpdate,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Update an existing tag-to-fixed-line mapping
    
    Updates the specified mapping with new configuration.
    """
    try:
        from models.database import TagFixedLineMapping, FixedLine
        
        # Find the mapping
        mapping = db.query(TagFixedLineMapping).filter(
            TagFixedLineMapping.id == mapping_id
        ).first()
        
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping introuvable")
        
        # Update fields if provided
        if payload.tag_name is not None:
            mapping.tag_name = payload.tag_name
        
        if payload.fixed_line_id is not None:
            # Verify the new fixed line exists
            fixed_line = db.query(FixedLine).filter(
                FixedLine.id == payload.fixed_line_id,
                FixedLine.active == True
            ).first()
            if not fixed_line:
                raise HTTPException(status_code=404, detail="Nouvelle ligne fixe introuvable ou inactive")
            mapping.fixed_line_id = payload.fixed_line_id
        
        if payload.label_pattern is not None:
            mapping.label_pattern = payload.label_pattern
        
        if payload.is_active is not None:
            mapping.is_active = payload.is_active
        
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        
        # Convert to response
        automation_service = get_tag_automation_service(db)
        response = automation_service._mapping_to_response(mapping)
        
        logger.info(f"Tag mapping {mapping_id} updated by user {current_user.username}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tag mapping {mapping_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du mapping")


@router.get("/mappings/{mapping_id}", response_model=TagFixedLineMappingResponse)
async def get_mapping_details(
    mapping_id: int,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Get details of a specific tag-to-fixed-line mapping
    
    Returns detailed information about a specific mapping including
    related fixed line information.
    """
    from models.database import TagFixedLineMapping
    
    mapping = db.query(TagFixedLineMapping).filter(
        TagFixedLineMapping.id == mapping_id
    ).first()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping introuvable")
    
    automation_service = get_tag_automation_service(db)
    response = automation_service._mapping_to_response(mapping)
    
    logger.info(f"Mapping {mapping_id} details requested by user {current_user.username}")
    return response


@router.get("/tags/{tag_name}/preview")
async def preview_tag_automation(
    tag_name: str,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Preview what would happen if a tag is applied automatically
    
    Shows what fixed line would be created for a given tag name
    without actually creating it.
    """
    try:
        from models.database import Transaction
        
        # Find a recent transaction with this tag to base the preview on
        sample_transaction = db.query(Transaction).filter(
            Transaction.tags.contains(tag_name)
        ).order_by(Transaction.date_op.desc()).first()
        
        if not sample_transaction:
            # Create a mock transaction for preview
            sample_transaction = Transaction(
                label=f"Sample transaction for {tag_name}",
                amount=50.0,  # Default amount
                category="autres"
            )
        
        automation_service = get_tag_automation_service(db)
        
        # Generate preview information
        preview_label = automation_service._generate_fixed_line_label(
            tag_name, sample_transaction.label or ""
        )
        estimated_amount = abs(sample_transaction.amount) if sample_transaction.amount else 0.0
        category = automation_service._map_transaction_category_to_fixed_line_category(
            sample_transaction.category or ""
        )
        pattern = automation_service._extract_label_pattern(
            sample_transaction.label or ""
        )
        
        return {
            "tag_name": tag_name,
            "preview_fixed_line": {
                "label": preview_label,
                "estimated_amount": estimated_amount,
                "category": category,
                "freq": "mensuelle",
                "split_mode": "clé"
            },
            "label_pattern": pattern,
            "based_on_transaction": {
                "id": sample_transaction.id if hasattr(sample_transaction, 'id') else None,
                "label": sample_transaction.label,
                "amount": sample_transaction.amount,
                "category": sample_transaction.category
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating tag automation preview for '{tag_name}': {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération du preview")


@router.post("/classify/transaction/{transaction_id}")
async def classify_transaction(
    transaction_id: int,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Classify a specific transaction as Fixed or Variable using intelligent classification
    
    Uses AI patterns to determine if a transaction should be classified as a recurring
    fixed expense or a variable expense.
    """
    try:
        from models.database import Transaction
        
        # Find the transaction
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction introuvable")
        
        automation_service = get_tag_automation_service(db)
        classification_result = automation_service.classify_transaction_type(transaction)
        
        # Add transaction details to response
        result = {
            "transaction": {
                "id": transaction.id,
                "label": transaction.label,
                "amount": transaction.amount,
                "category": transaction.category,
                "date": transaction.date_op.isoformat() if transaction.date_op else None
            },
            "classification": classification_result,
            "recommendation": {
                "action": "create_fixed_line" if classification_result["should_create_fixed_line"] else "keep_variable",
                "reason": (
                    f"Score de confiance de {classification_result['confidence_score']:.1%} pour "
                    f"classification {classification_result['expense_type']}"
                )
            }
        }
        
        logger.info(
            f"Transaction {transaction_id} classified as {classification_result['expense_type']} "
            f"(confidence: {classification_result['confidence_score']:.2f}) by user {current_user.username}"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error classifying transaction {transaction_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la classification")


@router.post("/convert/transaction-to-fixed/{transaction_id}")
async def convert_transaction_to_fixed_line(
    transaction_id: int,
    force_conversion: bool = Query(False, description="Forcer la conversion même si la confiance est faible"),
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Convert a transaction to a fixed line using intelligent classification
    
    Creates a new fixed expense line based on a transaction, using AI classification
    to determine optimal settings and category.
    """
    try:
        from models.database import Transaction
        
        # Find the transaction
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction introuvable")
        
        automation_service = get_tag_automation_service(db)
        
        # Classify the transaction
        classification_result = automation_service.classify_transaction_type(transaction)
        
        # Check if conversion is recommended
        if not force_conversion and not classification_result["should_create_fixed_line"]:
            return {
                "converted": False,
                "reason": (
                    f"Transaction classifiée comme {classification_result['expense_type']} "
                    f"avec confiance de {classification_result['confidence_score']:.1%}. "
                    "Utiliser force_conversion=true pour forcer la conversion."
                ),
                "classification": classification_result,
                "transaction": {
                    "id": transaction.id,
                    "label": transaction.label,
                    "amount": transaction.amount
                }
            }
        
        # Create automatic tag for conversion tracking
        conversion_tag = f"auto_fixed_{transaction_id}"
        
        # Create the fixed line
        fixed_line = automation_service._create_fixed_line_from_tag(
            conversion_tag, transaction, current_user.username
        )
        
        if not fixed_line:
            raise HTTPException(status_code=500, detail="Échec de la création de la ligne fixe")
        
        # Create mapping for tracking
        from models.database import TagFixedLineMapping
        mapping = TagFixedLineMapping(
            tag_name=conversion_tag,
            fixed_line_id=fixed_line.id,
            auto_created=True,
            created_by=current_user.username,
            label_pattern=automation_service._extract_label_pattern(transaction.label or ""),
            usage_count=1
        )
        
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        
        result = {
            "converted": True,
            "fixed_line": {
                "id": fixed_line.id,
                "label": fixed_line.label,
                "amount": fixed_line.amount,
                "category": fixed_line.category,
                "freq": fixed_line.freq
            },
            "classification": classification_result,
            "mapping": {
                "id": mapping.id,
                "tag_name": conversion_tag
            },
            "transaction": {
                "id": transaction.id,
                "label": transaction.label,
                "amount": transaction.amount
            }
        }
        
        logger.info(
            f"✅ Transaction {transaction_id} converted to fixed line {fixed_line.id} "
            f"by user {current_user.username}"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting transaction {transaction_id} to fixed line: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la conversion")


@router.get("/classification/summary")
async def get_classification_summary(
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Get summary of the intelligent classification system
    
    Returns information about classification patterns, rules, and statistics.
    """
    try:
        automation_service = get_tag_automation_service(db)
        
        # Get classification system summary
        classification_summary = automation_service.classifier.get_classification_summary()
        
        # Get automation stats
        automation_stats = automation_service.get_automation_stats()
        
        # Get some recent classification examples
        from models.database import Transaction
        recent_transactions = db.query(Transaction).filter(
            Transaction.is_expense == True
        ).order_by(Transaction.date_op.desc()).limit(5).all()
        
        classification_examples = []
        for tx in recent_transactions:
            if tx.label:
                classification = automation_service.classify_transaction_type(tx)
                classification_examples.append({
                    "transaction": {
                        "id": tx.id,
                        "label": tx.label[:50] + "..." if len(tx.label) > 50 else tx.label,
                        "amount": tx.amount
                    },
                    "classification": classification
                })
        
        result = {
            "classification_system": classification_summary,
            "automation_stats": {
                "total_mappings": automation_stats.total_mappings,
                "auto_created_mappings": automation_stats.auto_created_mappings,
                "total_usage_count": automation_stats.total_usage_count
            },
            "recent_classification_examples": classification_examples,
            "endpoints": {
                "classify_transaction": "/tag-automation/classify/transaction/{id}",
                "convert_transaction": "/tag-automation/convert/transaction-to-fixed/{id}",
                "bulk_classify": "/tag-automation/classify/bulk"
            }
        }
        
        logger.info(f"Classification summary requested by user {current_user.username}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting classification summary: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du résumé")


@router.post("/classify/bulk")
async def bulk_classify_transactions(
    month: str = Query(..., description="Mois au format YYYY-MM"),
    limit: int = Query(100, description="Nombre maximum de transactions à classifier"),
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Bulk classify transactions for a given month
    
    Classifies multiple transactions at once, useful for analyzing spending patterns
    and identifying potential fixed expenses.
    """
    try:
        from models.database import Transaction
        
        # Get transactions for the specified month
        transactions = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.is_expense == True,
            Transaction.exclude == False
        ).order_by(Transaction.date_op.desc()).limit(limit).all()
        
        if not transactions:
            return {
                "month": month,
                "total_transactions": 0,
                "classifications": [],
                "summary": {
                    "fixed_count": 0,
                    "variable_count": 0,
                    "high_confidence_fixed": 0
                }
            }
        
        automation_service = get_tag_automation_service(db)
        
        # Prepare transaction data for bulk classification
        transaction_data = []
        for tx in transactions:
            transaction_data.append({
                "id": tx.id,
                "label": tx.label or "",
                "amount": abs(tx.amount) if tx.amount else 0,
                "category": tx.category or "",
                "date": tx.date_op.isoformat() if tx.date_op else None
            })
        
        # Bulk classify
        classifications = automation_service.classifier.bulk_classify_expenses(transaction_data)
        
        # Calculate summary statistics
        fixed_count = sum(1 for c in classifications if c["expense_type"] == "fixe")
        variable_count = len(classifications) - fixed_count
        high_confidence_fixed = sum(
            1 for c in classifications 
            if c["expense_type"] == "fixe" and c["classification_confidence"] >= 0.7
        )
        
        # Get top potential fixed expenses
        potential_fixed = sorted([
            c for c in classifications 
            if c["expense_type"] == "fixe" and c["classification_confidence"] >= 0.6
        ], key=lambda x: x["classification_confidence"], reverse=True)[:10]
        
        result = {
            "month": month,
            "total_transactions": len(classifications),
            "classifications": classifications,
            "summary": {
                "fixed_count": fixed_count,
                "variable_count": variable_count,
                "high_confidence_fixed": high_confidence_fixed,
                "potential_conversion_rate": f"{(high_confidence_fixed / len(classifications) * 100):.1f}%"
            },
            "recommendations": {
                "top_potential_fixed_expenses": potential_fixed,
                "suggested_actions": [
                    f"Convertir {high_confidence_fixed} dépenses en lignes fixes avec confiance élevée",
                    f"Examiner {fixed_count - high_confidence_fixed} dépenses avec confiance modérée",
                    f"Maintenir {variable_count} dépenses comme variables"
                ]
            }
        }
        
        logger.info(
            f"Bulk classification for {month}: {len(classifications)} transactions, "
            f"{fixed_count} fixed, {high_confidence_fixed} high confidence by user {current_user.username}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in bulk classification for month {month}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la classification en lot")