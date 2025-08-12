"""
Import Service for Budget Famille v2.3
Business logic for CSV import operations
"""
import logging
import uuid
import datetime as dt
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import UploadFile
import pandas as pd

logger = logging.getLogger(__name__)

class ImportService:
    """Service for handling CSV import operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def process_csv_import(
        self, 
        file: UploadFile, 
        user_id: str,
        validate_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        Process a CSV file import
        
        Args:
            file: Uploaded CSV file
            user_id: User performing the import
            validate_duplicates: Whether to check for duplicates
            
        Returns:
            Import result summary
        """
        try:
            from app import (
                validate_file_security, robust_read_csv, detect_months_with_metadata,
                check_duplicate_transactions, validate_csv_data, ImportMetadata,
                Transaction
            )
            
            logger.info(f"Starting CSV import for user {user_id}: {file.filename}")
            
            # Security validation
            if not validate_file_security(file):
                raise ValueError("File not authorized or dangerous")
            
            # Read CSV with robust parsing
            df = robust_read_csv(file)
            logger.info(f"CSV parsed successfully: {len(df)} rows")
            
            if df.empty:
                raise ValueError("CSV file is empty")
            
            # Detect months in the data
            months_data = detect_months_with_metadata(df)
            if not months_data:
                raise ValueError("No valid months detected in the file")
            
            # Check for duplicates if requested
            duplicate_info = {}
            if validate_duplicates:
                duplicate_info = check_duplicate_transactions(df, self.db)
                logger.info(f"Duplicate check completed: {duplicate_info}")
            
            # Validate CSV data structure
            validation_errors = validate_csv_data(df)
            if validation_errors:
                raise ValueError(f"Validation errors: {'; '.join(validation_errors)}")
            
            # Process transactions import
            import_result = self._import_transactions(df, months_data, user_id)
            
            # Create import metadata
            import_id = str(uuid.uuid4())
            import_meta = ImportMetadata(
                import_id=import_id,
                filename=file.filename,
                file_size=len(df),
                import_date=dt.datetime.now(),
                user_id=user_id,
                status="completed",
                months_detected=len(months_data),
                rows_imported=import_result["rows_imported"]
            )
            
            self.db.add(import_meta)
            self.db.commit()
            
            logger.info(f"Import completed successfully: {import_id}")
            
            return {
                "import_id": import_id,
                "status": "success",
                "filename": file.filename,
                "rows_processed": len(df),
                "rows_imported": import_result["rows_imported"],
                "months_detected": months_data,
                "duplicates_info": duplicate_info,
                "validation_errors": [],
                "message": "Import completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Import failed for user {user_id}: {str(e)}")
            # Create failed import metadata
            try:
                import_id = str(uuid.uuid4())
                import_meta = ImportMetadata(
                    import_id=import_id,
                    filename=file.filename,
                    file_size=0,
                    import_date=dt.datetime.now(),
                    user_id=user_id,
                    status="failed",
                    months_detected=0,
                    rows_imported=0
                )
                self.db.add(import_meta)
                self.db.commit()
            except:
                pass  # Don't fail on metadata creation failure
            
            raise ValueError(f"Import failed: {str(e)}")
    
    def _import_transactions(
        self, 
        df: pd.DataFrame, 
        months_data: List[Dict], 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Import transactions from DataFrame
        
        Args:
            df: Parsed DataFrame
            months_data: Detected months metadata
            user_id: User ID
            
        Returns:
            Import statistics
        """
        try:
            from app import Transaction, normalize_cols
            
            # Normalize column names
            df = normalize_cols(df)
            
            imported_count = 0
            skipped_count = 0
            
            for _, row in df.iterrows():
                try:
                    # Extract transaction data
                    transaction_data = self._extract_transaction_data(row)
                    
                    # Check if transaction already exists (simple duplicate check)
                    existing = self.db.query(Transaction).filter(
                        Transaction.date_op == transaction_data.get("date_op"),
                        Transaction.amount == transaction_data.get("amount"),
                        Transaction.label == transaction_data.get("label")
                    ).first()
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Create new transaction
                    transaction = Transaction(**transaction_data)
                    self.db.add(transaction)
                    imported_count += 1
                    
                except Exception as e:
                    logger.warning(f"Skipping row due to error: {str(e)}")
                    skipped_count += 1
                    continue
            
            self.db.commit()
            
            return {
                "rows_imported": imported_count,
                "rows_skipped": skipped_count
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error importing transactions: {str(e)}")
            raise
    
    def _extract_transaction_data(self, row: pd.Series) -> Dict[str, Any]:
        """
        Extract transaction data from a DataFrame row
        
        Args:
            row: DataFrame row
            
        Returns:
            Transaction data dictionary
        """
        from app import parse_number, is_income_or_transfer
        
        # Extract basic fields
        date_op = pd.to_datetime(row.get('date_op'), errors='coerce')
        date_valeur = pd.to_datetime(row.get('date_valeur'), errors='coerce')
        amount = parse_number(row.get('amount', 0))
        label = str(row.get('label', '')).strip()
        category = str(row.get('category', 'Autre')).strip()
        subcategory = str(row.get('subcategory', '')).strip()
        
        # Determine if it's an expense
        is_expense = not is_income_or_transfer(label, category)
        
        # Extract month
        month = date_op.strftime('%Y-%m') if pd.notna(date_op) else None
        
        return {
            "month": month,
            "date_op": date_op.date() if pd.notna(date_op) else None,
            "date_valeur": date_valeur.date() if pd.notna(date_valeur) else None,
            "amount": amount,
            "label": label,
            "category": category,
            "subcategory": subcategory,
            "is_expense": is_expense,
            "exclude": False,
            "tags": ""
        }
    
    def get_import_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get import history for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of import records
        """
        try:
            from app import ImportMetadata
            
            imports = self.db.query(ImportMetadata).filter(
                ImportMetadata.user_id == user_id
            ).order_by(ImportMetadata.import_date.desc()).all()
            
            return [
                {
                    "import_id": imp.import_id,
                    "filename": imp.filename,
                    "file_size": imp.file_size,
                    "import_date": imp.import_date.isoformat(),
                    "status": imp.status,
                    "months_detected": imp.months_detected,
                    "rows_imported": imp.rows_imported
                }
                for imp in imports
            ]
        except Exception as e:
            logger.error(f"Error fetching import history for user {user_id}: {str(e)}")
            raise
    
    def get_import_details(self, import_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a specific import
        
        Args:
            import_id: Import ID
            
        Returns:
            Import details or None if not found
        """
        try:
            from app import ImportMetadata
            
            import_meta = self.db.query(ImportMetadata).filter(
                ImportMetadata.import_id == import_id
            ).first()
            
            if not import_meta:
                return None
            
            return {
                "import_id": import_meta.import_id,
                "filename": import_meta.filename,
                "file_size": import_meta.file_size,
                "import_date": import_meta.import_date.isoformat(),
                "status": import_meta.status,
                "months_detected": import_meta.months_detected,
                "rows_imported": import_meta.rows_imported,
                "user_id": import_meta.user_id
            }
        except Exception as e:
            logger.error(f"Error fetching import details for {import_id}: {str(e)}")
            raise