"""
Configuration router for Budget Famille v2.3
Handles application configuration management
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user
from dependencies.database import get_db
from audit_logger import get_audit_logger, AuditEventType

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/config",
    tags=["configuration"],
    responses={404: {"description": "Not found"}}
)

# Import models and dependencies
from models.database import Config
from models.schemas import ConfigIn, ConfigOut
from utils.core_functions import ensure_default_config

def _build_config_response(cfg: Config) -> ConfigOut:
    """Build configuration response"""
    return ConfigOut(
        id=cfg.id,
        member1=cfg.member1,
        member2=cfg.member2,
        rev1=cfg.rev1,
        rev2=cfg.rev2,
        split_mode=cfg.split_mode,
        split1=cfg.split1,
        split2=cfg.split2,
        other_split_mode=cfg.other_split_mode,
        var_percent=cfg.var_percent,
        max_var=cfg.max_var,
        min_fixed=cfg.min_fixed,
        created_at=cfg.created_at,
        updated_at=cfg.updated_at
    )

@router.get("", response_model=ConfigOut)
def get_config(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get current application configuration
    
    Returns the current configuration settings for the authenticated user.
    """
    cfg = ensure_default_config(db)
    return _build_config_response(cfg)

@router.post("", response_model=ConfigOut)
def update_config(payload: ConfigIn, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Update application configuration
    
    Updates the configuration settings with the provided values.
    Logs the changes for audit purposes.
    """
    audit_logger = get_audit_logger()
    logger.info(f"Configuration mise à jour par utilisateur: {current_user.username}")
    
    cfg = ensure_default_config(db)
    changes = {}
    for k, v in payload.dict().items():
        old_value = getattr(cfg, k, None)
        if old_value != v:
            changes[k] = {"old": old_value, "new": v}
        setattr(cfg, k, v)
    
    db.add(cfg); db.commit(); db.refresh(cfg)
    
    audit_logger.log_event(
        AuditEventType.CONFIG_UPDATE,
        username=current_user.username,
        details={"changes_count": len(changes)},
        success=True
    )
    
    cfg = ensure_default_config(db)
    return _build_config_response(cfg)