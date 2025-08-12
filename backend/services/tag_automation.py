"""
Tag Automation Service for Budget Famille v2.3
Handles automatic conversion of tags to fixed lines with intelligent expense classification
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.database import (
    Transaction, FixedLine, TagFixedLineMapping, User
)
from models.schemas import (
    TagFixedLineMappingCreate, TagFixedLineMappingResponse,
    FixedLineIn, FixedLineOut, TagAutomationStats
)
from services.expense_classification import get_expense_classification_service, ClassificationResult

logger = logging.getLogger(__name__)


class TagAutomationService:
    """Service for managing automatic tag to fixed line conversion with intelligent classification"""
    
    def __init__(self, db: Session):
        self.db = db
        self.classification_service = get_expense_classification_service(db)
    
    def process_tag_creation(self, tag_name: str, transaction: Transaction, username: str) -> Optional[TagFixedLineMappingResponse]:
        """
        Process tag creation and potentially create automatic fixed line
        
        Args:
            tag_name: Name of the newly created tag
            transaction: Transaction that received the tag
            username: Username of the user who created the tag
            
        Returns:
            TagFixedLineMappingResponse if a mapping was created, None otherwise
        """
        try:
            # Check if mapping already exists for this tag
            existing_mapping = self.db.query(TagFixedLineMapping).filter(
                TagFixedLineMapping.tag_name == tag_name,
                TagFixedLineMapping.is_active == True
            ).first()
            
            if existing_mapping:
                # Update usage statistics
                existing_mapping.usage_count += 1
                existing_mapping.last_used = datetime.utcnow()
                self.db.add(existing_mapping)
                self.db.commit()
                logger.info(f"Updated usage for existing tag mapping: {tag_name}")
                return self._mapping_to_response(existing_mapping)
            
            # Create automatic fixed line for this tag
            fixed_line = self._create_fixed_line_from_tag(tag_name, transaction, username)
            if not fixed_line:
                logger.warning(f"Could not create fixed line for tag: {tag_name}")
                return None
            
            # Create mapping
            mapping = TagFixedLineMapping(
                tag_name=tag_name,
                fixed_line_id=fixed_line.id,
                auto_created=True,
                created_by=username,
                label_pattern=self._extract_label_pattern(transaction.label),
                usage_count=1,
                last_used=datetime.utcnow()
            )
            
            self.db.add(mapping)
            self.db.commit()
            self.db.refresh(mapping)
            
            logger.info(f"✅ Created automatic tag mapping: {tag_name} → Fixed Line ID {fixed_line.id}")
            return self._mapping_to_response(mapping)
            
        except Exception as e:
            logger.error(f"Error processing tag creation for '{tag_name}': {e}")
            self.db.rollback()
            return None
    
    def classify_transaction_type(self, transaction: Transaction, tag_name: str = "") -> Dict[str, Any]:
        """
        Classify transaction as Fixed or Variable using intelligent ML classification
        
        Args:
            transaction: Transaction to classify
            tag_name: Tag name for additional context
            
        Returns:
            Dictionary with classification results
        """
        try:
            # Get historical transactions for pattern analysis
            history = []
            if tag_name:
                history = self.classification_service.get_historical_transactions(tag_name)
            
            # Perform intelligent classification
            result = self.classification_service.classify_expense(
                tag_name=tag_name or "unknown",
                transaction_amount=abs(transaction.amount) if transaction.amount else 0.0,
                transaction_description=transaction.label or "",
                transaction_history=history
            )
            
            return {
                "expense_type": result.expense_type,
                "confidence_score": result.confidence,
                "primary_reason": result.primary_reason,
                "contributing_factors": result.contributing_factors,
                "keyword_matches": result.keyword_matches,
                "stability_score": result.stability_score,
                "frequency_score": result.frequency_score,
                "should_create_fixed_line": (
                    result.expense_type == "FIXED" and 
                    result.confidence >= 0.6
                )
            }
        except Exception as e:
            logger.error(f"Error classifying transaction: {e}")
            return {
                "expense_type": "VARIABLE",
                "confidence_score": 0.1,
                "primary_reason": f"Classification error: {str(e)}",
                "contributing_factors": [],
                "keyword_matches": [],
                "stability_score": None,
                "frequency_score": None,
                "should_create_fixed_line": False
            }
    
    def _create_fixed_line_from_tag(self, tag_name: str, transaction: Transaction, username: str) -> Optional[FixedLine]:
        """
        Create a fixed line based on tag and transaction information with intelligent classification
        
        Args:
            tag_name: Name of the tag
            transaction: Source transaction
            username: Username creating the line
            
        Returns:
            Created FixedLine or None if creation failed
        """
        try:
            # Use intelligent classification to determine if this should be a fixed line
            classification_result = self.classify_transaction_type(transaction, tag_name)
            
            # Only create fixed line if classified as FIXED with sufficient confidence
            if not classification_result["should_create_fixed_line"]:
                logger.info(
                    f"Tag '{tag_name}' classified as {classification_result['expense_type']} "
                    f"(confidence: {classification_result['confidence_score']:.2f}) - skipping fixed line creation"
                )
                return None
            
            # Generate a meaningful label for the fixed line
            label = self._generate_fixed_line_label(tag_name, transaction.label)
            
            # Estimate amount based on transaction
            amount = abs(transaction.amount) if transaction.amount else 0.0
            
            # Determine category based on transaction category with intelligent mapping
            category = self._map_transaction_category_to_fixed_line_category(
                transaction.category or "", classification_result["keyword_matches"]
            )
            
            # Create fixed line with intelligent defaults
            fixed_line = FixedLine(
                label=label,
                amount=amount,
                freq="mensuelle",  # Default to monthly for fixed expenses
                split_mode="proportionnel",  # Use proportional split as default
                split1=50.0,       # Default split
                split2=50.0,
                category=category,
                active=True
            )
            
            self.db.add(fixed_line)
            self.db.commit()
            self.db.refresh(fixed_line)
            
            logger.info(
                f"✅ Created intelligent fixed line: '{label}' ({amount}€, {category}) - "
                f"Classification: {classification_result['expense_type']} "
                f"(confidence: {classification_result['confidence_score']:.2f}) "
                f"Reason: {classification_result['primary_reason']}"
            )
            return fixed_line
            
        except Exception as e:
            logger.error(f"Error creating fixed line for tag '{tag_name}': {e}")
            self.db.rollback()
            return None
    
    def _generate_fixed_line_label(self, tag_name: str, transaction_label: str) -> str:
        """
        Generate an intelligent label for the fixed line based on tag and transaction
        
        Args:
            tag_name: Name of the tag
            transaction_label: Original transaction label
            
        Returns:
            Generated label for the fixed line
        """
        # Clean transaction label for readability
        cleaned_label = self._clean_transaction_label(transaction_label)
        
        # If tag name is descriptive enough, use it as base
        if len(tag_name) > 3 and not tag_name.lower().startswith('tag'):
            return f"{tag_name.title()} (auto-généré)"
        
        # Otherwise, use cleaned transaction label with tag
        if cleaned_label and len(cleaned_label) > 3:
            return f"{cleaned_label} - {tag_name} (auto-généré)"
        
        # Fallback
        return f"Dépense {tag_name} (auto-générée)"
    
    def _clean_transaction_label(self, label: str) -> str:
        """
        Clean transaction label to make it suitable for fixed line naming
        
        Args:
            label: Original transaction label
            
        Returns:
            Cleaned label
        """
        if not label:
            return ""
        
        # Remove common prefixes and suffixes
        cleaned = label.strip()
        
        # Remove dates (common pattern: DD/MM/YY)
        import re
        cleaned = re.sub(r'\d{2}/\d{2}/\d{2,4}', '', cleaned)
        
        # Remove card references
        cleaned = re.sub(r'CB\*\d+', '', cleaned).strip()
        cleaned = re.sub(r'CARTE\s+\d{2}/\d{2}/\d{2}', '', cleaned).strip()
        
        # Remove excess whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Truncate if too long
        if len(cleaned) > 50:
            cleaned = cleaned[:47] + "..."
        
        return cleaned
    
    def _extract_label_pattern(self, label: str) -> Optional[str]:
        """
        Extract a pattern from transaction label for future recognition
        
        Args:
            label: Transaction label
            
        Returns:
            Pattern string or None
        """
        if not label or len(label) < 5:
            return None
        
        # Extract merchant name or service identifier
        import re
        
        # Common patterns for recurring charges
        patterns = [
            r'(NETFLIX|SPOTIFY|AMAZON|GOOGLE|APPLE)',  # Subscription services
            r'(EDF|ENGIE|TOTAL|DIRECT ENERGIE)',       # Utility companies  
            r'(ORANGE|SFR|BOUYGUES|FREE)',             # Telecom providers
            r'(ASSURANCE|MUTUELLE|MAIF|MACIF)',        # Insurance
        ]
        
        for pattern in patterns:
            match = re.search(pattern, label.upper())
            if match:
                return match.group(1).lower()
        
        # Fallback: extract first meaningful word
        words = label.split()
        for word in words:
            if len(word) >= 4 and word.isalpha():
                return word.lower()
        
        return None
    
    def _map_transaction_category_to_fixed_line_category(self, transaction_category: str, 
                                                        keyword_matches: List[str] = None) -> str:
        """
        Map transaction category to fixed line category with intelligent pattern analysis
        
        Args:
            transaction_category: Original transaction category
            keyword_matches: Classification keyword matches
            
        Returns:
            Mapped fixed line category
        """
        # Enhanced category mapping with pattern-based intelligence
        category_mapping = {
            # Housing related
            'logement': 'logement',
            'électricité': 'logement', 
            'gaz': 'logement',
            'eau': 'logement',
            
            # Transport
            'carburant': 'transport',
            'transport': 'transport',
            'automobile': 'transport',
            
            # Services
            'téléphone': 'services',
            'internet': 'services',
            'assurance': 'services',
            'banque': 'services',
            
            # Entertainment
            'loisirs': 'loisirs',
            'restaurants': 'loisirs',
            'culture': 'loisirs',
            
            # Health
            'santé': 'santé',
            'pharmacie': 'santé',
            'médecin': 'santé',
        }
        
        # Use keyword matches for intelligent categorization
        if keyword_matches:
            for match in keyword_matches:
                match_lower = match.lower()
                
                # Map specific keywords to categories
                if any(keyword in match_lower for keyword in ['netflix', 'spotify', 'disney', 'abonnement']):
                    return 'loisirs'
                elif any(keyword in match_lower for keyword in ['edf', 'engie', 'electricite', 'gaz', 'eau']):
                    return 'logement'
                elif any(keyword in match_lower for keyword in ['orange', 'sfr', 'free', 'internet', 'mobile']):
                    return 'services'
                elif any(keyword in match_lower for keyword in ['assurance', 'mutuelle', 'banque']):
                    return 'services'
                elif any(keyword in match_lower for keyword in ['navigo', 'transport']):
                    return 'transport'
                elif any(keyword in match_lower for keyword in ['pharmacie', 'medical', 'medecin']):
                    return 'santé'
        
        # Fallback to traditional category mapping
        if transaction_category:
            category_lower = transaction_category.lower()
            
            # Check for direct matches
            for key, value in category_mapping.items():
                if key in category_lower:
                    return value
        
        # Default fallback
        return 'autres'
    
    def get_mappings_by_tag(self, tag_name: str) -> List[TagFixedLineMappingResponse]:
        """Get all mappings for a specific tag"""
        mappings = self.db.query(TagFixedLineMapping).filter(
            TagFixedLineMapping.tag_name == tag_name,
            TagFixedLineMapping.is_active == True
        ).all()
        
        return [self._mapping_to_response(m) for m in mappings]
    
    def get_all_active_mappings(self) -> List[TagFixedLineMappingResponse]:
        """Get all active tag-to-fixed-line mappings"""
        mappings = self.db.query(TagFixedLineMapping).filter(
            TagFixedLineMapping.is_active == True
        ).order_by(TagFixedLineMapping.created_at.desc()).all()
        
        return [self._mapping_to_response(m) for m in mappings]
    
    def deactivate_mapping(self, mapping_id: int, username: str) -> bool:
        """
        Deactivate a tag mapping
        
        Args:
            mapping_id: ID of the mapping to deactivate
            username: Username requesting the action
            
        Returns:
            True if successful, False otherwise
        """
        try:
            mapping = self.db.query(TagFixedLineMapping).filter(
                TagFixedLineMapping.id == mapping_id
            ).first()
            
            if not mapping:
                logger.warning(f"Mapping {mapping_id} not found for deactivation")
                return False
            
            mapping.is_active = False
            self.db.add(mapping)
            self.db.commit()
            
            logger.info(f"Deactivated tag mapping {mapping_id} by user {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error deactivating mapping {mapping_id}: {e}")
            self.db.rollback()
            return False
    
    def get_automation_stats(self) -> TagAutomationStats:
        """Get statistics about tag automation system"""
        try:
            # Basic counts
            total_mappings = self.db.query(TagFixedLineMapping).filter(
                TagFixedLineMapping.is_active == True
            ).count()
            
            auto_created = self.db.query(TagFixedLineMapping).filter(
                TagFixedLineMapping.is_active == True,
                TagFixedLineMapping.auto_created == True
            ).count()
            
            manual_mappings = total_mappings - auto_created
            
            # Total usage count
            total_usage = self.db.query(func.sum(TagFixedLineMapping.usage_count)).filter(
                TagFixedLineMapping.is_active == True
            ).scalar() or 0
            
            # Most used tags
            most_used = self.db.query(
                TagFixedLineMapping.tag_name,
                func.sum(TagFixedLineMapping.usage_count).label('total_usage')
            ).filter(
                TagFixedLineMapping.is_active == True
            ).group_by(
                TagFixedLineMapping.tag_name
            ).order_by(
                func.sum(TagFixedLineMapping.usage_count).desc()
            ).limit(10).all()
            
            most_used_tags = [
                {"tag_name": tag_name, "usage_count": usage_count}
                for tag_name, usage_count in most_used
            ]
            
            # Recent mappings
            recent = self.db.query(TagFixedLineMapping).filter(
                TagFixedLineMapping.is_active == True
            ).order_by(
                TagFixedLineMapping.created_at.desc()
            ).limit(5).all()
            
            recent_mappings = [self._mapping_to_response(m) for m in recent]
            
            return TagAutomationStats(
                total_mappings=total_mappings,
                auto_created_mappings=auto_created,
                manual_mappings=manual_mappings,
                total_usage_count=total_usage,
                most_used_tags=most_used_tags,
                recent_mappings=recent_mappings
            )
            
        except Exception as e:
            logger.error(f"Error getting automation stats: {e}")
            # Return empty stats on error
            return TagAutomationStats(
                total_mappings=0,
                auto_created_mappings=0,
                manual_mappings=0,
                total_usage_count=0,
                most_used_tags=[],
                recent_mappings=[]
            )
    
    def _mapping_to_response(self, mapping: TagFixedLineMapping) -> TagFixedLineMappingResponse:
        """Convert database mapping to response model"""
        # Get related fixed line
        fixed_line = None
        if mapping.fixed_line:
            fixed_line = FixedLineOut(
                id=mapping.fixed_line.id,
                label=mapping.fixed_line.label,
                amount=mapping.fixed_line.amount,
                freq=mapping.fixed_line.freq,
                split_mode=mapping.fixed_line.split_mode,
                split1=mapping.fixed_line.split1,
                split2=mapping.fixed_line.split2,
                category=mapping.fixed_line.category,
                active=mapping.fixed_line.active
            )
        
        return TagFixedLineMappingResponse(
            id=mapping.id,
            tag_name=mapping.tag_name,
            fixed_line_id=mapping.fixed_line_id,
            label_pattern=mapping.label_pattern,
            is_active=mapping.is_active,
            auto_created=mapping.auto_created,
            created_at=mapping.created_at,
            created_by=mapping.created_by,
            usage_count=mapping.usage_count,
            last_used=mapping.last_used,
            fixed_line=fixed_line
        )


def get_tag_automation_service(db: Session) -> TagAutomationService:
    """Dependency to get tag automation service"""
    return TagAutomationService(db)