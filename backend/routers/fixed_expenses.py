"""
Fixed Expenses router for Budget Famille v2.3
Handles fixed expense lines management
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from auth import get_current_user
from models.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/fixed-lines",
    tags=["fixed-expenses"],
    responses={404: {"description": "Not found"}}
)

# Explicit OPTIONS handler for CORS preflight
@router.options("")
async def fixed_lines_options():
    """Handle CORS preflight requests for fixed-lines endpoint"""
    return {"message": "OK"}

@router.options("/{path:path}")
async def fixed_lines_options_with_path(path: str):
    """Handle CORS preflight requests for all fixed-lines sub-endpoints"""
    return {"message": "OK"}

# Import models and schemas
from models.database import FixedLine
from models.schemas import FixedLineIn, FixedLineOut

@router.get("", response_model=List[FixedLineOut])
async def list_fixed_lines(
    category: Optional[str] = Query(None, max_length=200, description="Filtrer par catégorie"),
    active_only: bool = Query(True, description="Afficher uniquement les lignes actives"),
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    List all fixed expense lines with optional category filtering
    
    Returns all fixed expense lines, optionally filtered by category and active status.
    """
    query = db.query(FixedLine)
    
    if active_only:
        query = query.filter(FixedLine.active == True)
    
    if category:
        query = query.filter(FixedLine.category == category)
    
    items = query.order_by(FixedLine.category, FixedLine.id.asc()).all()
    return [FixedLineOut(
        id=i.id, 
        label=i.label, 
        amount=i.amount, 
        freq=i.freq, 
        split_mode=i.split_mode, 
        split1=i.split1, 
        split2=i.split2, 
        category=i.category,
        active=i.active
    ) for i in items]

