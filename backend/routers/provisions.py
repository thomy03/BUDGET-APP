"""
Provisions router for Budget Famille v2.3
Handles custom provisions management
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dependencies.auth import get_current_user
from dependencies.database import get_db
from audit_logger import get_audit_logger, AuditEventType

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/provisions",
    tags=["provisions"],
    responses={404: {"description": "Not found"}}
)

# Import models and schemas
from models.database import CustomProvision, Config
from models.schemas import CustomProvisionResponse, CustomProvisionCreate, CustomProvisionUpdate, CustomProvisionSummary
from services.calculations import calculate_provision_amount, calculate_provisions_summary
from utils.core_functions import ensure_default_config

@router.get("", response_model=List[CustomProvisionResponse])
def list_provisions(
    active_only: bool = True,
    category: Optional[str] = None,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """List all custom provisions for the current user"""
    logger.info(f"Liste provisions demandée par utilisateur: {current_user.username}")
    
    query = db.query(CustomProvision).filter(CustomProvision.created_by == current_user.username)
    
    if active_only:
        query = query.filter(CustomProvision.is_active == True)
    
    if category:
        query = query.filter(CustomProvision.category == category)
    
    provisions = query.order_by(CustomProvision.display_order, CustomProvision.name).all()
    
    # Calculer les montants pour chaque provision
    config = ensure_default_config(db)
    result = []
    
    for provision in provisions:
        monthly_amount, _, _ = calculate_provision_amount(provision, config)
        
        # Calcul du pourcentage de progression
        progress_percentage = None
        if provision.target_amount and provision.target_amount > 0:
            progress_percentage = min(100.0, (provision.current_amount / provision.target_amount) * 100)
        
        provision_response = CustomProvisionResponse(
            id=provision.id,
            name=provision.name,
            description=provision.description,
            percentage=provision.percentage,
            base_calculation=provision.base_calculation,
            fixed_amount=provision.fixed_amount,
            split_mode=provision.split_mode,
            split_member1=provision.split_member1,
            split_member2=provision.split_member2,
            icon=provision.icon,
            color=provision.color,
            display_order=provision.display_order,
            is_active=provision.is_active,
            is_temporary=provision.is_temporary,
            start_date=provision.start_date,
            end_date=provision.end_date,
            target_amount=provision.target_amount,
            category=provision.category,
            current_amount=provision.current_amount,
            created_at=provision.created_at,
            updated_at=provision.updated_at,
            created_by=provision.created_by,
            monthly_amount=monthly_amount,
            progress_percentage=progress_percentage
        )
        result.append(provision_response)
    
    return result

@router.post("", response_model=CustomProvisionResponse)
def create_provision(
    payload: CustomProvisionCreate,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Create a new custom provision"""
    audit_logger = get_audit_logger()
    logger.info(f"Création provision '{payload.name}' par utilisateur: {current_user.username}")
    
    # Vérifier qu'il n'y a pas de doublons de nom pour cet utilisateur
    existing = db.query(CustomProvision).filter(
        CustomProvision.created_by == current_user.username,
        CustomProvision.name == payload.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Une provision nommée '{payload.name}' existe déjà"
        )
    
    # Créer la nouvelle provision
    provision = CustomProvision(
        name=payload.name,
        description=payload.description,
        percentage=payload.percentage,
        base_calculation=payload.base_calculation,
        fixed_amount=payload.fixed_amount,
        split_mode=payload.split_mode,
        split_member1=payload.split_member1,
        split_member2=payload.split_member2,
        icon=payload.icon,
        color=payload.color,
        display_order=payload.display_order,
        is_active=payload.is_active,
        is_temporary=payload.is_temporary,
        start_date=payload.start_date,
        end_date=payload.end_date,
        target_amount=payload.target_amount,
        category=payload.category,
        created_by=current_user.username
    )
    
    db.add(provision)
    db.commit()
    db.refresh(provision)
    
    # Log audit
    audit_logger.log_event(
        AuditEventType.CONFIG_UPDATE,  # Or create PROVISION_CREATE
        username=current_user.username,
        details={"provision_name": provision.name, "action": "create"},
        success=True
    )
    
    logger.info(f"✅ Provision créée avec ID: {provision.id}")
    
    # Calculate amounts for response
    config = ensure_default_config(db)
    monthly_amount, _, _ = calculate_provision_amount(provision, config)
    progress_percentage = None
    if provision.target_amount and provision.target_amount > 0:
        progress_percentage = min(100.0, (provision.current_amount / provision.target_amount) * 100)
    
    return CustomProvisionResponse(
        id=provision.id,
        name=provision.name,
        description=provision.description,
        percentage=provision.percentage,
        base_calculation=provision.base_calculation,
        fixed_amount=provision.fixed_amount,
        split_mode=provision.split_mode,
        split_member1=provision.split_member1,
        split_member2=provision.split_member2,
        icon=provision.icon,
        color=provision.color,
        display_order=provision.display_order,
        is_active=provision.is_active,
        is_temporary=provision.is_temporary,
        start_date=provision.start_date,
        end_date=provision.end_date,
        target_amount=provision.target_amount,
        category=provision.category,
        current_amount=provision.current_amount,
        created_at=provision.created_at,
        updated_at=provision.updated_at,
        created_by=provision.created_by,
        monthly_amount=monthly_amount,
        progress_percentage=progress_percentage
    )

@router.get("/summary", response_model=CustomProvisionSummary)
def get_provisions_summary_endpoint(
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Get provisions summary statistics"""
    logger.info(f"Résumé provisions demandé par utilisateur: {current_user.username}")
    
    config = ensure_default_config(db)
    summary = calculate_provisions_summary(db, config)
    
    logger.info(f"Résumé provisions calculé: {summary.total_monthly_amount}€/mois")
    return summary