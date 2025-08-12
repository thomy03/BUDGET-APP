"""
Merchant Knowledge Service for Dynamic Learning and Classification
Implements fuzzy matching, machine learning, and automated merchant intelligence
"""
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func, or_, and_, text
from difflib import SequenceMatcher
import re

from models.database import (
    MerchantKnowledgeBase, 
    ResearchCache, 
    Transaction
)
from models.schemas import *

logger = logging.getLogger(__name__)

class MerchantKnowledgeService:
    """
    Advanced merchant knowledge service with machine learning capabilities
    
    Features:
    - Fuzzy string matching for merchant identification
    - Confidence scoring and learning from user feedback
    - Web research integration and caching
    - Automatic pattern recognition and classification
    - Performance optimization with intelligent indexing
    """
    
    def __init__(self):
        self.similarity_threshold = 0.6  # Minimum similarity for fuzzy matching
        self.confidence_decay_days = 90   # Days after which confidence starts decaying
        self.max_cache_age_days = 30     # Max age for research cache
        
    def search_merchant_fuzzy(
        self,
        db: Session,
        merchant_name: str,
        confidence_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search merchants using fuzzy matching with confidence scoring
        
        Returns list of matching merchants sorted by confidence and usage
        """
        try:
            if not merchant_name or len(merchant_name.strip()) < 2:
                return []
            
            normalized_query = self._normalize_merchant_name(merchant_name)
            
            # First try exact normalized match (fastest)
            exact_matches = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.normalized_name == normalized_query,
                MerchantKnowledgeBase.is_active == True,
                MerchantKnowledgeBase.confidence_score >= confidence_threshold
            ).order_by(desc(MerchantKnowledgeBase.confidence_score)).all()
            
            if exact_matches:
                return [self._format_merchant_result(match, 1.0) for match in exact_matches]
            
            # Fuzzy search for similar merchants
            potential_matches = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.is_active == True,
                MerchantKnowledgeBase.confidence_score >= confidence_threshold
            ).order_by(desc(MerchantKnowledgeBase.usage_count)).limit(100).all()
            
            fuzzy_results = []
            for merchant in potential_matches:
                similarity = self._calculate_similarity(
                    normalized_query, 
                    merchant.normalized_name
                )
                
                if similarity >= self.similarity_threshold:
                    result = self._format_merchant_result(merchant, similarity)
                    fuzzy_results.append(result)
            
            # Sort by combined score (similarity * confidence * usage_weight)
            fuzzy_results.sort(
                key=lambda x: x['combined_score'], 
                reverse=True
            )
            
            logger.debug(f"Found {len(fuzzy_results)} fuzzy matches for '{merchant_name}'")
            return fuzzy_results[:10]  # Return top 10 matches
            
        except Exception as e:
            logger.error(f"Error in fuzzy merchant search: {e}")
            return []
    
    def get_merchant_by_id(self, db: Session, merchant_id: int) -> Optional[MerchantKnowledgeBase]:
        """Get merchant by ID with usage tracking"""
        try:
            merchant = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.id == merchant_id,
                MerchantKnowledgeBase.is_active == True
            ).first()
            
            if merchant:
                # Update usage tracking
                merchant.last_used = datetime.now()
                merchant.usage_count += 1
                db.commit()
                
            return merchant
            
        except Exception as e:
            logger.error(f"Error getting merchant by ID {merchant_id}: {e}")
            return None
    
    def create_merchant_entry(
        self,
        db: Session,
        merchant_name: str,
        business_type: str = None,
        category: str = None,
        expense_type: str = "VARIABLE",
        confidence_score: float = 0.5,
        source: str = "user_input",
        additional_data: Dict = None
    ) -> MerchantKnowledgeBase:
        """Create new merchant entry in knowledge base"""
        try:
            normalized_name = self._normalize_merchant_name(merchant_name)
            
            # Check if merchant already exists
            existing = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.normalized_name == normalized_name
            ).first()
            
            if existing:
                logger.info(f"Merchant '{merchant_name}' already exists, updating entry")
                return self.update_merchant_entry(
                    db, existing.id, 
                    business_type=business_type,
                    category=category,
                    expense_type=expense_type,
                    confidence_score=confidence_score,
                    additional_data=additional_data
                )
            
            # Create new merchant entry
            merchant = MerchantKnowledgeBase(
                merchant_name=merchant_name,
                normalized_name=normalized_name,
                business_type=business_type,
                category=category,
                expense_type=expense_type,
                confidence_score=confidence_score,
                created_by=source,
                data_sources=json.dumps({source: confidence_score}),
                is_active=True,
                usage_count=1,
                last_used=datetime.now()
            )
            
            # Add additional data if provided
            if additional_data:
                for key, value in additional_data.items():
                    if hasattr(merchant, key):
                        setattr(merchant, key, value)
            
            db.add(merchant)
            db.commit()
            db.refresh(merchant)
            
            logger.info(f"Created new merchant entry: {merchant_name}")
            return merchant
            
        except Exception as e:
            logger.error(f"Error creating merchant entry: {e}")
            db.rollback()
            raise
    
    def update_merchant_entry(
        self,
        db: Session,
        merchant_id: int,
        **updates
    ) -> Optional[MerchantKnowledgeBase]:
        """Update merchant entry with new information and confidence adjustment"""
        try:
            merchant = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.id == merchant_id
            ).first()
            
            if not merchant:
                logger.warning(f"Merchant with ID {merchant_id} not found")
                return None
            
            # Update fields
            updated_fields = []
            for key, value in updates.items():
                if hasattr(merchant, key) and value is not None:
                    setattr(merchant, key, value)
                    updated_fields.append(key)
            
            # Update metadata
            merchant.last_updated = datetime.now()
            
            # Adjust confidence based on update source
            if 'confidence_score' not in updates:
                # Boost confidence for user corrections
                if updates.get('source') == 'user_correction':
                    merchant.confidence_score = min(0.95, merchant.confidence_score + 0.1)
                    merchant.user_corrections += 1
            
            db.commit()
            db.refresh(merchant)
            
            logger.info(f"Updated merchant {merchant_id}, fields: {updated_fields}")
            return merchant
            
        except Exception as e:
            logger.error(f"Error updating merchant entry: {e}")
            db.rollback()
            return None
    
    def validate_merchant(
        self,
        db: Session,
        merchant_id: int,
        user_feedback: Dict[str, Any]
    ) -> bool:
        """Process user validation feedback to improve accuracy"""
        try:
            merchant = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.id == merchant_id
            ).first()
            
            if not merchant:
                return False
            
            # Process feedback
            feedback_type = user_feedback.get('type', 'validation')
            is_correct = user_feedback.get('is_correct', True)
            corrections = user_feedback.get('corrections', {})
            
            if is_correct:
                # Positive feedback - boost confidence
                merchant.confidence_score = min(0.98, merchant.confidence_score + 0.05)
                merchant.accuracy_rating = min(1.0, merchant.accuracy_rating + 0.02)
                merchant.success_rate = self._calculate_success_rate(merchant, True)
            else:
                # Negative feedback - reduce confidence and apply corrections
                merchant.confidence_score = max(0.1, merchant.confidence_score - 0.1)
                merchant.accuracy_rating = max(0.0, merchant.accuracy_rating - 0.05)
                merchant.success_rate = self._calculate_success_rate(merchant, False)
                merchant.needs_review = True
                
                # Apply corrections
                for field, corrected_value in corrections.items():
                    if hasattr(merchant, field):
                        setattr(merchant, field, corrected_value)
                        merchant.user_corrections += 1
            
            merchant.is_validated = True
            merchant.last_verified = datetime.now()
            
            db.commit()
            
            logger.info(f"Processed validation for merchant {merchant_id}: {'positive' if is_correct else 'negative'}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating merchant: {e}")
            db.rollback()
            return False
    
    def get_knowledge_base_stats(self, db: Session) -> Dict[str, Any]:
        """Get comprehensive statistics about the knowledge base"""
        try:
            # Basic counts
            total_merchants = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.is_active == True
            ).count()
            
            verified_merchants = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.is_active == True,
                MerchantKnowledgeBase.is_verified == True
            ).count()
            
            needs_review = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.needs_review == True,
                MerchantKnowledgeBase.is_active == True
            ).count()
            
            # Confidence distribution
            high_confidence = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.confidence_score >= 0.8,
                MerchantKnowledgeBase.is_active == True
            ).count()
            
            medium_confidence = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.confidence_score >= 0.5,
                MerchantKnowledgeBase.confidence_score < 0.8,
                MerchantKnowledgeBase.is_active == True
            ).count()
            
            low_confidence = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.confidence_score < 0.5,
                MerchantKnowledgeBase.is_active == True
            ).count()
            
            # Business type distribution
            business_types = db.query(
                MerchantKnowledgeBase.business_type,
                func.count(MerchantKnowledgeBase.id).label('count')
            ).filter(
                MerchantKnowledgeBase.is_active == True,
                MerchantKnowledgeBase.business_type.isnot(None)
            ).group_by(MerchantKnowledgeBase.business_type).all()
            
            # Expense type distribution
            expense_types = db.query(
                MerchantKnowledgeBase.expense_type,
                func.count(MerchantKnowledgeBase.id).label('count')
            ).filter(
                MerchantKnowledgeBase.is_active == True
            ).group_by(MerchantKnowledgeBase.expense_type).all()
            
            # Top used merchants
            top_merchants = db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.is_active == True
            ).order_by(desc(MerchantKnowledgeBase.usage_count)).limit(10).all()
            
            # Average confidence and accuracy
            avg_stats = db.query(
                func.avg(MerchantKnowledgeBase.confidence_score).label('avg_confidence'),
                func.avg(MerchantKnowledgeBase.accuracy_rating).label('avg_accuracy'),
                func.avg(MerchantKnowledgeBase.success_rate).label('avg_success_rate')
            ).filter(
                MerchantKnowledgeBase.is_active == True
            ).first()
            
            return {
                'total_merchants': total_merchants,
                'verified_merchants': verified_merchants,
                'needs_review': needs_review,
                'confidence_distribution': {
                    'high': high_confidence,
                    'medium': medium_confidence,
                    'low': low_confidence
                },
                'business_type_distribution': [
                    {'business_type': bt, 'count': count} for bt, count in business_types
                ],
                'expense_type_distribution': [
                    {'expense_type': et, 'count': count} for et, count in expense_types
                ],
                'top_merchants': [
                    {
                        'id': m.id,
                        'name': m.merchant_name,
                        'usage_count': m.usage_count,
                        'confidence_score': m.confidence_score
                    } for m in top_merchants
                ],
                'average_metrics': {
                    'confidence': float(avg_stats.avg_confidence or 0),
                    'accuracy': float(avg_stats.avg_accuracy or 0),
                    'success_rate': float(avg_stats.avg_success_rate or 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting knowledge base stats: {e}")
            return {}
    
    def cleanup_outdated_entries(self, db: Session, max_age_days: int = 180) -> int:
        """Clean up outdated and low-confidence entries"""
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            
            # Find entries to clean up
            outdated_entries = db.query(MerchantKnowledgeBase).filter(
                or_(
                    # Very old entries with no recent usage
                    and_(
                        MerchantKnowledgeBase.created_at < cutoff_date,
                        MerchantKnowledgeBase.last_used < cutoff_date,
                        MerchantKnowledgeBase.usage_count == 1,
                        MerchantKnowledgeBase.confidence_score < 0.3
                    ),
                    # Entries with consistently poor performance
                    and_(
                        MerchantKnowledgeBase.success_rate < 0.2,
                        MerchantKnowledgeBase.user_corrections > 3,
                        MerchantKnowledgeBase.confidence_score < 0.4
                    )
                )
            ).all()
            
            # Mark as inactive rather than delete to preserve learning
            count = 0
            for entry in outdated_entries:
                entry.is_active = False
                entry.needs_update = True
                count += 1
            
            db.commit()
            
            logger.info(f"Cleaned up {count} outdated merchant entries")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up outdated entries: {e}")
            db.rollback()
            return 0
    
    def _normalize_merchant_name(self, name: str) -> str:
        """Normalize merchant name for consistent matching"""
        if not name:
            return ""
        
        # Remove common prefixes/suffixes and normalize
        normalized = name.lower().strip()
        
        # Remove common business suffixes
        suffixes = ['sas', 'sarl', 'sa', 'eurl', 'sasu', 'snc', 'scop', 
                   'ltd', 'inc', 'llc', 'corp', 'co', 'company', 'limited']
        
        for suffix in suffixes:
            pattern = rf'\b{suffix}\b\.?$'
            normalized = re.sub(pattern, '', normalized).strip()
        
        # Remove special characters and extra spaces
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using multiple methods"""
        if not str1 or not str2:
            return 0.0
        
        # Use SequenceMatcher for ratio
        ratio = SequenceMatcher(None, str1, str2).ratio()
        
        # Check for substring matches
        if str1 in str2 or str2 in str1:
            ratio = max(ratio, 0.8)
        
        # Check for word-level matches
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if words1 and words2:
            word_intersection = len(words1 & words2)
            word_union = len(words1 | words2)
            word_similarity = word_intersection / word_union
            
            # Combine ratios
            ratio = max(ratio, word_similarity * 0.9)
        
        return ratio
    
    def _format_merchant_result(self, merchant: MerchantKnowledgeBase, similarity: float) -> Dict[str, Any]:
        """Format merchant result for API response"""
        # Calculate combined score for ranking
        usage_weight = min(1.0, merchant.usage_count / 10.0)  # Cap at 10 uses
        combined_score = similarity * merchant.confidence_score * (0.7 + 0.3 * usage_weight)
        
        return {
            'id': merchant.id,
            'merchant_name': merchant.merchant_name,
            'normalized_name': merchant.normalized_name,
            'business_type': merchant.business_type,
            'category': merchant.category,
            'expense_type': merchant.expense_type,
            'confidence_score': merchant.confidence_score,
            'similarity_score': similarity,
            'combined_score': combined_score,
            'usage_count': merchant.usage_count,
            'is_verified': merchant.is_verified,
            'last_used': merchant.last_used.isoformat() if merchant.last_used else None,
            'suggested_tags': merchant.suggested_tags,
            'data_sources': json.loads(merchant.data_sources) if merchant.data_sources else {},
            'accuracy_rating': merchant.accuracy_rating,
            'needs_review': merchant.needs_review
        }
    
    def _calculate_success_rate(self, merchant: MerchantKnowledgeBase, is_success: bool) -> float:
        """Calculate new success rate based on feedback"""
        current_successes = merchant.success_rate * merchant.auto_classifications
        
        if is_success:
            new_successes = current_successes + 1
        else:
            new_successes = current_successes
        
        new_total = merchant.auto_classifications + 1
        return new_successes / new_total if new_total > 0 else 0.5
    
    def get_merchants_for_review(self, db: Session, limit: int = 20) -> List[MerchantKnowledgeBase]:
        """Get merchants that need manual review"""
        try:
            return db.query(MerchantKnowledgeBase).filter(
                MerchantKnowledgeBase.needs_review == True,
                MerchantKnowledgeBase.is_active == True
            ).order_by(
                desc(MerchantKnowledgeBase.usage_count)
            ).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error getting merchants for review: {e}")
            return []
    
    def bulk_import_merchants(
        self,
        db: Session,
        merchants_data: List[Dict[str, Any]],
        source: str = "bulk_import"
    ) -> Dict[str, int]:
        """Bulk import merchant data for seeding the knowledge base"""
        try:
            created = 0
            updated = 0
            errors = 0
            
            for merchant_data in merchants_data:
                try:
                    merchant_name = merchant_data.get('merchant_name')
                    if not merchant_name:
                        errors += 1
                        continue
                    
                    existing = db.query(MerchantKnowledgeBase).filter(
                        MerchantKnowledgeBase.normalized_name == self._normalize_merchant_name(merchant_name)
                    ).first()
                    
                    if existing:
                        # Update existing entry
                        for key, value in merchant_data.items():
                            if hasattr(existing, key) and value is not None:
                                setattr(existing, key, value)
                        existing.last_updated = datetime.now()
                        updated += 1
                    else:
                        # Create new entry
                        merchant_data['normalized_name'] = self._normalize_merchant_name(merchant_name)
                        merchant_data['created_by'] = source
                        merchant_data['is_active'] = True
                        
                        merchant = MerchantKnowledgeBase(**merchant_data)
                        db.add(merchant)
                        created += 1
                        
                except Exception as e:
                    logger.error(f"Error processing merchant data: {e}")
                    errors += 1
                    continue
            
            db.commit()
            
            logger.info(f"Bulk import completed: {created} created, {updated} updated, {errors} errors")
            return {
                'created': created,
                'updated': updated,
                'errors': errors,
                'total_processed': len(merchants_data)
            }
            
        except Exception as e:
            logger.error(f"Error in bulk import: {e}")
            db.rollback()
            return {'created': 0, 'updated': 0, 'errors': len(merchants_data), 'total_processed': 0}