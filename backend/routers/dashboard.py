"""
Dashboard router for Budget Famille v2.3
Optimized endpoints for hierarchical dashboard with drill-down navigation
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from dependencies.auth import get_current_user
from dependencies.database import get_db
from services.redis_cache import get_redis_cache
from models.schemas import (
    DashboardSummaryResponse, 
    SavingsColumnResponse, 
    ExpensesColumnResponse,
    CategoryDrillDownResponse,
    DetailDrillDownResponse
)
from services.calculations import (
    calculate_provisions_total,
    calculate_fixed_lines_total,
    get_active_provisions,
    calculate_provision_amount
)
from utils.core_functions import ensure_default_config

logger = logging.getLogger(__name__)
redis_cache = get_redis_cache()

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    responses={404: {"description": "Not found"}}
)


# =====================================
# DASHBOARD SUMMARY (TOP LEVEL)
# =====================================

@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dashboard principal avec vue d'ensemble Épargne vs Dépenses
    
    Retourne:
    - Colonne Épargne: Total provisions, progression, nombre d'objectifs
    - Colonne Dépenses: Total charges fixes, répartition, nombre de postes
    - Comparaison: Ratio épargne/dépenses, solde disponible
    """
    cache_key = f"dashboard:summary:{current_user.username}"
    
    # Check cache first
    cached_data = redis_cache.get(cache_key)
    if cached_data:
        return cached_data
    
    try:
        config = ensure_default_config(db)
        
        # Calculate savings (provisions)
        total_savings, member1_savings, member2_savings = calculate_provisions_total(db, config)
        active_provisions = get_active_provisions(db)
        
        # Calculate progress for savings
        total_target = sum(p.target_amount or 0 for p in active_provisions)
        total_current = sum(p.current_amount or 0 for p in active_provisions)
        savings_progress = (total_current / total_target * 100) if total_target > 0 else 0
        
        # Calculate expenses (fixed lines)
        total_expenses, member1_expenses, member2_expenses = calculate_fixed_lines_total(db, config)
        
        from models.database import FixedLine
        active_fixed_lines = db.query(FixedLine).filter(FixedLine.active == True).all()
        
        # Summary response
        summary = DashboardSummaryResponse(
            # Savings column
            savings_total_monthly=total_savings,
            savings_member1_share=member1_savings,
            savings_member2_share=member2_savings,
            savings_count=len(active_provisions),
            savings_progress_percentage=savings_progress,
            savings_categories=_group_provisions_by_category(active_provisions, config),
            
            # Expenses column  
            expenses_total_monthly=total_expenses,
            expenses_member1_share=member1_expenses,
            expenses_member2_share=member2_expenses,
            expenses_count=len(active_fixed_lines),
            expenses_categories=_group_expenses_by_category(active_fixed_lines),
            
            # Comparison metrics
            savings_to_expenses_ratio=(total_savings / total_expenses * 100) if total_expenses > 0 else 0,
            total_monthly_outflow=total_savings + total_expenses,
            net_available=(config.rev1 + config.rev2) - (total_savings + total_expenses)
        )
        
        # Cache for 5 minutes (dashboard data changes frequently)
        redis_cache.set(cache_key, summary, ttl=300)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error calculating dashboard summary: {e}")
        raise HTTPException(status_code=500, detail="Erreur calcul dashboard")


# =====================================
# SAVINGS COLUMN (ÉPARGNE)
# =====================================

