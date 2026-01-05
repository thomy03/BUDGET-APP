"""
Transactions router for Budget Famille v2.3
Handles transaction operations and management
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
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
    # Normalize expense_type to uppercase to match TxOut validation pattern
    raw_expense_type = getattr(tx, 'expense_type', 'VARIABLE')
    normalized_expense_type = raw_expense_type.upper() if raw_expense_type else 'VARIABLE'
    
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
        expense_type=normalized_expense_type,
        tags=parse_tags_to_array(tx.tags or "")
    )

# Hierarchical navigation endpoints
@router.get("/categories")
def get_categories(
    month: str,
    expense_type: Optional[str] = Query(None, description="Filter by expense type: FIXED, VARIABLE, or PROVISION"),
    db: Session = Depends(get_db)
):
    """
    Get hierarchical category structure for navigation
    """
    from sqlalchemy import distinct, func
    
    query = db.query(
        Transaction.category,
        func.count(Transaction.id).label('count'),
        func.sum(func.abs(Transaction.amount)).label('amount')
    ).filter(
        Transaction.month == month,
        Transaction.exclude == False,
        Transaction.is_expense == True
    )
    
    # Filter by expense type if provided
    if expense_type and expense_type.strip():
        normalized_type = expense_type.strip().upper()
        if normalized_type in ['FIXED', 'VARIABLE', 'PROVISION']:
            query = query.filter(Transaction.expense_type == normalized_type)
    
    results = query.group_by(Transaction.category).all()
    
    return [
        {
            "name": result.category or "Non catégorisé",
            "level": "category",
            "value": result.category or "",
            "count": result.count,
            "amount": result.amount
        }
        for result in results
    ]

@router.get("/subcategories") 
def get_subcategories(
    month: str,
    category: str,
    expense_type: Optional[str] = Query(None, description="Filter by expense type: FIXED, VARIABLE, or PROVISION"),
    db: Session = Depends(get_db)
):
    """
    Get subcategories for a specific category
    """
    from sqlalchemy import func
    
    query = db.query(
        Transaction.subcategory,
        func.count(Transaction.id).label('count'),
        func.sum(func.abs(Transaction.amount)).label('amount')
    ).filter(
        Transaction.month == month,
        Transaction.category == category,
        Transaction.exclude == False,
        Transaction.is_expense == True
    )
    
    # Filter by expense type if provided  
    if expense_type and expense_type.strip():
        normalized_type = expense_type.strip().upper()
        if normalized_type in ['FIXED', 'VARIABLE', 'PROVISION']:
            query = query.filter(Transaction.expense_type == normalized_type)
    
    results = query.group_by(Transaction.subcategory).all()
    
    return [
        {
            "name": result.subcategory or "Non spécifié",
            "level": "subcategory", 
            "value": result.subcategory or "",
            "count": result.count,
            "amount": result.amount,
            "parent": category
        }
        for result in results
    ]

@router.get("/tags")
def get_transaction_tags(
    month: str,
    category: Optional[str] = Query(None),
    subcategory: Optional[str] = Query(None),
    expense_type: Optional[str] = Query(None, description="Filter by expense type: FIXED, VARIABLE, or PROVISION"),
    db: Session = Depends(get_db)
):
    """
    Get unique tags for transactions with optional category/subcategory filtering
    """
    query = db.query(Transaction).filter(
        Transaction.month == month,
        Transaction.exclude == False,
        Transaction.is_expense == True
    )
    
    # Apply filters
    if category:
        query = query.filter(Transaction.category == category)
    if subcategory:
        query = query.filter(Transaction.subcategory == subcategory)
    if expense_type and expense_type.strip():
        normalized_type = expense_type.strip().upper()
        if normalized_type in ['FIXED', 'VARIABLE', 'PROVISION']:
            query = query.filter(Transaction.expense_type == normalized_type)
    
    transactions = query.all()
    
    # Collect and count tags
    tag_counts = {}
    tag_amounts = {}
    
    for tx in transactions:
        if tx.tags:
            tx_tags = [tag.strip() for tag in tx.tags.split(',') if tag.strip()]
            for tag in tx_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                tag_amounts[tag] = tag_amounts.get(tag, 0) + abs(tx.amount)
    
    return [
        {
            "name": tag,
            "level": "tag",
            "value": tag,
            "count": count,
            "amount": tag_amounts[tag],
            "parent": f"{category or ''}/{subcategory or ''}".strip('/')
        }
        for tag, count in tag_counts.items()
    ]

@router.get("/hierarchy")
def get_hierarchy_data(
    month: str,
    expense_type: Optional[str] = Query(None, description="Filter by expense type: FIXED, VARIABLE, or PROVISION"),
    category: Optional[str] = Query(None),
    subcategory: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    level: Optional[str] = Query("category", description="Level to return: category, subcategory, tag"),
    db: Session = Depends(get_db)
):
    """
    Generic hierarchical data endpoint for navigation modal
    """
    if level == "category":
        return get_categories(month, expense_type, db)
    elif level == "subcategory" and category:
        return get_subcategories(month, category, expense_type, db)
    elif level == "tag":
        return get_transaction_tags(month, category, subcategory, expense_type, db)
    else:
        return []

@router.get("", response_model=List[TxOut])
def list_transactions(
    month: str, 
    tag: Optional[str] = Query(None, description="Filter by specific tag (supports multiple tags separated by comma)"),
    expense_type: Optional[str] = Query(None, description="Filter by expense type: FIXED, VARIABLE, or PROVISION"),
    db: Session = Depends(get_db)
):
    """
    List all transactions for a specific month with optional tag and expense type filtering
    
    Returns all transactions for the specified month in YYYY-MM format.
    If tag parameter is provided, filters transactions containing any of the specified tags.
    Multiple tags can be specified separated by commas (e.g., tag=restaurant,courses).
    If expense_type is provided, filters transactions by their expense type.
    """
    query = db.query(Transaction).filter(Transaction.month == month)
    
    # Add expense_type filtering if specified
    if expense_type and expense_type.strip():
        normalized_type = expense_type.strip().upper()
        if normalized_type in ['FIXED', 'VARIABLE', 'PROVISION']:
            query = query.filter(Transaction.expense_type == normalized_type)
        else:
            # If invalid expense_type provided, return empty results
            query = query.filter(Transaction.id == -1)  # Filter that matches nothing
    
    txs = query.order_by(Transaction.date_op.desc()).all()
    
    # Add tag filtering if specified (applied after database query for complex matching)
    if tag:
        # Parse requested tags
        requested_tags = [t.strip().lower() for t in tag.split(',') if t.strip()]
        
        filtered_txs = []
        for tx in txs:
            if tx.tags:
                tx_tags = [t.strip().lower() for t in tx.tags.split(',') if t.strip()]
                # Check if any requested tag is in this transaction's tags
                if any(req_tag in tx_tags for req_tag in requested_tags):
                    filtered_txs.append(tx)
        txs = filtered_txs
    
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
    
    # Send ML feedback for expense type change
    try:
        from routers.ml_feedback import MLFeedbackService
        from models.schemas import MLFeedbackCreate
        
        feedback_service = MLFeedbackService(db)
        feedback_data = MLFeedbackCreate(
            transaction_id=tx_id,
            original_expense_type=old_type,
            corrected_expense_type=new_type,
            feedback_type="correction",
            confidence_before=0.5  # Default confidence for manual corrections
        )
        feedback_service.save_feedback(feedback_data, current_user.username)
        logger.info(f"📊 ML feedback sent for expense type change on transaction {tx_id}")
    except Exception as e:
        logger.warning(f"Failed to send ML feedback for transaction {tx_id}: {e}")
    
    return tx_to_response(tx)

@router.put("/{tx_id}/tag", response_model=TxOut)
def put_transaction_tag(tx_id: int, payload: TagsIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Set tags for a transaction (PUT method for tag replacement)
    
    Replaces all tags for a specific transaction and automatically creates 
    corresponding fixed lines for new tags. This endpoint provides ML feedback data.
    """
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    
    # Store old tags for ML feedback
    old_tags = parse_tags_to_array(tx.tags or "")
    new_tags = parse_tags_to_array(payload.tags)
    
    # Update transaction tags
    tx.tags = payload.tags
    db.add(tx)
    db.commit()
    db.refresh(tx)
    
    # Find newly added tags for automation
    added_tags = [tag for tag in new_tags if tag not in old_tags]
    
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
    
    # Send ML feedback if tags changed significantly
    if old_tags != new_tags:
        try:
            from routers.ml_feedback import MLFeedbackService
            from models.schemas import MLFeedbackCreate
            
            feedback_service = MLFeedbackService(db)
            feedback_data = MLFeedbackCreate(
                transaction_id=tx_id,
                original_tag=','.join(old_tags) if old_tags else None,
                corrected_tag=','.join(new_tags) if new_tags else None,
                feedback_type="correction" if old_tags else "manual",
                confidence_before=0.5  # Default confidence for manual corrections
            )
            feedback_service.save_feedback(feedback_data, current_user.username)
            logger.info(f"📊 ML feedback sent for tag change on transaction {tx_id}")
        except Exception as e:
            logger.warning(f"Failed to send ML feedback for transaction {tx_id}: {e}")

    # Learn pattern from user tagging for future auto-tag
    if new_tags and tx.label:
        for tag in new_tags:
            if tag.strip():
                save_learned_pattern(tx.label, tag.strip())

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

    # Learn pattern from user tagging for future auto-tag
    if added_tags and tx.label:
        for tag in added_tags:
            if tag.strip():
                save_learned_pattern(tx.label, tag.strip())

    return tx_to_response(tx)

