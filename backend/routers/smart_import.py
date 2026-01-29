"""
Smart Import Router for Budget Famille v4.1
Intelligent multi-format file import with automatic detection

Supports:
- CSV files (various bank formats)
- XLSX files (Excel)
- PDF files (bank statements)

Features:
- Auto-detect file format and bank source
- Preview mode with column detection
- Custom column mapping support
- Two-step import: analyze then confirm
"""

import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from auth import get_current_user
from dependencies.database import get_db
from models.database import ImportMetadata, Transaction
from services.smart_parser import get_smart_parser, ParseResult

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/smart-import",
    tags=["smart-import"],
    responses={404: {"description": "Not found"}}
)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ColumnMappingRequest(BaseModel):
    """Custom column mapping from user"""
    date: Optional[str] = Field(None, description="Column name for date")
    label: Optional[str] = Field(None, description="Column name for label/description")
    amount: Optional[str] = Field(None, description="Column name for amount (combined)")
    debit: Optional[str] = Field(None, description="Column name for debit")
    credit: Optional[str] = Field(None, description="Column name for credit")


class AnalyzeResponse(BaseModel):
    """Response from analyze endpoint"""
    success: bool
    session_id: str
    file_format: str
    bank_source: str
    column_mapping: Dict[str, Optional[str]]
    raw_columns: List[str]
    sample_data: List[Dict]
    transaction_count: int
    transactions_preview: List[Dict]
    errors: List[str]
    warnings: List[str]
    metadata: Dict


class ConfirmImportRequest(BaseModel):
    """Request to confirm and execute import"""
    session_id: str = Field(..., description="Session ID from analyze step")
    custom_mapping: Optional[ColumnMappingRequest] = Field(None, description="Override column mapping")
    confirm: bool = Field(True, description="Must be true to confirm import")


class ImportResultResponse(BaseModel):
    """Response after import execution"""
    success: bool
    import_id: str
    transactions_imported: int
    months_detected: List[str]
    message: str
    errors: List[str] = []
    warnings: List[str] = []


