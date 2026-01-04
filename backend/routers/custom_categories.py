"""
Custom Categories API Router

This module provides API endpoints for managing user-defined categories.
These categories are used to classify tags into parent categories for analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from models.database import get_db, CustomCategory
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/custom-categories", tags=["Custom Categories"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class CustomCategoryCreate(BaseModel):
    """Model for creating a custom category"""
    id: str = Field(..., min_length=1, max_length=50, description="Category ID (lowercase)")
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    icon: Optional[str] = Field(None, max_length=10, description="Emoji icon")
    color: Optional[str] = Field(None, max_length=7, description="Hex color")


class CustomCategoryOut(BaseModel):
    """Model for returning a custom category"""
    id: str
    name: str
    icon: Optional[str]
    color: Optional[str]
    user_id: Optional[str]
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CustomCategoryBulkIn(BaseModel):
    """Model for bulk sync of custom categories"""
    categories: List[CustomCategoryCreate] = Field(..., description="List of categories to sync")


class CustomCategoryBulkOut(BaseModel):
    """Model for returning bulk operation results"""
    created: int
    updated: int
    total: int
    categories: List[CustomCategoryOut]


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[CustomCategoryOut])
def get_all_categories(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all custom categories.
    """
    try:
        categories = db.query(CustomCategory).filter(
            CustomCategory.is_active == True
        ).order_by(CustomCategory.name).all()
        return categories
    except Exception as e:
        logger.error(f"Error fetching custom categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching categories: {str(e)}"
        )


@router.get("/{category_id}", response_model=CustomCategoryOut)
def get_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a single custom category by ID.
    """
    try:
        category = db.query(CustomCategory).filter(
            CustomCategory.id == category_id.lower()
        ).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category_id}' not found"
            )

        return category
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching category: {str(e)}"
        )


@router.post("/", response_model=CustomCategoryOut)
def create_or_update_category(
    category: CustomCategoryCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create or update a custom category.
    """
    try:
        category_id = category.id.strip().lower()
        user_id = getattr(current_user, 'username', None) or getattr(current_user, 'id', None)

        # Check if category already exists
        existing = db.query(CustomCategory).filter(
            CustomCategory.id == category_id
        ).first()

        if existing:
            # Update existing category
            existing.name = category.name
            existing.icon = category.icon
            existing.color = category.color
            existing.updated_at = datetime.utcnow()
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated custom category: {category_id}")
            return existing
        else:
            # Create new category
            new_category = CustomCategory(
                id=category_id,
                name=category.name,
                icon=category.icon,
                color=category.color,
                user_id=user_id,
                is_active=True
            )
            db.add(new_category)
            db.commit()
            db.refresh(new_category)
            logger.info(f"Created custom category: {category_id}")
            return new_category

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating/updating custom category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving category: {str(e)}"
        )


@router.post("/bulk", response_model=CustomCategoryBulkOut)
def bulk_sync_categories(
    data: CustomCategoryBulkIn,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Bulk sync custom categories.

    This endpoint syncs all categories from frontend localStorage to backend.
    """
    try:
        created = 0
        updated = 0
        result_categories = []

        user_id = getattr(current_user, 'username', None) or getattr(current_user, 'id', None)

        for cat in data.categories:
            category_id = cat.id.strip().lower()

            # Skip empty values
            if not category_id or not cat.name:
                continue

            # Check if category already exists
            existing = db.query(CustomCategory).filter(
                CustomCategory.id == category_id
            ).first()

            if existing:
                # Update if different
                if existing.name != cat.name or existing.icon != cat.icon or existing.color != cat.color:
                    existing.name = cat.name
                    existing.icon = cat.icon
                    existing.color = cat.color
                    existing.updated_at = datetime.utcnow()
                    existing.is_active = True
                    updated += 1
                result_categories.append(existing)
            else:
                # Create new
                new_category = CustomCategory(
                    id=category_id,
                    name=cat.name,
                    icon=cat.icon,
                    color=cat.color,
                    user_id=user_id,
                    is_active=True
                )
                db.add(new_category)
                created += 1
                result_categories.append(new_category)

        db.commit()

        # Refresh all to get updated values
        for cat in result_categories:
            db.refresh(cat)

        logger.info(f"Bulk custom categories sync: {created} created, {updated} updated")

        return CustomCategoryBulkOut(
            created=created,
            updated=updated,
            total=created + updated,
            categories=result_categories
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error in bulk custom categories sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing categories: {str(e)}"
        )


@router.delete("/{category_id}")
def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a custom category (soft delete - sets is_active=False).
    """
    try:
        category_id = category_id.strip().lower()

        category = db.query(CustomCategory).filter(
            CustomCategory.id == category_id
        ).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category_id}' not found"
            )

        # Soft delete
        category.is_active = False
        category.updated_at = datetime.utcnow()
        db.commit()
        logger.info(f"Deleted custom category: {category_id}")

        return {"message": f"Category '{category_id}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting custom category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting category: {str(e)}"
        )
