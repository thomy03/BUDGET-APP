"""
Transactions router for Budget Famille v2.3
Handles transaction operations and management
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user
from models.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/transactions",
    tags=["transactions"],
    responses={404: {"description": "Not found"}}
)

# Import models and schemas
from models.database import Transaction
from models.schemas import TxOut, ExcludeIn, TagsIn, TransactionUpdate, ExpenseTypeConversion

def parse_tags_to_array(tags_string: str) -> List[str]:
    """Convert comma-separated tags string to array"""
    if not tags_string or tags_string.strip() == "":
        return []
    return [tag.strip() for tag in tags_string.split(',') if tag.strip()]

def tx_to_response(tx: Transaction) -> TxOut:
    """Convert Transaction model to TxOut response with proper tags array"""
    return TxOut(
        id=tx.id,
        month=tx.month,
        date_op=tx.date_op,
        date_valeur=tx.date_op,
        amount=tx.amount,
        label=tx.label,
        category=getattr(tx, 'category', ''),
        subcategory=getattr(tx, 'subcategory', ''),
        is_expense=tx.is_expense,
        exclude=tx.exclude,
        expense_type=getattr(tx, 'expense_type', 'VARIABLE'),
        tags=parse_tags_to_array(tx.tags or "")
    )

@router.get("", response_model=List[TxOut])
def list_transactions(month: str, db: Session = Depends(get_db)):
    """
    List all transactions for a specific month
    
    Returns all transactions for the specified month in YYYY-MM format.
    """
    txs = db.query(Transaction).filter(Transaction.month == month).order_by(Transaction.date_op.desc()).all()
    return [tx_to_response(tx) for tx in txs]

@router.patch("/{tx_id}", response_model=TxOut)
def update_transaction(tx_id: int, payload: TransactionUpdate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Update transaction properties (exclude status, tags, expense_type, or combination)
    
    Unified endpoint to update transaction exclude status, tags, and/or expense type.
    Supports both string and array formats for tags with automatic conversion.
    Expense type controls strict separation between Fixed/Variable/Provision.
    """
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    
    # Track changes for automation
    changes_made = False
    old_tags = None
    old_expense_type = tx.expense_type
    
    # Update exclude status if provided
    if payload.exclude is not None:
        tx.exclude = payload.exclude
        changes_made = True
    
    # Update expense type if provided (strict separation logic)
    if payload.expense_type is not None:
        tx.expense_type = payload.expense_type
        changes_made = True
        logger.info(f"🔄 Transaction {tx_id} expense type changed: {old_expense_type} → {payload.expense_type}")
    
    # Update tags if provided
    if payload.tags is not None:
        old_tags = parse_tags_to_array(tx.tags or "")
        tx.tags = payload.tags
        changes_made = True
    
    if changes_made:
        db.add(tx)
        db.commit()
        db.refresh(tx)
        
        # Process tag automation if tags were added
        if payload.tags is not None and old_tags is not None:
            new_tags = parse_tags_to_array(tx.tags or "")
            added_tags = [tag for tag in new_tags if tag not in old_tags]
            
            if added_tags:
                try:
                    from services.tag_automation import get_tag_automation_service
                    automation_service = get_tag_automation_service(db)
                    
                    for tag in added_tags:
                        if tag.strip():  # Only process non-empty tags
                            mapping = automation_service.process_tag_creation(
                                tag_name=tag.strip(),
                                transaction=tx,
                                username=current_user.username
                            )
                            if mapping:
                                logger.info(f"✅ Auto-created fixed line for tag '{tag}' on transaction {tx_id}")
                            else:
                                logger.warning(f"⚠️ Could not auto-create fixed line for tag '{tag}'")
                except Exception as e:
                    # Don't fail the tag update if automation fails
                    logger.error(f"Tag automation error for transaction {tx_id}: {e}")
    
    return tx_to_response(tx)