@router.post("", response_model=FixedLineOut)
async def create_fixed_line(payload: FixedLineIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Create a new fixed expense line
    
    Creates a new fixed expense line with the provided details.
    """
    logger.info(f"Création ligne fixe '{payload.label}' catégorie '{payload.category}' par utilisateur: {current_user.username}")
    f = FixedLine(
        label=payload.label, 
        amount=payload.amount, 
        freq=payload.freq,
        split_mode=payload.split_mode, 
        split1=payload.split1, 
        split2=payload.split2, 
        category=payload.category,
        active=payload.active
    )
    db.add(f); db.commit(); db.refresh(f)
    return FixedLineOut(
        id=f.id, 
        label=f.label, 
        amount=f.amount, 
        freq=f.freq, 
        split_mode=f.split_mode, 
        split1=f.split1, 
        split2=f.split2, 
        category=f.category,
        active=f.active
    )

@router.get("/{lid}", response_model=FixedLineOut)
async def get_fixed_line(lid: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get a specific fixed expense line by ID
    
    Returns the details of a single fixed expense line.
    """
    f = db.query(FixedLine).filter(FixedLine.id == lid).first()
    if not f:
        raise HTTPException(status_code=404, detail="Ligne fixe introuvable")
    
    return FixedLineOut(
        id=f.id, 
        label=f.label, 
        amount=f.amount, 
        freq=f.freq, 
        split_mode=f.split_mode, 
        split1=f.split1, 
        split2=f.split2, 
        category=f.category,
        active=f.active
    )

@router.patch("/{lid}", response_model=FixedLineOut)
async def update_fixed_line(lid: int, payload: FixedLineIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Update an existing fixed expense line (PATCH method)
    
    Updates the specified fixed expense line with new values.
    """
    logger.info(f"Mise à jour ligne fixe {lid} par utilisateur: {current_user.username}")
    f = db.query(FixedLine).filter(FixedLine.id == lid).first()
    if not f: 
        raise HTTPException(status_code=404, detail="Ligne fixe introuvable")
    
    # Mise à jour avec validation
    for k, v in payload.dict().items():
        setattr(f, k, v)
    
    db.add(f); db.commit(); db.refresh(f)
    logger.info(f"Ligne fixe {lid} mise à jour: '{f.label}' - {f.category}")
    
    return FixedLineOut(
        id=f.id, 
        label=f.label, 
        amount=f.amount, 
        freq=f.freq, 
        split_mode=f.split_mode, 
        split1=f.split1, 
        split2=f.split2, 
        category=f.category,
        active=f.active
    )

@router.put("/{lid}", response_model=FixedLineOut)
async def replace_fixed_line(lid: int, payload: FixedLineIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Replace an existing fixed expense line (PUT method)
    
    Completely replaces the specified fixed expense line with new values.
    Functionally identical to PATCH but follows REST semantics.
    """
    logger.info(f"Remplacement ligne fixe {lid} par utilisateur: {current_user.username}")
    f = db.query(FixedLine).filter(FixedLine.id == lid).first()
    if not f: 
        raise HTTPException(status_code=404, detail="Ligne fixe introuvable")
    
    # Mise à jour complète avec validation
    for k, v in payload.dict().items():
        setattr(f, k, v)
    
    db.add(f); db.commit(); db.refresh(f)
    logger.info(f"Ligne fixe {lid} remplacée: '{f.label}' - {f.category}")
    
    return FixedLineOut(
        id=f.id, 
        label=f.label, 
        amount=f.amount, 
        freq=f.freq, 
        split_mode=f.split_mode, 
        split1=f.split1, 
        split2=f.split2, 
        category=f.category,
        active=f.active
    )

@router.delete("/{lid}")
async def delete_fixed_line(lid: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Delete a fixed expense line
    
    Permanently removes the specified fixed expense line and handles related mappings.
    """
    logger.info(f"Suppression ligne fixe {lid} par utilisateur: {current_user.username}")
    f = db.query(FixedLine).filter(FixedLine.id == lid).first()
    if not f: 
        raise HTTPException(status_code=404, detail="Ligne fixe introuvable")
    
    # Import TagFixedLineMapping locally to avoid circular imports
    try:
        from models.database import TagFixedLineMapping
        
        # First, handle related tag mappings
        related_mappings = db.query(TagFixedLineMapping).filter(
            TagFixedLineMapping.fixed_line_id == lid
        ).all()
        
        if related_mappings:
            logger.info(f"Trouvé {len(related_mappings)} mappings liés à supprimer")
            for mapping in related_mappings:
                logger.info(f"Suppression mapping tag '{mapping.tag_name}' -> ligne fixe {lid}")
                db.delete(mapping)
        
        # Now delete the fixed line
        logger.info(f"Suppression confirmée: '{f.label}' - {f.category}")
        db.delete(f)
        db.commit()
        
        return {
            "ok": True, 
            "message": f"Ligne fixe '{f.label}' supprimée",
            "related_mappings_deleted": len(related_mappings)
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de la ligne fixe {lid}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression: {str(e)}"
        )

@router.get("/stats/by-category")
async def get_fixed_lines_stats_by_category(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get fixed expense statistics grouped by category
    
    Returns statistical data about fixed expenses organized by category,
    including count and monthly totals.
    """
    # Statistiques par catégorie
    stats = db.query(
        FixedLine.category,
        func.count(FixedLine.id).label('count'),
        func.sum(FixedLine.amount).label('total_amount')
    ).filter(
        FixedLine.active == True
    ).group_by(FixedLine.category).all()
    
    # Conversion en montants mensuels
    monthly_stats = []
    for cat, count, total in stats:
        # Calculer le total mensuel pour cette catégorie
        lines = db.query(FixedLine).filter(
            FixedLine.category == cat, 
            FixedLine.active == True
        ).all()
        
        monthly_total = 0.0
        for line in lines:
            if line.freq == "mensuelle":
                monthly_total += line.amount
            elif line.freq == "trimestrielle":
                monthly_total += (line.amount or 0.0) / 3.0
            else:  # annuelle
                monthly_total += (line.amount or 0.0) / 12.0
        
        monthly_stats.append({
            "category": cat,
            "count": count,
            "monthly_total": round(monthly_total, 2)
        })
    
    # Total général
    global_monthly_total = sum(s["monthly_total"] for s in monthly_stats)
    
    return {
        "by_category": monthly_stats,
        "global_monthly_total": round(global_monthly_total, 2),
        "total_lines": sum(s["count"] for s in monthly_stats)
    }