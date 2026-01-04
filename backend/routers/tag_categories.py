"""
Tag Category Mappings API Router

This module provides API endpoints for managing tag-to-category associations.
These mappings are used for analytics grouping and visualization.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from models.database import get_db, TagCategoryMapping
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tag-categories", tags=["Tag Categories"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class TagCategoryMappingCreate(BaseModel):
    """Model for creating a single tag-category mapping"""
    tag_name: str = Field(..., min_length=1, max_length=100, description="Tag name (will be lowercased)")
    category_id: str = Field(..., min_length=1, max_length=50, description="Category ID")


class TagCategoryMappingOut(BaseModel):
    """Model for returning a tag-category mapping"""
    id: int
    tag_name: str
    category_id: str
    user_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    usage_count: int

    class Config:
        from_attributes = True


class TagCategoryMappingBulkIn(BaseModel):
    """Model for bulk creating/updating tag-category mappings"""
    mappings: Dict[str, str] = Field(..., description="Dictionary of tag_name -> category_id")


class TagCategoryMappingBulkOut(BaseModel):
    """Model for returning bulk operation results"""
    created: int
    updated: int
    total: int
    mappings: Dict[str, str]


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/", response_model=Dict[str, str])
def get_all_mappings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all tag-category mappings as a dictionary.

    Returns a simple dict of {tag_name: category_id} for easy frontend consumption.
    """
    try:
        mappings = db.query(TagCategoryMapping).all()
        return {m.tag_name: m.category_id for m in mappings}
    except Exception as e:
        logger.error(f"Error fetching tag-category mappings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching mappings: {str(e)}"
        )


@router.get("/list", response_model=List[TagCategoryMappingOut])
def get_mappings_list(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all tag-category mappings as a list with full details.
    """
    try:
        mappings = db.query(TagCategoryMapping).order_by(TagCategoryMapping.tag_name).all()
        return mappings
    except Exception as e:
        logger.error(f"Error fetching tag-category mappings list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching mappings: {str(e)}"
        )


@router.post("/", response_model=TagCategoryMappingOut)
def create_or_update_mapping(
    mapping: TagCategoryMappingCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create or update a single tag-category mapping.

    If the tag already exists, updates its category. Otherwise creates a new mapping.
    """
    try:
        tag_name = mapping.tag_name.strip().lower()
        category_id = mapping.category_id.strip().lower()

        # Get user_id from current_user object (UserInDB or similar)
        user_id = getattr(current_user, 'username', None) or getattr(current_user, 'id', None)

        # Check if mapping already exists
        existing = db.query(TagCategoryMapping).filter(
            TagCategoryMapping.tag_name == tag_name
        ).first()

        if existing:
            # Update existing mapping
            existing.category_id = category_id
            existing.updated_at = datetime.utcnow()
            existing.usage_count += 1
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated tag-category mapping: {tag_name} -> {category_id}")
            return existing
        else:
            # Create new mapping
            new_mapping = TagCategoryMapping(
                tag_name=tag_name,
                category_id=category_id,
                user_id=user_id,
                usage_count=1
            )
            db.add(new_mapping)
            db.commit()
            db.refresh(new_mapping)
            logger.info(f"Created tag-category mapping: {tag_name} -> {category_id}")
            return new_mapping

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating/updating tag-category mapping: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving mapping: {str(e)}"
        )


@router.post("/bulk", response_model=TagCategoryMappingBulkOut)
def bulk_create_or_update_mappings(
    data: TagCategoryMappingBulkIn,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Bulk create or update tag-category mappings.

    Accepts a dictionary of {tag_name: category_id} and creates/updates all mappings.
    This is the primary endpoint used when syncing frontend localStorage to backend.
    """
    try:
        created = 0
        updated = 0
        result_mappings = {}

        # Get user_id from current_user object (UserInDB or similar)
        user_id = getattr(current_user, 'username', None) or getattr(current_user, 'id', None)

        for tag_name, category_id in data.mappings.items():
            tag_name = tag_name.strip().lower()
            category_id = category_id.strip().lower()

            # Skip empty values
            if not tag_name or not category_id:
                continue

            # Check if mapping already exists
            existing = db.query(TagCategoryMapping).filter(
                TagCategoryMapping.tag_name == tag_name
            ).first()

            if existing:
                if existing.category_id != category_id:
                    existing.category_id = category_id
                    existing.updated_at = datetime.utcnow()
                    updated += 1
                existing.usage_count += 1
            else:
                new_mapping = TagCategoryMapping(
                    tag_name=tag_name,
                    category_id=category_id,
                    user_id=user_id,
                    usage_count=1
                )
                db.add(new_mapping)
                created += 1

            result_mappings[tag_name] = category_id

        db.commit()
        logger.info(f"Bulk tag-category sync: {created} created, {updated} updated")

        return TagCategoryMappingBulkOut(
            created=created,
            updated=updated,
            total=created + updated,
            mappings=result_mappings
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error in bulk tag-category mapping: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving mappings: {str(e)}"
        )


@router.delete("/{tag_name}")
def delete_mapping(
    tag_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a tag-category mapping.
    """
    try:
        tag_name = tag_name.strip().lower()

        mapping = db.query(TagCategoryMapping).filter(
            TagCategoryMapping.tag_name == tag_name
        ).first()

        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mapping for tag '{tag_name}' not found"
            )

        db.delete(mapping)
        db.commit()
        logger.info(f"Deleted tag-category mapping: {tag_name}")

        return {"message": f"Mapping for tag '{tag_name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting tag-category mapping: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting mapping: {str(e)}"
        )


@router.get("/stats")
def get_mapping_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get statistics about tag-category mappings.
    """
    try:
        total_mappings = db.query(func.count(TagCategoryMapping.id)).scalar()

        # Count by category
        category_counts = db.query(
            TagCategoryMapping.category_id,
            func.count(TagCategoryMapping.id).label('count')
        ).group_by(TagCategoryMapping.category_id).all()

        categories_breakdown = {cat: count for cat, count in category_counts}

        # Most used mappings
        top_mappings = db.query(TagCategoryMapping).order_by(
            TagCategoryMapping.usage_count.desc()
        ).limit(10).all()

        return {
            "total_mappings": total_mappings,
            "categories_breakdown": categories_breakdown,
            "top_mappings": [
                {"tag": m.tag_name, "category": m.category_id, "usage_count": m.usage_count}
                for m in top_mappings
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching mapping stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching stats: {str(e)}"
        )