# In-memory session storage for analyze results
# In production, use Redis or database
_analyze_sessions: Dict[str, Dict] = {}


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_file(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 1: Analyze file and return preview

    This endpoint:
    - Detects file format (CSV, XLSX, PDF)
    - Detects bank source (BoursoBank, LCL, etc.)
    - Auto-maps columns to transaction fields
    - Returns sample data for user confirmation

    After analysis, use /confirm to execute the import.
    """
    logger.info(f"Smart import analyze: {file.filename} by user {current_user.username}")

    try:
        # Read file content
        content = await file.read()

        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fichier vide"
            )

        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fichier trop volumineux (max 10MB)"
            )

        # Parse with smart parser
        parser = get_smart_parser()
        result: ParseResult = parser.parse(content, file.filename)

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Store in session for later confirmation
        _analyze_sessions[session_id] = {
            "content": content,
            "filename": file.filename,
            "result": result,
            "user_id": current_user.username,
            "created_at": datetime.now(),
        }

        # Clean old sessions (older than 1 hour)
        now = datetime.now()
        expired = [
            sid for sid, data in _analyze_sessions.items()
            if (now - data["created_at"]).total_seconds() > 3600
        ]
        for sid in expired:
            del _analyze_sessions[sid]

        logger.info(f"Analyze complete: {result.file_format.value}, {result.bank_source.value}, {len(result.transactions)} transactions")

        return AnalyzeResponse(
            success=result.success,
            session_id=session_id,
            file_format=result.file_format.value,
            bank_source=result.bank_source.value,
            column_mapping={
                "date": result.column_mapping.date_column,
                "label": result.column_mapping.label_column,
                "amount": result.column_mapping.amount_column,
                "debit": result.column_mapping.debit_column,
                "credit": result.column_mapping.credit_column,
            },
            raw_columns=result.raw_columns,
            sample_data=result.sample_data[:5],
            transaction_count=len(result.transactions),
            transactions_preview=[t.to_dict() for t in result.transactions[:10]],
            errors=result.errors,
            warnings=result.warnings,
            metadata=result.metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analyze error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur d'analyse: {str(e)}"
        )


@router.post("/confirm", response_model=ImportResultResponse)
async def confirm_import(
    request: ConfirmImportRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 2: Confirm and execute import

    After reviewing the analyze results, call this endpoint to:
    - Execute the actual import
    - Optionally provide custom column mapping
    - Save transactions to database

    Uses "annule et remplace" mode for existing months.
    """
    logger.info(f"Smart import confirm: session {request.session_id}")

    # Get session data
    session_data = _analyze_sessions.get(request.session_id)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session expirée ou invalide. Veuillez réanalyser le fichier."
        )

    # Verify user
    if session_data["user_id"] != current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette session appartient à un autre utilisateur"
        )

    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation requise (confirm=true)"
        )

    try:
        result: ParseResult = session_data["result"]

        # If custom mapping provided, re-parse with it
        if request.custom_mapping:
            parser = get_smart_parser()
            custom_map = {
                "date": request.custom_mapping.date,
                "label": request.custom_mapping.label,
                "amount": request.custom_mapping.amount,
                "debit": request.custom_mapping.debit,
                "credit": request.custom_mapping.credit,
            }
            result = parser.apply_custom_mapping(
                session_data["content"],
                session_data["filename"],
                custom_map
            )

        if not result.success or len(result.transactions) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aucune transaction valide trouvée"
            )

        # Create import metadata
        import_id = str(uuid.uuid4())

        # Get unique months
        months_set = set()
        for tx in result.transactions:
            if tx.date_op:
                months_set.add(tx.date_op.strftime("%Y-%m"))
        months_list = sorted(list(months_set))

        import_meta = ImportMetadata(
            id=import_id,
            filename=session_data["filename"],
            created_at=datetime.now().date(),
            user_id=current_user.username,
            months_detected=json.dumps(months_list),
            duplicates_count=0,
            warnings=json.dumps(result.warnings) if result.warnings else None,
            processing_ms=0
        )
        db.add(import_meta)

        # PRÉSERVATION DES TAGS: Sauvegarder les tags existants avant suppression
        # Clé: (label_normalized, date_op, amount) -> (tags, exclude, category, expense_type)
        existing_tags_map = {}
        for month in months_list:
            existing_transactions = db.query(Transaction).filter(
                Transaction.month == month
            ).all()

            for tx in existing_transactions:
                # Normaliser le label pour une meilleure correspondance
                label_key = tx.label.upper().strip() if tx.label else ""
                date_key = str(tx.date_op) if tx.date_op else ""
                amount_key = round(tx.amount, 2) if tx.amount else 0
                key = (label_key, date_key, amount_key)

                # Ne sauvegarder que si un tag a été défini (pas "Non classé")
                if tx.tags and tx.tags.lower() != "non classé":
                    existing_tags_map[key] = {
                        "tags": tx.tags,
                        "exclude": tx.exclude,
                        "category": tx.category,
                        "expense_type": tx.expense_type
                    }

        logger.info(f"💾 {len(existing_tags_map)} tags sauvegardés pour préservation")

        # ANNULE ET REMPLACE: Delete existing transactions for detected months
        logger.info(f"Mode ANNULE ET REMPLACE pour les mois: {months_list}")
        for month in months_list:
            existing_count = db.query(Transaction).filter(
                Transaction.month == month
            ).count()

            if existing_count > 0:
                logger.info(f"  Suppression de {existing_count} transactions existantes pour {month}")
                db.query(Transaction).filter(
                    Transaction.month == month
                ).delete()

        db.flush()

        # Insert new transactions
        transactions_created = 0
        tags_preserved = 0
        for tx in result.transactions:
            if not tx.date_op:
                continue

            # Chercher un tag existant pour cette transaction
            label_key = tx.label.upper().strip() if tx.label else ""
            date_key = str(tx.date_op)
            amount_key = round(tx.amount, 2) if tx.amount else 0
            key = (label_key, date_key, amount_key)

            # Récupérer les données sauvegardées ou utiliser les défauts
            saved_data = existing_tags_map.get(key, {})
            tags = saved_data.get("tags", "Non classé")
            exclude = saved_data.get("exclude", False)
            category = saved_data.get("category", "VARIABLE")
            expense_type = saved_data.get("expense_type", "VARIABLE")

            if key in existing_tags_map:
                tags_preserved += 1

            transaction = Transaction(
                label=tx.label,
                amount=tx.amount,
                date_op=tx.date_op,
                month=tx.date_op.strftime("%Y-%m"),
                tags=tags,
                category=category,
                category_parent="VARIABLE",
                exclude=exclude,
                expense_type=expense_type,
                is_expense=(tx.amount < 0),  # Définir is_expense basé sur le signe du montant
                import_id=import_id
            )
            db.add(transaction)
            transactions_created += 1

        db.commit()

        # Clean up session
        del _analyze_sessions[request.session_id]

        logger.info(f"Import terminé: {transactions_created} transactions, {tags_preserved} tags préservés, mois: {months_list}")

        message = f"Import réussi: {transactions_created} transactions importées"
        if tags_preserved > 0:
            message += f" ({tags_preserved} tags préservés)"

        return ImportResultResponse(
            success=True,
            import_id=import_id,
            transactions_imported=transactions_created,
            months_detected=months_list,
            message=message,
            errors=result.errors,
            warnings=result.warnings
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Import error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur d'import: {str(e)}"
        )