@router.get("/savings", response_model=SavingsColumnResponse)
async def get_savings_column(
    category: Optional[str] = Query(None, description="Filtrer par catégorie d'épargne"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Colonne Épargne du dashboard avec drill-down par catégorie
    
    Retourne les provisions d'épargne groupées par catégorie avec:
    - Vue globale par catégorie
    - Détails par provision dans chaque catégorie
    - Métriques de progression et objectifs
    """
    cache_key = f"dashboard:savings:{current_user.username}:{category or 'all'}"
    
    cached_data = redis_cache.get(cache_key)
    if cached_data:
        return cached_data
    
    try:
        config = ensure_default_config(db)
        provisions = get_active_provisions(db)
        
        if category:
            provisions = [p for p in provisions if p.category == category]
        
        # Group by category
        categories = {}
        for provision in provisions:
            cat = provision.category or "épargne"
            if cat not in categories:
                categories[cat] = {
                    "name": cat,
                    "provisions": [],
                    "total_monthly": 0,
                    "total_target": 0,
                    "total_current": 0,
                    "progress_percentage": 0
                }
            
            monthly_amount, _, _ = calculate_provision_amount(provision, config)
            progress = 0
            if provision.target_amount and provision.target_amount > 0:
                progress = min(100, (provision.current_amount or 0) / provision.target_amount * 100)
            
            categories[cat]["provisions"].append({
                "id": provision.id,
                "name": provision.name,
                "description": provision.description,
                "monthly_amount": monthly_amount,
                "target_amount": provision.target_amount or 0,
                "current_amount": provision.current_amount or 0,
                "progress_percentage": progress,
                "icon": provision.icon,
                "color": provision.color
            })
            
            categories[cat]["total_monthly"] += monthly_amount
            categories[cat]["total_target"] += provision.target_amount or 0
            categories[cat]["total_current"] += provision.current_amount or 0
        
        # Calculate category progress
        for cat_data in categories.values():
            if cat_data["total_target"] > 0:
                cat_data["progress_percentage"] = min(100, 
                    cat_data["total_current"] / cat_data["total_target"] * 100)
        
        response = SavingsColumnResponse(
            total_monthly_savings=sum(cat["total_monthly"] for cat in categories.values()),
            categories=list(categories.values()),
            total_provisions=len(provisions)
        )
        
        # Cache for 5 minutes
        redis_cache.set(cache_key, response, ttl=300)
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting savings column: {e}")
        raise HTTPException(status_code=500, detail="Erreur colonne épargne")


# =====================================
# EXPENSES COLUMN (DÉPENSES)
# =====================================

@router.get("/expenses", response_model=ExpensesColumnResponse)
async def get_expenses_column(
    category: Optional[str] = Query(None, description="Filtrer par catégorie de dépense"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Colonne Dépenses du dashboard avec drill-down par catégorie
    
    Retourne les charges fixes groupées par catégorie avec:
    - Vue globale par catégorie (logement, transport, etc.)
    - Détails par ligne de charge dans chaque catégorie
    - Répartition membre1/membre2
    """
    cache_key = f"dashboard:expenses:{current_user.username}:{category or 'all'}"
    
    cached_data = redis_cache.get(cache_key)
    if cached_data:
        return cached_data
    
    try:
        from models.database import FixedLine
        
        query = db.query(FixedLine).filter(FixedLine.active == True)
        if category:
            query = query.filter(FixedLine.category == category)
        
        fixed_lines = query.all()
        
        # Group by category
        categories = {}
        for line in fixed_lines:
            cat = line.category or "autres"
            if cat not in categories:
                categories[cat] = {
                    "name": cat,
                    "fixed_lines": [],
                    "monthly_total": 0,
                    "member1_total": 0,
                    "member2_total": 0
                }
            
            # Convert to monthly amount
            if line.freq == "mensuelle":
                monthly_amount = line.amount
            elif line.freq == "trimestrielle":
                monthly_amount = line.amount / 3.0
            elif line.freq == "annuelle":
                monthly_amount = line.amount / 12.0
            else:
                monthly_amount = line.amount
            
            # Calculate member split
            config = ensure_default_config(db)
            from services.calculations import split_amount, get_split
            r1, r2 = get_split(config)
            member1_amount, member2_amount = split_amount(
                monthly_amount, line.split_mode, r1, r2, line.split1, line.split2
            )
            
            categories[cat]["fixed_lines"].append({
                "id": line.id,
                "label": line.label,
                "monthly_amount": monthly_amount,
                "member1_amount": member1_amount,
                "member2_amount": member2_amount,
                "frequency": line.freq,
                "split_mode": line.split_mode
            })
            
            categories[cat]["monthly_total"] += monthly_amount
            categories[cat]["member1_total"] += member1_amount
            categories[cat]["member2_total"] += member2_amount
        
        response = ExpensesColumnResponse(
            total_monthly_expenses=sum(cat["monthly_total"] for cat in categories.values()),
            categories=list(categories.values()),
            total_fixed_lines=len(fixed_lines)
        )
        
        # Cache for 5 minutes
        redis_cache.set(cache_key, response, ttl=300)
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting expenses column: {e}")
        raise HTTPException(status_code=500, detail="Erreur colonne dépenses")


# =====================================
# DRILL-DOWN ENDPOINTS
# =====================================

@router.get("/category/{category_name}", response_model=CategoryDrillDownResponse)
async def get_category_drill_down(
    category_name: str,
    column_type: str = Query(..., regex="^(savings|expenses)$", description="Type de colonne"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Drill-down dans une catégorie spécifique
    
    Retourne le détail complet d'une catégorie avec tous ses éléments
    """
    cache_key = f"dashboard:category:{column_type}:{category_name}:{current_user.username}"
    
    cached_data = redis_cache.get(cache_key)
    if cached_data:
        return cached_data
    
    try:
        if column_type == "savings":
            return _get_savings_category_details(category_name, db, cache_key)
        else:
            return _get_expenses_category_details(category_name, db, cache_key)
            
    except Exception as e:
        logger.error(f"Error getting category drill-down: {e}")
        raise HTTPException(status_code=500, detail="Erreur drill-down catégorie")


@router.get("/detail/{item_type}/{item_id}", response_model=DetailDrillDownResponse)
async def get_detail_drill_down(
    item_type: str = Query(..., regex="^(provision|fixed_line)$"),
    item_id: int = ...,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Drill-down vers le détail d'un élément spécifique
    
    Retourne tous les détails d'une provision ou ligne fixe
    """
    cache_key = f"dashboard:detail:{item_type}:{item_id}:{current_user.username}"
    
    cached_data = redis_cache.get(cache_key)
    if cached_data:
        return cached_data
    
    try:
        if item_type == "provision":
            return _get_provision_details(item_id, db, cache_key)
        else:
            return _get_fixed_line_details(item_id, db, cache_key)
            
    except Exception as e:
        logger.error(f"Error getting detail drill-down: {e}")
        raise HTTPException(status_code=500, detail="Erreur drill-down détail")


# =====================================
# CACHE MANAGEMENT
# =====================================

@router.post("/cache/invalidate")
async def invalidate_dashboard_cache(
    current_user = Depends(get_current_user)
):
    """Invalider le cache dashboard pour l'utilisateur actuel"""
    try:
        pattern = f"dashboard:*:{current_user.username}*"
        deleted_count = redis_cache.delete_pattern(pattern)
        
        return {
            "message": "Cache dashboard invalidé",
            "deleted_entries": deleted_count
        }
    except Exception as e:
        logger.error(f"Error invalidating dashboard cache: {e}")
        raise HTTPException(status_code=500, detail="Erreur invalidation cache")


# =====================================
# HELPER FUNCTIONS
# =====================================

def _group_provisions_by_category(provisions: List, config) -> List[Dict]:
    """Group provisions by category for summary"""
    categories = {}
    
    for provision in provisions:
        cat = provision.category or "épargne"
        if cat not in categories:
            categories[cat] = {"name": cat, "count": 0, "monthly_total": 0}
        
        monthly_amount, _, _ = calculate_provision_amount(provision, config)
        categories[cat]["count"] += 1
        categories[cat]["monthly_total"] += monthly_amount
    
    return list(categories.values())


def _group_expenses_by_category(fixed_lines: List) -> List[Dict]:
    """Group fixed lines by category for summary"""
    categories = {}
    
    for line in fixed_lines:
        cat = line.category or "autres"
        if cat not in categories:
            categories[cat] = {"name": cat, "count": 0, "monthly_total": 0}
        
        # Convert to monthly
        if line.freq == "mensuelle":
            monthly_amount = line.amount
        elif line.freq == "trimestrielle":
            monthly_amount = line.amount / 3.0
        elif line.freq == "annuelle":
            monthly_amount = line.amount / 12.0
        else:
            monthly_amount = line.amount
        
        categories[cat]["count"] += 1
        categories[cat]["monthly_total"] += monthly_amount
    
    return list(categories.values())


def _get_savings_category_details(category_name: str, db: Session, cache_key: str):
    """Get detailed view of savings category"""
    # Implementation for savings category drill-down
    provisions = db.query(CustomProvision).filter(
        CustomProvision.category == category_name,
        CustomProvision.is_active == True
    ).all()
    
    config = ensure_default_config(db)
    details = []
    
    for provision in provisions:
        monthly_amount, member1_amount, member2_amount = calculate_provision_amount(provision, config)
        progress = 0
        if provision.target_amount and provision.target_amount > 0:
            progress = min(100, (provision.current_amount or 0) / provision.target_amount * 100)
        
        details.append({
            "id": provision.id,
            "name": provision.name,
            "description": provision.description,
            "monthly_amount": monthly_amount,
            "member1_amount": member1_amount,
            "member2_amount": member2_amount,
            "target_amount": provision.target_amount or 0,
            "current_amount": provision.current_amount or 0,
            "progress_percentage": progress,
            "calculation_method": f"{provision.percentage}% of {provision.base_calculation}",
            "split_mode": provision.split_mode,
            "icon": provision.icon,
            "color": provision.color
        })
    
    response = CategoryDrillDownResponse(
        category_name=category_name,
        column_type="savings",
        items=details,
        total_monthly=sum(d["monthly_amount"] for d in details),
        items_count=len(details)
    )
    
    redis_cache.set(cache_key, response, ttl=300)
    return response


def _get_expenses_category_details(category_name: str, db: Session, cache_key: str):
    """Get detailed view of expenses category"""
    # Similar implementation for expenses category drill-down
    from models.database import FixedLine
    
    lines = db.query(FixedLine).filter(
        FixedLine.category == category_name,
        FixedLine.active == True
    ).all()
    
    config = ensure_default_config(db)
    from services.calculations import split_amount, get_split
    r1, r2 = get_split(config)
    
    details = []
    
    for line in lines:
        # Convert to monthly
        if line.freq == "mensuelle":
            monthly_amount = line.amount
        elif line.freq == "trimestrielle":
            monthly_amount = line.amount / 3.0
        elif line.freq == "annuelle":
            monthly_amount = line.amount / 12.0
        else:
            monthly_amount = line.amount
        
        member1_amount, member2_amount = split_amount(
            monthly_amount, line.split_mode, r1, r2, line.split1, line.split2
        )
        
        details.append({
            "id": line.id,
            "label": line.label,
            "monthly_amount": monthly_amount,
            "member1_amount": member1_amount,
            "member2_amount": member2_amount,
            "frequency": line.freq,
            "original_amount": line.amount,
            "split_mode": line.split_mode,
            "split1": line.split1,
            "split2": line.split2
        })
    
    response = CategoryDrillDownResponse(
        category_name=category_name,
        column_type="expenses",
        items=details,
        total_monthly=sum(d["monthly_amount"] for d in details),
        items_count=len(details)
    )
    
    redis_cache.set(cache_key, response, ttl=300)
    return response


def _get_provision_details(provision_id: int, db: Session, cache_key: str):
    """Get full details of a specific provision"""
    from models.database import CustomProvision
    
    provision = db.query(CustomProvision).filter(CustomProvision.id == provision_id).first()
    if not provision:
        raise HTTPException(status_code=404, detail="Provision not found")
    
    config = ensure_default_config(db)
    monthly_amount, member1_amount, member2_amount = calculate_provision_amount(provision, config)
    
    progress = 0
    if provision.target_amount and provision.target_amount > 0:
        progress = min(100, (provision.current_amount or 0) / provision.target_amount * 100)
    
    # Calculate time to goal
    months_to_goal = None
    if provision.target_amount and provision.current_amount and monthly_amount > 0:
        remaining = provision.target_amount - provision.current_amount
        if remaining > 0:
            months_to_goal = remaining / monthly_amount
    
    response = DetailDrillDownResponse(
        item_type="provision",
        item_id=provision_id,
        name=provision.name,
        details={
            "description": provision.description,
            "monthly_amount": monthly_amount,
            "member1_amount": member1_amount,
            "member2_amount": member2_amount,
            "target_amount": provision.target_amount or 0,
            "current_amount": provision.current_amount or 0,
            "progress_percentage": progress,
            "months_to_goal": months_to_goal,
            "calculation": {
                "percentage": provision.percentage,
                "base": provision.base_calculation,
                "fixed_amount": provision.fixed_amount
            },
            "split": {
                "mode": provision.split_mode,
                "member1": provision.split_member1,
                "member2": provision.split_member2
            },
            "visual": {
                "icon": provision.icon,
                "color": provision.color
            },
            "schedule": {
                "is_temporary": provision.is_temporary,
                "start_date": provision.start_date.isoformat() if provision.start_date else None,
                "end_date": provision.end_date.isoformat() if provision.end_date else None
            }
        }
    )
    
    redis_cache.set(cache_key, response, ttl=300)
    return response


def _get_fixed_line_details(line_id: int, db: Session, cache_key: str):
    """Get full details of a specific fixed line"""
    from models.database import FixedLine
    
    line = db.query(FixedLine).filter(FixedLine.id == line_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Fixed line not found")
    
    config = ensure_default_config(db)
    from services.calculations import split_amount, get_split
    r1, r2 = get_split(config)
    
    # Convert to monthly
    if line.freq == "mensuelle":
        monthly_amount = line.amount
    elif line.freq == "trimestrielle":
        monthly_amount = line.amount / 3.0
    elif line.freq == "annuelle":
        monthly_amount = line.amount / 12.0
    else:
        monthly_amount = line.amount
    
    member1_amount, member2_amount = split_amount(
        monthly_amount, line.split_mode, r1, r2, line.split1, line.split2
    )
    
    # Calculate annual cost
    annual_cost = monthly_amount * 12
    
    response = DetailDrillDownResponse(
        item_type="fixed_line",
        item_id=line_id,
        name=line.label,
        details={
            "category": line.category,
            "monthly_amount": monthly_amount,
            "member1_amount": member1_amount,
            "member2_amount": member2_amount,
            "original_amount": line.amount,
            "frequency": line.freq,
            "annual_cost": annual_cost,
            "split": {
                "mode": line.split_mode,
                "split1": line.split1,
                "split2": line.split2
            },
            "calculation": {
                "frequency_multiplier": {
                    "mensuelle": 1,
                    "trimestrielle": 1/3,
                    "annuelle": 1/12
                }.get(line.freq, 1),
                "original_to_monthly": f"{line.amount} ({line.freq}) = {monthly_amount} (mensuel)"
            }
        }
    )
    
    redis_cache.set(cache_key, response, ttl=300)
    return response