@router.patch("/{tx_id}/expense-type", response_model=TxOut)
def convert_expense_type(tx_id: int, payload: ExpenseTypeConversion, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Convert transaction expense type (FIXED ↔ VARIABLE ↔ PROVISION)
    
    Dedicated endpoint for expense type conversion to ensure strict separation.
    This prevents double-counting between Fixed and Variable sections.
    """
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    
    old_type = tx.expense_type
    new_type = payload.expense_type
    
    # Prevent unnecessary updates
    if old_type == new_type:
        logger.info(f"⚠️ Transaction {tx_id} already has expense_type '{new_type}', no change needed")
        return tx_to_response(tx)
    
    # Update expense type
    tx.expense_type = new_type
    db.add(tx)
    db.commit()
    db.refresh(tx)
    
    logger.info(f"✅ Transaction {tx_id} expense type converted: {old_type} → {new_type} (User: {current_user.username})")
    
    return tx_to_response(tx)

@router.patch("/{tx_id}/tags", response_model=TxOut)
def update_tags(tx_id: int, payload: TagsIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Update tags for a transaction with automatic fixed line creation
    
    Updates the tags associated with a specific transaction and automatically
    creates corresponding fixed lines for new tags.
    """
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    
    # Get old and new tags for comparison
    old_tags = parse_tags_to_array(tx.tags or "")
    new_tags = parse_tags_to_array(payload.tags)
    
    # Find newly added tags
    added_tags = [tag for tag in new_tags if tag not in old_tags]
    
    # Update transaction tags
    tx.tags = payload.tags
    db.add(tx)
    db.commit()
    db.refresh(tx)
    
    # Process new tags for automatic fixed line creation
    if added_tags:
        try:
            from services.tag_automation import get_tag_automation_service
            automation_service = get_tag_automation_service(db)
            
            for tag in added_tags:
                if tag.strip():  # Only process non-empty tags
                    mapping = automation_service.process_tag_creation(
                        tag_name=tag.strip(),
                        transaction=tx,
                        username=current_user.username
                    )
                    if mapping:
                        logger.info(f"✅ Auto-created fixed line for tag '{tag}' on transaction {tx_id}")
                    else:
                        logger.warning(f"⚠️ Could not auto-create fixed line for tag '{tag}'")
        except Exception as e:
            # Don't fail the tag update if automation fails
            logger.error(f"Tag automation error for transaction {tx_id}: {e}")
    
    return tx_to_response(tx)

@router.get("/tags", response_model=List[str])
def list_tags(db: Session = Depends(get_db)):
    """
    List all unique tags used in transactions
    
    Returns a list of all unique tags found across all transactions.
    """
    from sqlalchemy import func, distinct
    
    # Récupérer tous les tags non-vides
    result = db.query(distinct(Transaction.tags)).filter(
        Transaction.tags.isnot(None),
        Transaction.tags != ""
    ).all()
    
    # Flatten et nettoyer les tags
    all_tags = set()
    for (tag_string,) in result:
        if tag_string:
            tags = [t.strip() for t in tag_string.split(',') if t.strip()]
            all_tags.update(tags)
    
    return sorted(list(all_tags))

@router.get("/tags-summary")
def tags_summary(month: str, db: Session = Depends(get_db)):
    """
    Get summary statistics for tags in a specific month
    
    Returns statistics about tag usage in the specified month.
    """
    from collections import defaultdict
    
    txs = db.query(Transaction).filter(
        Transaction.month == month,
        Transaction.tags.isnot(None),
        Transaction.tags != ""
    ).all()
    
    tag_stats = defaultdict(lambda: {"count": 0, "total_amount": 0})
    
    for tx in txs:
        if tx.tags:
            tags = [t.strip() for t in tx.tags.split(',') if t.strip()]
            for tag in tags:
                tag_stats[tag]["count"] += 1
                tag_stats[tag]["total_amount"] += abs(tx.amount or 0)
    
    return {
        "month": month,
        "tags": dict(tag_stats),
        "total_tagged_transactions": len(txs)
    }

@router.get("/tag-suggestions")
def get_tag_suggestions(label: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get tag suggestions for a transaction label
    
    Uses learned associations to suggest appropriate tags for a given label.
    """
    from models.database import LabelTagMapping
    from sqlalchemy import or_, func
    
    # Look for exact matches first
    exact_matches = db.query(LabelTagMapping).filter(
        LabelTagMapping.label_pattern == label,
        LabelTagMapping.is_active == True,
        LabelTagMapping.created_by == current_user.username
    ).order_by(LabelTagMapping.confidence_score.desc()).all()
    
    suggestions = []
    
    # Add exact matches
    for mapping in exact_matches:
        suggestions.append({
            "tags": mapping.suggested_tags.split(',') if mapping.suggested_tags else [],
            "confidence": mapping.confidence_score,
            "match_type": "exact",
            "usage_count": mapping.usage_count,
            "success_rate": mapping.success_rate
        })
    
    # If no exact matches, look for partial matches
    if not suggestions:
        partial_matches = db.query(LabelTagMapping).filter(
            or_(
                LabelTagMapping.label_pattern.contains(label),
                func.lower(label).contains(func.lower(LabelTagMapping.label_pattern))
            ),
            LabelTagMapping.is_active == True,
            LabelTagMapping.created_by == current_user.username,
            LabelTagMapping.match_type.in_(["contains", "starts_with"])
        ).order_by(LabelTagMapping.confidence_score.desc()).limit(3).all()
        
        for mapping in partial_matches:
            suggestions.append({
                "tags": mapping.suggested_tags.split(',') if mapping.suggested_tags else [],
                "confidence": mapping.confidence_score * 0.8,  # Lower confidence for partial matches
                "match_type": "partial",
                "usage_count": mapping.usage_count,
                "success_rate": mapping.success_rate
            })
    
    return {
        "label": label,
        "suggestions": suggestions[:5]  # Limit to top 5 suggestions
    }

@router.post("/learn-tag-association")
def learn_tag_association(
    payload: dict, 
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Learn a new label-to-tag association
    
    Records a user's tagging decision to improve future suggestions.
    """
    from models.database import LabelTagMapping
    from datetime import datetime
    
    label = payload.get("label", "").strip()
    tags = payload.get("tags", [])
    feedback_type = payload.get("feedback_type", "accepted")  # accepted, rejected, modified
    
    if not label or not isinstance(tags, list):
        raise HTTPException(status_code=400, detail="Label and tags are required")
    
    tags_string = ','.join([tag.strip() for tag in tags if tag.strip()])
    
    # Find or create mapping
    mapping = db.query(LabelTagMapping).filter(
        LabelTagMapping.label_pattern == label,
        LabelTagMapping.created_by == current_user.username
    ).first()
    
    if mapping:
        # Update existing mapping
        if feedback_type == "accepted":
            mapping.accepted_count += 1
            mapping.confidence_score = min(1.0, mapping.confidence_score + 0.1)
        elif feedback_type == "rejected":
            mapping.rejected_count += 1
            mapping.confidence_score = max(0.1, mapping.confidence_score - 0.2)
        elif feedback_type == "modified":
            mapping.modified_count += 1
            mapping.suggested_tags = tags_string
            mapping.confidence_score = min(1.0, mapping.confidence_score + 0.05)
        
        mapping.usage_count += 1
        mapping.last_used = datetime.now()
        
        # Recalculate success rate
        total_interactions = mapping.accepted_count + mapping.rejected_count + mapping.modified_count
        if total_interactions > 0:
            mapping.success_rate = (mapping.accepted_count + mapping.modified_count * 0.8) / total_interactions
        
        # Deactivate if success rate is too low
        if mapping.success_rate < 0.2 and total_interactions >= 5:
            mapping.is_active = False
            
    else:
        # Create new mapping
        mapping = LabelTagMapping(
            label_pattern=label,
            suggested_tags=tags_string,
            match_type="exact",
            case_sensitive=False,
            created_by=current_user.username,
            last_used=datetime.now(),
            accepted_count=1 if feedback_type == "accepted" else 0,
            rejected_count=1 if feedback_type == "rejected" else 0,
            modified_count=1 if feedback_type == "modified" else 0
        )
        db.add(mapping)
    
    db.commit()
    db.refresh(mapping)
    
    return {
        "message": "Tag association learned successfully",
        "mapping_id": mapping.id,
        "confidence_score": mapping.confidence_score,
        "success_rate": mapping.success_rate
    }

@router.get("/learned-associations")
def get_learned_associations(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get all learned label-to-tag associations for the current user
    
    Returns all associations with their statistics for management.
    """
    from models.database import LabelTagMapping
    
    mappings = db.query(LabelTagMapping).filter(
        LabelTagMapping.created_by == current_user.username,
        LabelTagMapping.is_active == True
    ).order_by(
        LabelTagMapping.usage_count.desc(),
        LabelTagMapping.confidence_score.desc()
    ).all()
    
    associations = []
    for mapping in mappings:
        associations.append({
            "id": mapping.id,
            "label_pattern": mapping.label_pattern,
            "suggested_tags": mapping.suggested_tags.split(',') if mapping.suggested_tags else [],
            "confidence_score": mapping.confidence_score,
            "usage_count": mapping.usage_count,
            "success_rate": mapping.success_rate,
            "match_type": mapping.match_type,
            "case_sensitive": mapping.case_sensitive,
            "created_at": mapping.created_at.isoformat() if mapping.created_at else None,
            "last_used": mapping.last_used.isoformat() if mapping.last_used else None,
            "accepted_count": mapping.accepted_count,
            "rejected_count": mapping.rejected_count,
            "modified_count": mapping.modified_count
        })
    
    return {
        "associations": associations,
        "total_count": len(associations)
    }

@router.delete("/learned-associations/{mapping_id}")
def delete_learned_association(
    mapping_id: int, 
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Delete a learned association
    
    Removes a specific label-to-tag association.
    """
    from models.database import LabelTagMapping
    
    mapping = db.query(LabelTagMapping).filter(
        LabelTagMapping.id == mapping_id,
        LabelTagMapping.created_by == current_user.username
    ).first()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Association not found")
    
    db.delete(mapping)
    db.commit()
    
    return {"message": "Association deleted successfully"}