@router.put("/{tx_id}", response_model=TxOut)
def update_transaction(
    tx_id: int,
    payload: TransactionUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a transaction
    """
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    
    # Update fields if provided
    if payload.label is not None:
        tx.label = payload.label
    if payload.amount is not None:
        tx.amount = payload.amount
    if payload.category is not None:
        tx.category = payload.category
    if payload.subcategory is not None:
        tx.subcategory = payload.subcategory
    if payload.expense_type is not None:
        tx.expense_type = payload.expense_type.upper()
    if payload.tags is not None:
        tx.tags = payload.tags
    if payload.exclude is not None:
        tx.exclude = payload.exclude
    
    db.add(tx)
    db.commit()
    db.refresh(tx)
    
    logger.info(f"✅ Transaction {tx_id} updated by {current_user.username}")
    return tx_to_response(tx)

@router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    tx_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a transaction
    """
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    
    db.delete(tx)
    db.commit()
    
    logger.info(f"✅ Transaction {tx_id} deleted by {current_user.username}")
    return None

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
    
    try:
        # Validate month format
        if not month or len(month) != 7 or month[4] != '-':
            raise HTTPException(
                status_code=422, 
                detail="Month must be in YYYY-MM format"
            )
        
        txs = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.tags.isnot(None),
            Transaction.tags != ""
        ).all()
        
        tag_stats = defaultdict(lambda: {"count": 0, "total_amount": 0.0})
        
        for tx in txs:
            if tx.tags and tx.tags.strip():
                tags = [t.strip() for t in tx.tags.split(',') if t.strip()]
                for tag in tags:
                    tag_stats[tag]["count"] += 1
                    tag_stats[tag]["total_amount"] += abs(tx.amount or 0.0)
        
        # Convert to regular dict to avoid serialization issues
        clean_tag_stats = {}
        for tag_name, stats in tag_stats.items():
            clean_tag_stats[tag_name] = {
                "count": int(stats["count"]),
                "total_amount": round(float(stats["total_amount"]), 2)
            }
        
        # Return a simple dict instead of Pydantic model to avoid validation issues
        return {
            "month": month,
            "tags": clean_tag_stats,
            "total_tagged_transactions": len(txs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in tags_summary for month {month}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate tags summary: {str(e)}"
        )

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

# New endpoints for hierarchical navigation and transaction reassignment
@router.put("/{tx_id}/reassign")
def reassign_transaction(
    tx_id: int,
    category: str,
    subcategory: Optional[str] = None,
    tags: Optional[List[str]] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reassign transaction to new category, subcategory and tags
    """
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    
    # Update transaction properties
    tx.category = category
    tx.subcategory = subcategory or ""
    
    if tags:
        tx.tags = ','.join(tags)
    else:
        tx.tags = ""
    
    db.add(tx)
    db.commit()
    db.refresh(tx)
    
    logger.info(f"✅ Transaction {tx_id} reassigned: category={category}, subcategory={subcategory}, tags={tags}")
    
    return tx_to_response(tx)

# New endpoints for creating categories and tags
@router.post("/categories")
def create_category(
    name: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new category (for now, just return success since categories are implicit)
    """
    return {"message": f"Category '{name}' noted for future use", "name": name}

@router.post("/tags")
def create_tag(
    name: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new tag (for now, just return success since tags are implicit)
    """
    return {"message": f"Tag '{name}' noted for future use", "name": name}


# ============================================================================
# AUTO-TAGGING ENDPOINTS - Suggestion de tags basée sur les patterns appris
# ============================================================================

import json
import os
import re
from pathlib import Path

def get_patterns_path():
    """Get the path to learned_patterns.json"""
    return Path(__file__).parent.parent / "data" / "learned_patterns.json"

def load_learned_patterns():
    """Load learned patterns from JSON file"""
    patterns_path = get_patterns_path()
    if patterns_path.exists():
        try:
            with open(patterns_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading learned patterns: {e}")
    return {}

def save_learned_pattern(label: str, tag: str):
    """
    Save or update a learned pattern when user tags a transaction.
    This enables auto-tagging to learn from user actions.
    """
    if not label or not tag:
        return

    # Normalize the label for pattern matching
    normalized = normalize_label_for_matching(label)
    if not normalized or len(normalized) < 3:
        return

    try:
        patterns_path = get_patterns_path()

        # Ensure data directory exists
        patterns_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing patterns
        patterns = load_learned_patterns()

        # Update or create pattern
        normalized_upper = normalized.upper()
        if normalized_upper in patterns:
            # Update existing pattern
            pattern_data = patterns[normalized_upper]
            pattern_data['correction_count'] = pattern_data.get('correction_count', 0) + 1

            # Track all tags used for this pattern
            all_tags = pattern_data.get('all_tags', {})
            all_tags[tag] = all_tags.get(tag, 0) + 1
            pattern_data['all_tags'] = all_tags

            # Update suggested tag to the most common one
            most_common_tag = max(all_tags.items(), key=lambda x: x[1])[0]
            pattern_data['suggested_tag'] = most_common_tag
            pattern_data['last_updated'] = datetime.now().isoformat()

            # Update confidence based on consistency
            total_tags = sum(all_tags.values())
            pattern_data['confidence_score'] = min(1.0, all_tags[most_common_tag] / total_tags)
        else:
            # Create new pattern
            patterns[normalized_upper] = {
                'suggested_tag': tag,
                'correction_count': 1,
                'confidence_score': 1.0,
                'last_updated': datetime.now().isoformat(),
                'source': 'user_tagging',
                'all_tags': {tag: 1}
            }

        # Save updated patterns
        with open(patterns_path, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, indent=2, ensure_ascii=False)

        logger.info(f"Learned pattern saved: '{normalized_upper}' -> '{tag}'")

    except Exception as e:
        logger.error(f"Error saving learned pattern: {e}")

def normalize_label_for_matching(label: str) -> str:
    """Normalize transaction label for pattern matching"""
    if not label:
        return ""

    # Convert to uppercase
    clean = label.upper().strip()

    # Remove common prefixes
    prefixes = ['CARTE ', 'VIR ', 'PRLV ', 'AVOIR ', 'CHQ ', 'RETRAIT ']
    for prefix in prefixes:
        if clean.startswith(prefix):
            clean = clean[len(prefix):]

    # Remove dates (DD/MM/YY or DD/MM/YYYY)
    clean = re.sub(r'\d{2}/\d{2}/\d{2,4}', '', clean)

    # Remove card numbers (CB*1234)
    clean = re.sub(r'CB\*?\d+', '', clean)

    # Remove trailing amounts
    clean = re.sub(r'\d+[,\.]\d{2}\s*(?:EUR|€)?$', '', clean)

    # Clean up spaces
    clean = re.sub(r'\s+', ' ', clean).strip()

    return clean

def find_tag_suggestion(label: str, patterns: dict) -> tuple:
    """
    Find a tag suggestion for a transaction label using learned patterns.
    Returns (suggested_tag, confidence, match_type) or (None, 0, None)
    """
    if not label or not patterns:
        return None, 0, None

    normalized = normalize_label_for_matching(label)
    normalized_upper = normalized.upper()

    # 1. Exact match (highest confidence)
    for pattern_key, pattern_data in patterns.items():
        if normalized_upper == pattern_key.upper():
            return pattern_data.get('suggested_tag'), 1.0, 'exact'

    # 2. Pattern contains the key or key contains pattern (good confidence)
    for pattern_key, pattern_data in patterns.items():
        pattern_upper = pattern_key.upper()
        # Check if the pattern is a significant part of the label
        if pattern_upper in normalized_upper or normalized_upper in pattern_upper:
            # Extra validation: pattern should be at least 4 chars
            if len(pattern_key) >= 4:
                return pattern_data.get('suggested_tag'), 0.85, 'contains'

    # 3. First word match (medium confidence)
    first_word = normalized_upper.split()[0] if normalized_upper.split() else ""
    if first_word and len(first_word) >= 3:
        for pattern_key, pattern_data in patterns.items():
            pattern_first = pattern_key.upper().split()[0] if pattern_key.split() else ""
            if first_word == pattern_first:
                return pattern_data.get('suggested_tag'), 0.7, 'first_word'

    # 4. Known merchant keywords (lower confidence)
    merchant_keywords = {
        'AMAZON': 'amazon',
        'AMZN': 'amazon',
        'AMZ': 'amazon',
        'LECLERC': 'courses',
        'FRANPRIX': 'courses',
        'CARREFOUR': 'courses',
        'AUCHAN': 'courses',
        'PICARD': 'courses',
        'LIDL': 'courses',
        'MONOPRIX': 'courses',
        'CASINO': 'courses',
        'INTERMARCHE': 'courses',
        'TEMU': 'temu',
        'VINTED': 'vinted',
        'NETFLIX': 'streaming',
        'SPOTIFY': 'streaming',
        'DISNEY': 'streaming',
        'MCDO': 'restaurant',
        'MCDONALD': 'restaurant',
        'BURGER': 'restaurant',
        'KFC': 'restaurant',
        'SNCF': 'transport',
        'RATP': 'transport',
        'UBER': 'transport',
        'EDF': 'electricité',
        'ENGIE': 'énergie',
        'BOUYGUES': 'internet',
        'ORANGE': 'téléphone',
        'SFR': 'téléphone',
        'FREE': 'internet',
    }

    for keyword, tag in merchant_keywords.items():
        if keyword in normalized_upper:
            return tag, 0.6, 'keyword'

    return None, 0, None


@router.get("/auto-tag-preview")
def auto_tag_preview(
    month: str = Query(..., description="Month in YYYY-MM format"),
    min_confidence: float = Query(0.5, description="Minimum confidence threshold"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Preview auto-tag suggestions for transactions without tags.

    Returns suggestions based on learned patterns from user feedback.
    """
    try:
        # Load learned patterns
        patterns = load_learned_patterns()
        logger.info(f"Loaded {len(patterns)} patterns for auto-tagging")

        # Get transactions without tags for the specified month
        transactions = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.exclude == False
        ).all()

        # Filter to only untagged transactions (including "Non classé" which is the default)
        untagged = [tx for tx in transactions if not tx.tags or tx.tags.strip() == '' or tx.tags.strip().lower() == 'non classé']

        suggestions = []
        for tx in untagged:
            suggested_tag, confidence, match_type = find_tag_suggestion(tx.label, patterns)

            if suggested_tag and confidence >= min_confidence:
                suggestions.append({
                    'transaction_id': tx.id,
                    'label': tx.label,
                    'suggested_tag': suggested_tag,
                    'confidence': confidence,
                    'match_type': match_type,
                    'source_label': tx.label
                })

        # Sort by confidence descending
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)

        return {
            'total_untagged': len(untagged),
            'suggestions_found': len(suggestions),
            'suggestions': suggestions,
            'patterns_loaded': len(patterns)
        }

    except Exception as e:
        logger.error(f"Error in auto-tag preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating auto-tag suggestions: {str(e)}"
        )


@router.post("/auto-tag-month")
def auto_tag_month(
    month: str = Query(..., description="Month in YYYY-MM format"),
    min_confidence: float = Query(0.7, description="Minimum confidence to auto-apply"),
    dry_run: bool = Query(False, description="If true, don't apply changes"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply auto-tagging to all untagged transactions for a month.

    Only applies tags where confidence >= min_confidence.
    Use dry_run=true to preview without applying changes.
    """
    try:
        # Load learned patterns
        patterns = load_learned_patterns()

        # Get untagged transactions
        transactions = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.exclude == False
        ).all()

        untagged = [tx for tx in transactions if not tx.tags or tx.tags.strip() == '' or tx.tags.strip().lower() == 'non classé']

        applied = []
        skipped = []

        for tx in untagged:
            suggested_tag, confidence, match_type = find_tag_suggestion(tx.label, patterns)

            if suggested_tag and confidence >= min_confidence:
                if not dry_run:
                    tx.tags = suggested_tag
                    db.add(tx)

                applied.append({
                    'transaction_id': tx.id,
                    'label': tx.label,
                    'suggested_tag': suggested_tag,
                    'confidence': confidence,
                    'match_type': match_type
                })
            else:
                skipped.append({
                    'transaction_id': tx.id,
                    'label': tx.label,
                    'suggested_tag': suggested_tag,
                    'confidence': confidence,
                    'reason': 'low_confidence' if suggested_tag else 'no_match'
                })

        if not dry_run and applied:
            db.commit()
            logger.info(f"Auto-tagged {len(applied)} transactions for {month}")

        return {
            'total_untagged': len(untagged),
            'suggestions': applied,
            'applied_count': len(applied) if not dry_run else 0,
            'skipped_count': len(skipped),
            'dry_run': dry_run
        }

    except Exception as e:
        logger.error(f"Error in auto-tag month: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error applying auto-tags: {str(e)}"
        )