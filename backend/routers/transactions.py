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
from models.schemas import TxOut, ExcludeIn, TagsIn

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
def toggle_exclude(tx_id: int, payload: ExcludeIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Toggle the exclude status of a transaction
    
    Updates whether a transaction should be excluded from calculations.
    """
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    
    tx.exclude = payload.exclude
    db.add(tx); db.commit(); db.refresh(tx)
    return tx_to_response(tx)

@router.patch("/{tx_id}/tags", response_model=TxOut)
def update_tags(tx_id: int, payload: TagsIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Update tags for a transaction
    
    Updates the tags associated with a specific transaction.
    """
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    
    tx.tags = payload.tags
    db.add(tx); db.commit(); db.refresh(tx)
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