@router.post("/quick", response_model=ImportResultResponse)
async def quick_import(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Quick import: Analyze + Confirm in one step

    Use this for automated imports without user confirmation.
    The system will auto-detect format and columns.
    """
    logger.info(f"Quick import: {file.filename}")

    try:
        # Read file
        content = await file.read()

        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Fichier vide")

        # Parse
        parser = get_smart_parser()
        result = parser.parse(content, file.filename)

        if not result.success or len(result.transactions) == 0:
            return ImportResultResponse(
                success=False,
                import_id="",
                transactions_imported=0,
                months_detected=[],
                message="Aucune transaction trouvée",
                errors=result.errors,
                warnings=result.warnings
            )

        # Create import
        import_id = str(uuid.uuid4())

        months_set = set()
        for tx in result.transactions:
            if tx.date_op:
                months_set.add(tx.date_op.strftime("%Y-%m"))
        months_list = sorted(list(months_set))

        import_meta = ImportMetadata(
            id=import_id,
            filename=file.filename,
            created_at=datetime.now().date(),
            user_id=current_user.username,
            months_detected=json.dumps(months_list),
            duplicates_count=0,
            warnings=None,
            processing_ms=0
        )
        db.add(import_meta)

        # PRÉSERVATION DES TAGS: Sauvegarder les tags existants avant suppression
        existing_tags_map = {}
        for month in months_list:
            existing_transactions = db.query(Transaction).filter(
                Transaction.month == month
            ).all()

            for tx in existing_transactions:
                label_key = tx.label.upper().strip() if tx.label else ""
                date_key = str(tx.date_op) if tx.date_op else ""
                amount_key = round(tx.amount, 2) if tx.amount else 0
                key = (label_key, date_key, amount_key)

                if tx.tags and tx.tags.lower() != "non classé":
                    existing_tags_map[key] = {
                        "tags": tx.tags,
                        "exclude": tx.exclude,
                        "category": tx.category,
                        "expense_type": tx.expense_type
                    }

        logger.info(f"💾 {len(existing_tags_map)} tags sauvegardés pour préservation")

        # ANNULE ET REMPLACE
        for month in months_list:
            db.query(Transaction).filter(Transaction.month == month).delete()

        db.flush()

        # Insert transactions
        transactions_created = 0
        tags_preserved = 0
        for tx in result.transactions:
            if not tx.date_op:
                continue

            # Chercher un tag existant
            label_key = tx.label.upper().strip() if tx.label else ""
            date_key = str(tx.date_op)
            amount_key = round(tx.amount, 2) if tx.amount else 0
            key = (label_key, date_key, amount_key)

            saved_data = existing_tags_map.get(key, {})
            tags = saved_data.get("tags", "Non classé")
            exclude = saved_data.get("exclude", False)
            category = saved_data.get("category", "VARIABLE")
            expense_type = saved_data.get("expense_type", "VARIABLE")

            if key in existing_tags_map:
                tags_preserved += 1

            transaction = Transaction(
                label=tx.label,
                amount=tx.amount,
                date_op=tx.date_op,
                month=tx.date_op.strftime("%Y-%m"),
                tags=tags,
                category=category,
                category_parent="VARIABLE",
                exclude=exclude,
                expense_type=expense_type,
                is_expense=(tx.amount < 0),  # Définir is_expense basé sur le signe du montant
                import_id=import_id
            )
            db.add(transaction)
            transactions_created += 1

        db.commit()

        message = f"Import rapide réussi: {transactions_created} transactions"
        if tags_preserved > 0:
            message += f" ({tags_preserved} tags préservés)"

        return ImportResultResponse(
            success=True,
            import_id=import_id,
            transactions_imported=transactions_created,
            months_detected=months_list,
            message=message,
            errors=result.errors,
            warnings=result.warnings
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Quick import error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.get("/formats")
async def get_supported_formats():
    """
    Get list of supported file formats and banks
    """
    return {
        "formats": [
            {"id": "csv", "name": "CSV", "extensions": [".csv"]},
            {"id": "xlsx", "name": "Excel", "extensions": [".xlsx", ".xls"]},
            {"id": "pdf", "name": "PDF", "extensions": [".pdf"]}
        ],
        "banks": [
            {"id": "boursobank", "name": "BoursoBank (Boursorama)"},
            {"id": "lcl", "name": "LCL"},
            {"id": "societe_generale", "name": "Société Générale"},
            {"id": "bnp", "name": "BNP Paribas"},
            {"id": "credit_agricole", "name": "Crédit Agricole"},
            {"id": "credit_mutuel", "name": "Crédit Mutuel"},
            {"id": "caisse_epargne", "name": "Caisse d'Épargne"},
            {"id": "fortuneo", "name": "Fortuneo"},
            {"id": "n26", "name": "N26"},
            {"id": "revolut", "name": "Revolut"},
            {"id": "generic", "name": "Autre banque"}
        ]
    }
