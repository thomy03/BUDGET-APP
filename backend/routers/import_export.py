"""
Import/Export router for Budget Famille v2.3
Handles CSV import and data export functionality
"""
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from auth import get_current_user
from dependencies.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["import-export"],
    responses={404: {"description": "Not found"}}
)

# Import models, schemas and functions
from models.database import ImportMetadata, ExportHistory, Transaction
from models.schemas import ImportResponse
from utils.core_functions import (
    validate_file_security, robust_read_csv, detect_months_with_metadata,
    check_duplicate_transactions, validate_csv_data
)
from export_engine import ExportManager, ExportRequest, ExportFilters

@router.post("/import", response_model=ImportResponse)
def import_file(file: UploadFile = File(...), current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Import CSV file with transactions
    
    Uploads and processes a CSV file containing transaction data.
    Performs validation, duplicate detection, and data import.
    """
    import uuid
    import datetime as dt
    
    logger.info(f"Début import fichier '{file.filename}' par utilisateur: {current_user.username}")
    
    try:
        # Validation sécurité
        if not validate_file_security(file):
            raise HTTPException(status_code=400, detail="Fichier non autorisé ou dangereux")
        
        # Lecture robuste du CSV
        df = robust_read_csv(file)
        logger.info(f"CSV lu avec succès: {len(df)} lignes")
        
        # Détection des mois
        months_data = detect_months_with_metadata(df)
        if not months_data:
            raise HTTPException(status_code=400, detail="Aucun mois détecté dans le fichier")
        
        # Vérification doublons
        duplicate_info = check_duplicate_transactions(df, db)
        
        # Validation données
        validation_errors = validate_csv_data(df)
        if validation_errors:
            raise HTTPException(status_code=400, detail=f"Erreurs de validation: {'; '.join(validation_errors)}")
        
        # Création métadonnées d'import
        import_id = str(uuid.uuid4())
        
        # Extraction des mois pour les métadonnées (correction du bug .keys())
        if isinstance(months_data, list):
            # months_data est une liste de dictionnaires avec métadonnées
            months_list = [month_dict['month'] for month_dict in months_data if isinstance(month_dict, dict) and 'month' in month_dict]
        else:
            # Compatibilité si c'est un dictionnaire
            months_list = list(months_data.keys())
        
        import_meta = ImportMetadata(
            id=import_id,
            filename=file.filename,
            created_at=dt.datetime.now().date(),
            user_id=current_user.username,
            months_detected=json.dumps(months_list),
            duplicates_count=duplicate_info.get('duplicates_count', 0),
            warnings=json.dumps(validation_errors) if validation_errors else None,
            processing_ms=0  # Will be updated at the end
        )
        
        db.add(import_meta)
        db.commit()
        
        logger.info(f"✅ Import terminé: ID={import_id}")
        
        # Préparation des données de réponse
        if isinstance(months_data, list):
            # months_data est une liste de dictionnaires avec métadonnées
            months_for_response = {month_dict['month']: month_dict for month_dict in months_data if isinstance(month_dict, dict) and 'month' in month_dict}
        else:
            # months_data est déjà un dictionnaire
            months_for_response = months_data
        
        return ImportResponse(
            import_id=import_id,
            status="success",
            filename=file.filename,
            rows_processed=len(df),
            months_detected=months_for_response,
            duplicates_info=duplicate_info,
            validation_errors=[],
            message="Import réussi"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur import: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'import: {str(e)}")

@router.get("/imports/{import_id}", response_model=ImportResponse)
def get_import_details(import_id: str, db: Session = Depends(get_db)):
    """
    Get details of a specific import operation
    
    Returns detailed information about a previous import operation.
    """
    import_meta = db.query(ImportMetadata).filter(ImportMetadata.id == import_id).first()
    if not import_meta:
        raise HTTPException(status_code=404, detail="Import introuvable")
    
    return ImportResponse(
        import_id=import_meta.id,
        status="completed",  # ImportMetadata doesn't have status field, assume completed
        filename=import_meta.filename,
        rows_processed=0,  # ImportMetadata doesn't have rows_imported field
        months_detected=json.loads(import_meta.months_detected) if import_meta.months_detected else [],
        duplicates_info={"duplicates_count": import_meta.duplicates_count},
        validation_errors=json.loads(import_meta.warnings) if import_meta.warnings else [],
        message="Détails de l'import récupérés"
    )

@router.post("/export")
def export_data(
    request: ExportRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export data in various formats
    
    Exports transaction data based on the specified filters and format.
    """
    try:
        export_manager = ExportManager()
        result = export_manager.export_data(request, db, current_user.username)
        
        # Log the export
        export_log = ExportHistory(
            export_id=result["export_id"],
            user_id=current_user.username,
            export_type=request.export_format.value,
            filters_applied=str(request.filters.dict() if request.filters else {}),
            file_path=result["file_path"],
            created_at=result["created_at"]
        )
        db.add(export_log)
        db.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/export/history")
def get_export_history(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get export history for the current user
    
    Returns a list of all export operations performed by the current user.
    """
    exports = db.query(ExportHistory).filter(
        ExportHistory.user_id == current_user.username
    ).order_by(ExportHistory.created_at.desc()).all()
    
    return {
        "exports": [
            {
                "export_id": exp.export_id,
                "export_type": exp.export_type,
                "created_at": exp.created_at.isoformat(),
                "file_path": exp.file_path,
                "filters_applied": exp.filters_applied
            }
            for exp in exports
        ]
    }