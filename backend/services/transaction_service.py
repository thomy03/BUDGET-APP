"""
Transaction Service for Budget Famille v2.3
Business logic for transaction operations
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import pandas as pd

logger = logging.getLogger(__name__)

class TransactionService:
    """Service for transaction business logic operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_transactions_by_month(self, month: str) -> List[Dict[str, Any]]:
        """
        Get all transactions for a specific month
        
        Args:
            month: Month in YYYY-MM format
            
        Returns:
            List of transaction dictionaries
        """
        try:
            from app import Transaction
            
            transactions = self.db.query(Transaction).filter(
                Transaction.month == month
            ).order_by(Transaction.date_op.desc()).all()
            
            return [
                {
                    "id": tx.id,
                    "month": tx.month,
                    "date_op": tx.date_op,
                    "date_valeur": tx.date_valeur,
                    "amount": tx.amount,
                    "label": tx.label,
                    "category": tx.category,
                    "subcategory": tx.subcategory,
                    "is_expense": tx.is_expense,
                    "exclude": tx.exclude,
                    "tags": tx.tags or ""
                }
                for tx in transactions
            ]
        except Exception as e:
            logger.error(f"Error fetching transactions for month {month}: {str(e)}")
            raise
    
    def update_transaction_exclude_status(self, tx_id: int, exclude: bool) -> Dict[str, Any]:
        """
        Update the exclude status of a transaction
        
        Args:
            tx_id: Transaction ID
            exclude: New exclude status
            
        Returns:
            Updated transaction data
        """
        try:
            from app import Transaction
            
            transaction = self.db.query(Transaction).filter(Transaction.id == tx_id).first()
            if not transaction:
                raise ValueError(f"Transaction {tx_id} not found")
            
            transaction.exclude = exclude
            self.db.add(transaction)
            self.db.commit()
            self.db.refresh(transaction)
            
            logger.info(f"Transaction {tx_id} exclude status updated to {exclude}")
            
            return {
                "id": transaction.id,
                "month": transaction.month,
                "date_op": transaction.date_op,
                "date_valeur": transaction.date_valeur,
                "amount": transaction.amount,
                "label": transaction.label,
                "category": transaction.category,
                "subcategory": transaction.subcategory,
                "is_expense": transaction.is_expense,
                "exclude": transaction.exclude,
                "tags": transaction.tags or ""
            }
        except Exception as e:
            logger.error(f"Error updating transaction exclude status: {str(e)}")
            raise
    
    def update_transaction_tags(self, tx_id: int, tags: str) -> Dict[str, Any]:
        """
        Update tags for a transaction
        
        Args:
            tx_id: Transaction ID
            tags: New tags string
            
        Returns:
            Updated transaction data
        """
        try:
            from app import Transaction
            
            transaction = self.db.query(Transaction).filter(Transaction.id == tx_id).first()
            if not transaction:
                raise ValueError(f"Transaction {tx_id} not found")
            
            transaction.tags = tags
            self.db.add(transaction)
            self.db.commit()
            self.db.refresh(transaction)
            
            logger.info(f"Transaction {tx_id} tags updated")
            
            return {
                "id": transaction.id,
                "month": transaction.month,
                "date_op": transaction.date_op,
                "date_valeur": transaction.date_valeur,
                "amount": transaction.amount,
                "label": transaction.label,
                "category": transaction.category,
                "subcategory": transaction.subcategory,
                "is_expense": transaction.is_expense,
                "exclude": transaction.exclude,
                "tags": transaction.tags or ""
            }
        except Exception as e:
            logger.error(f"Error updating transaction tags: {str(e)}")
            raise
    
    def get_all_tags(self) -> List[str]:
        """
        Get all unique tags from all transactions
        
        Returns:
            List of unique tags
        """
        try:
            from app import Transaction
            from sqlalchemy import distinct
            
            # Get all non-empty tags
            result = self.db.query(distinct(Transaction.tags)).filter(
                Transaction.tags.isnot(None),
                Transaction.tags != ""
            ).all()
            
            # Flatten and clean tags
            all_tags = set()
            for (tag_string,) in result:
                if tag_string:
                    tags = [t.strip() for t in tag_string.split(',') if t.strip()]
                    all_tags.update(tags)
            
            return sorted(list(all_tags))
        except Exception as e:
            logger.error(f"Error fetching tags: {str(e)}")
            raise
    
    def get_tags_summary(self, month: str) -> Dict[str, Any]:
        """
        Get tag usage summary for a specific month
        
        Args:
            month: Month in YYYY-MM format
            
        Returns:
            Tag usage statistics
        """
        try:
            from app import Transaction
            from collections import defaultdict
            
            transactions = self.db.query(Transaction).filter(
                Transaction.month == month,
                Transaction.tags.isnot(None),
                Transaction.tags != ""
            ).all()
            
            tag_stats = defaultdict(lambda: {"count": 0, "total_amount": 0})
            
            for tx in transactions:
                if tx.tags:
                    tags = [t.strip() for t in tx.tags.split(',') if t.strip()]
                    for tag in tags:
                        tag_stats[tag]["count"] += 1
                        tag_stats[tag]["total_amount"] += abs(tx.amount or 0)
            
            return {
                "month": month,
                "tags": dict(tag_stats),
                "total_tagged_transactions": len(transactions)
            }
        except Exception as e:
            logger.error(f"Error generating tags summary for month {month}: {str(e)}")
            raise
    
    def bulk_update_transactions(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk update multiple transactions
        
        Args:
            updates: List of transaction updates
            
        Returns:
            Summary of updates performed
        """
        try:
            from app import Transaction
            
            updated_count = 0
            
            for update in updates:
                tx_id = update.get("id")
                if not tx_id:
                    continue
                
                transaction = self.db.query(Transaction).filter(Transaction.id == tx_id).first()
                if not transaction:
                    continue
                
                # Update fields that are provided
                for field, value in update.items():
                    if field != "id" and hasattr(transaction, field):
                        setattr(transaction, field, value)
                
                self.db.add(transaction)
                updated_count += 1
            
            self.db.commit()
            
            logger.info(f"Bulk updated {updated_count} transactions")
            
            return {
                "updated_count": updated_count,
                "total_requests": len(updates)
            }
        except Exception as e:
            logger.error(f"Error in bulk transaction update: {str(e)}")
            self.db.rollback()
            raise