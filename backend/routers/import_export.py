"""
Import/Export router for Budget Famille v2.3
Handles CSV import and data export functionality
"""
import json
import logging
import pandas as pd
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


# =============================================================================
# PREVIEW IMPORT - Prévisualisation avant import définitif
# =============================================================================

from pydantic import BaseModel, Field
from typing import Dict, Any


class ImportPreviewTransaction(BaseModel):
    """Transaction preview with validation status"""
    row_number: int
    date: Optional[str]
    label: Optional[str]
    amount: Optional[float]
    month: Optional[str]
    is_valid: bool = True
    validation_errors: List[str] = []


class ImportPreviewResponse(BaseModel):
    """Response for import preview"""
    success: bool
    filename: str
    file_type: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    months_detected: List[str]
    months_summary: Dict[str, int]  # {month: transaction_count}
    sample_transactions: List[ImportPreviewTransaction]
    potential_duplicates: List[Dict[str, Any]]
    validation_warnings: List[str]
    columns_detected: List[str]
    ready_to_import: bool


@router.post("/import/preview", response_model=ImportPreviewResponse)
def preview_import_file(
    file: UploadFile = File(...),
    sample_size: int = 10,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Prévisualiser un fichier CSV/XLSX avant import.

    Cette opération analyse le fichier SANS modifier la base de données.
    Permet de vérifier :
    - Structure du fichier et colonnes détectées
    - Mois présents et nombre de transactions par mois
    - Validation des données (dates, montants)
    - Détection des doublons potentiels avec les données existantes
    - Aperçu des premières transactions

    **Paramètres :**
    - file: Fichier CSV ou XLSX à prévisualiser
    - sample_size: Nombre de transactions à afficher en aperçu (défaut: 10)

    **Réponse :**
    - ready_to_import: Indique si le fichier peut être importé
    - months_summary: Nombre de transactions par mois détecté
    - potential_duplicates: Transactions qui existent déjà en base
    - validation_warnings: Avertissements (lignes invalides, etc.)
    """
    logger.info(f"Preview import fichier '{file.filename}' par utilisateur: {current_user.username}")

    try:
        # Validation sécurité
        if not validate_file_security(file):
            raise HTTPException(status_code=400, detail="Fichier non autorisé ou dangereux")

        # Detect file type
        file_ext = file.filename.lower().rsplit('.', 1)[-1] if '.' in file.filename else ''

        if file_ext in ('xlsx', 'xls'):
            # Use smart parser for Excel files
            from services.smart_parser import get_smart_parser
            content = file.file.read()
            file.file.seek(0)
            parser = get_smart_parser()
            result = parser.parse(content, file.filename)

            if not result.success or not result.transactions:
                return ImportPreviewResponse(
                    success=False,
                    filename=file.filename,
                    file_type="xlsx",
                    total_rows=0,
                    valid_rows=0,
                    invalid_rows=0,
                    months_detected=[],
                    months_summary={},
                    sample_transactions=[],
                    potential_duplicates=[],
                    validation_warnings=[f"Erreur parsing XLSX: {result.errors}"],
                    columns_detected=[],
                    ready_to_import=False
                )

            # Convert to DataFrame for unified processing
            data = []
            for tx in result.transactions:
                data.append({
                    'date': tx.date_op,
                    'label': tx.label,
                    'amount': tx.amount,
                    'month': tx.date_op.strftime("%Y-%m") if tx.date_op else None
                })
            df = pd.DataFrame(data)
            columns_detected = list(df.columns)
        else:
            # Lecture robuste du CSV
            df = robust_read_csv(file)
            columns_detected = list(df.columns)

        # Détection automatique des colonnes
        date_col = None
        label_col = None
        amount_col = None

        for col in df.columns:
            col_lower = col.lower()
            if 'date' in col_lower and date_col is None:
                date_col = col
            elif any(x in col_lower for x in ['libel', 'label', 'description', 'libell']) and label_col is None:
                label_col = col
            elif any(x in col_lower for x in ['montant', 'amount', 'credit', 'debit']) and amount_col is None:
                amount_col = col

        # Process rows and detect months
        months_summary: Dict[str, int] = {}
        sample_transactions: List[ImportPreviewTransaction] = []
        validation_warnings: List[str] = []
        valid_rows = 0
        invalid_rows = 0

        for idx, row in df.iterrows():
            try:
                # Extract values with fallbacks
                date_val = str(row.get(date_col, '')) if date_col else None
                label_val = str(row.get(label_col, '')) if label_col else None
                amount_val = row.get(amount_col) if amount_col else None

                # Try to parse amount
                if amount_val is not None:
                    if isinstance(amount_val, str):
                        amount_val = float(amount_val.replace(',', '.').replace(' ', ''))
                    else:
                        amount_val = float(amount_val)

                # Detect month from date
                month_val = None
                if date_val:
                    import re
                    # Try YYYY-MM-DD format
                    match = re.search(r'(\d{4})-(\d{2})', date_val)
                    if match:
                        month_val = f"{match.group(1)}-{match.group(2)}"
                    else:
                        # Try DD/MM/YYYY format
                        match = re.search(r'(\d{2})/(\d{2})/(\d{4})', date_val)
                        if match:
                            month_val = f"{match.group(3)}-{match.group(2)}"

                # Track months
                if month_val:
                    months_summary[month_val] = months_summary.get(month_val, 0) + 1

                # Validation
                errors = []
                is_valid = True

                if not date_val or date_val == 'nan':
                    errors.append("Date manquante")
                    is_valid = False
                if not label_val or label_val == 'nan':
                    errors.append("Libellé manquant")
                    is_valid = False
                if amount_val is None or pd.isna(amount_val):
                    errors.append("Montant invalide")
                    is_valid = False

                if is_valid:
                    valid_rows += 1
                else:
                    invalid_rows += 1
                    if len(validation_warnings) < 10:
                        validation_warnings.append(f"Ligne {idx + 2}: {', '.join(errors)}")

                # Add to samples
                if len(sample_transactions) < sample_size:
                    sample_transactions.append(ImportPreviewTransaction(
                        row_number=idx + 2,  # +2 for header + 1-indexed
                        date=date_val if date_val and date_val != 'nan' else None,
                        label=label_val if label_val and label_val != 'nan' else None,
                        amount=amount_val if amount_val and not pd.isna(amount_val) else None,
                        month=month_val,
                        is_valid=is_valid,
                        validation_errors=errors
                    ))

            except Exception as e:
                invalid_rows += 1
                if len(validation_warnings) < 10:
                    validation_warnings.append(f"Ligne {idx + 2}: Erreur de parsing - {str(e)}")

        # Check for potential duplicates
        potential_duplicates = []
        months_detected = sorted(months_summary.keys())

        for month in months_detected[:3]:  # Check first 3 months only for performance
            existing_count = db.query(Transaction).filter(
                Transaction.month == month
            ).count()

            if existing_count > 0:
                potential_duplicates.append({
                    "month": month,
                    "existing_transactions": existing_count,
                    "new_transactions": months_summary[month],
                    "warning": f"Le mois {month} contient déjà {existing_count} transactions. L'import les remplacera."
                })

        # Determine if ready to import
        ready_to_import = (
            valid_rows > 0 and
            len(months_detected) > 0 and
            invalid_rows / max(1, valid_rows + invalid_rows) < 0.2  # Less than 20% invalid
        )

        return ImportPreviewResponse(
            success=True,
            filename=file.filename,
            file_type=file_ext or "csv",
            total_rows=len(df),
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            months_detected=months_detected,
            months_summary=months_summary,
            sample_transactions=sample_transactions,
            potential_duplicates=potential_duplicates,
            validation_warnings=validation_warnings,
            columns_detected=columns_detected,
            ready_to_import=ready_to_import
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur preview import: {e}")
        return ImportPreviewResponse(
            success=False,
            filename=file.filename,
            file_type=file_ext if 'file_ext' in dir() else "unknown",
            total_rows=0,
            valid_rows=0,
            invalid_rows=0,
            months_detected=[],
            months_summary={},
            sample_transactions=[],
            potential_duplicates=[],
            validation_warnings=[f"Erreur lors de la prévisualisation: {str(e)}"],
            columns_detected=[],
            ready_to_import=False
        )


@router.post("/import", response_model=ImportResponse)
def import_file(file: UploadFile = File(...), current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Import CSV/XLSX file with transactions

    Uploads and processes a CSV or XLSX file containing transaction data.
    Performs validation, duplicate detection, and data import.
    """
    import uuid
    import datetime as dt
    from services.smart_parser import get_smart_parser

    logger.info(f"Début import fichier '{file.filename}' par utilisateur: {current_user.username}")

    try:
        # Validation sécurité
        if not validate_file_security(file):
            raise HTTPException(status_code=400, detail="Fichier non autorisé ou dangereux")

        # Detect file type
        file_ext = file.filename.lower().rsplit('.', 1)[-1] if '.' in file.filename else ''

        if file_ext in ('xlsx', 'xls'):
            # Use smart parser for Excel files
            content = file.file.read()
            file.file.seek(0)
            parser = get_smart_parser()
            result = parser.parse(content, file.filename)

            if not result.success or not result.transactions:
                raise HTTPException(status_code=400, detail=f"Erreur lors du parsing XLSX: {result.errors}")

            # Convert ParsedTransaction to DataFrame-like structure for compatibility
            data = []
            for tx in result.transactions:
                data.append({
                    'date': tx.date_op,
                    'label': tx.label,
                    'amount': tx.amount,
                    'month': tx.date_op.strftime("%Y-%m") if tx.date_op else None
                })
            df = pd.DataFrame(data)
            logger.info(f"XLSX parsé avec succès: {len(df)} transactions")
        else:
            # Lecture robuste du CSV
            df = robust_read_csv(file)
            logger.info(f"CSV lu avec succès: {len(df)} lignes")
        
        # Détection des mois
        months_data = detect_months_with_metadata(df)
        logger.info(f"DEBUG: months_data type={type(months_data)}, value={months_data}")
        if not months_data:
            raise HTTPException(status_code=400, detail="Aucun mois détecté dans le fichier")
        
        # Mode ANNULE ET REMPLACE - pas de vérification de doublons
        duplicate_info = {'duplicates_count': 0, 'exact_matches': 0}
        
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
        
        # ANNULE ET REMPLACE: Supprimer les transactions existantes pour les mois détectés
        logger.info(f"🔄 Mode ANNULE ET REMPLACE pour les mois: {months_list}")
        for month in months_list:
            existing_count = db.query(Transaction).filter(
                Transaction.month == month
            ).count()
            
            if existing_count > 0:
                logger.info(f"  ❌ Suppression de {existing_count} transactions existantes pour {month}")
                db.query(Transaction).filter(
                    Transaction.month == month
                ).delete()
        
        db.flush()  # Appliquer les suppressions avant d'ajouter les nouvelles
        
        # IMPORTANT: Sauvegarder les transactions dans la base de données
        transactions_created = 0
        # Dictionnaire pour compter les nouvelles transactions par mois
        new_transactions_by_month = {}
        
        # Log des colonnes disponibles pour debug
        logger.info(f"Colonnes du CSV: {df.columns.tolist()}")
        
        # Détection automatique des colonnes
        date_col = None
        label_col = None
        amount_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if 'date' in col_lower and date_col is None:
                date_col = col
            elif any(x in col_lower for x in ['libel', 'label', 'description', 'libell']) and label_col is None:
                label_col = col
            elif any(x in col_lower for x in ['montant', 'amount', 'debit', 'credit', 'solde']) and amount_col is None:
                amount_col = col
        
        logger.info(f"Colonnes détectées - Date: {date_col}, Label: {label_col}, Montant: {amount_col}")
        
        if not all([date_col, label_col, amount_col]):
            logger.error(f"Colonnes manquantes! Date: {date_col}, Label: {label_col}, Montant: {amount_col}")
        
        for idx, row in df.iterrows():
            try:
                # Extraire les données avec les colonnes détectées
                date_val = row.get(date_col) if date_col else None
                label_val = row.get(label_col) if label_col else f"Transaction {idx}"
                amount_val = row.get(amount_col) if amount_col else 0
                
                # Parser la date
                date_op = pd.to_datetime(date_val, errors='coerce', dayfirst=True)
                if pd.isna(date_op):
                    logger.warning(f"Date invalide ligne {idx}: {date_val}")
                    continue
                
                # Convertir le montant
                if isinstance(amount_val, str):
                    amount_val = amount_val.replace(',', '.').replace(' ', '')
                amount = float(amount_val) if amount_val else 0.0
                
                month = date_op.strftime("%Y-%m")
                
                # Pas de vérification de doublons car on fait un ANNULE ET REMPLACE
                # Créer l'objet Transaction
                # is_expense est True si le montant est négatif (dépense)
                transaction = Transaction(
                    label=str(label_val),
                    amount=amount,
                    date_op=date_op.date(),  # Stocker comme date, pas datetime
                    month=month,
                    tags="Non classé",  # Tag par défaut
                    category="VARIABLE",
                    category_parent="VARIABLE",
                    exclude=False,
                    expense_type="VARIABLE",
                    is_expense=(amount < 0),  # Définir is_expense basé sur le signe du montant
                    import_id=import_id
                )
                db.add(transaction)
                transactions_created += 1
                
                # Compter les nouvelles transactions par mois
                if month not in new_transactions_by_month:
                    new_transactions_by_month[month] = 0
                new_transactions_by_month[month] += 1
                
                if transactions_created <= 3:  # Log les 3 premières pour debug
                    logger.info(f"✅ Transaction créée: {label_val} - {amount}€ - {date_op.strftime('%Y-%m-%d')}")
                    
            except Exception as e:
                logger.warning(f"Erreur ligne {idx}: {e}")
                continue
        
        db.commit()
        
        logger.info(f"✅ Import terminé: ID={import_id}, {transactions_created} transactions importées (mode ANNULE ET REMPLACE)")
        
        # Préparation des données de réponse avec le nombre RÉEL de transactions importées
        logger.info(f"DEBUG: Transactions importées par mois: {new_transactions_by_month}")
        
        # Préparer la réponse avec les transactions importées
        months_for_response = []
        
        if new_transactions_by_month:
            # Il y a des transactions importées
            for month in new_transactions_by_month.keys():
                # Trouver les métadonnées d'origine pour ce mois si elles existent
                original_month_data = None
                if isinstance(months_data, list):
                    for m in months_data:
                        if isinstance(m, dict) and m.get('month') == month:
                            original_month_data = m
                            break
                
                if original_month_data:
                    # Copier les métadonnées originales mais remplacer transaction_count
                    month_response = original_month_data.copy()
                    month_response['transaction_count'] = new_transactions_by_month[month]
                else:
                    # Créer des métadonnées minimales
                    month_response = {
                        'month': month,
                        'transaction_count': new_transactions_by_month[month],
                        'date_range': {'start': None, 'end': None},
                        'total_amount': 0.0,
                        'categories': []
                    }
                months_for_response.append(month_response)
        
        # Trier par mois décroissant
        months_for_response.sort(key=lambda x: x['month'], reverse=True)
        
        logger.info(f"DEBUG: months_for_response avec transactions importées: {months_for_response}")
        
        # Mode ANNULE ET REMPLACE - pas de doublons à signaler
        duplicate_info['duplicates_count'] = 0
        duplicate_info['exact_matches'] = 0
        
        if transactions_created > 0:
            message = f"Import réussi : {transactions_created} transactions importées (mode annule et remplace)"
        else:
            message = "Import terminé : aucune transaction trouvée"
        
        return ImportResponse(
            import_id=import_id,
            status="success",
            filename=file.filename,
            rows_processed=len(df),
            months_detected=months_for_response,
            duplicates_info=duplicate_info,
            validation_errors=[],
            message=message
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
    
    # Parse months_detected to match ImportMonth schema
    months_list = json.loads(import_meta.months_detected) if import_meta.months_detected else []
    months_formatted = []
    
    # If months are stored as simple strings, convert them to ImportMonth format
    for month_data in months_list:
        if isinstance(month_data, str):
            # Simple month string, create minimal ImportMonth structure
            months_formatted.append({
                "month": month_data,
                "transaction_count": 0,
                "date_range": {"start": None, "end": None},
                "total_amount": 0.0,
                "categories": []
            })
        elif isinstance(month_data, dict):
            # Already in correct format
            months_formatted.append(month_data)
    
    return ImportResponse(
        import_id=import_meta.id,
        status="completed",  # ImportMetadata doesn't have status field, assume completed
        filename=import_meta.filename,
        rows_processed=0,  # ImportMetadata doesn't have rows_imported field
        months_detected=months_formatted,
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