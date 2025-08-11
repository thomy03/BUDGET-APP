"""
Core utility functions for Budget Famille v2.3
Essential functions extracted from monolithic app.py
"""
import logging
import re
import hashlib
import datetime as dt
from typing import List, Optional, Dict, Union, Any, Tuple
import pandas as pd
import numpy as np
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from html import escape
import tempfile
import io
import csv

logger = logging.getLogger(__name__)

# Import magic with fallback
MAGIC_AVAILABLE = False
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    try:
        import magic_fallback as magic
        MAGIC_AVAILABLE = True
    except ImportError:
        MAGIC_AVAILABLE = False

def parse_number(x):
    """Parse a number from various string formats"""
    if pd.isna(x) or x is None or x == "":
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    
    x_str = str(x).strip()
    x_str = x_str.replace(',', '.')
    x_str = x_str.replace(' ', '')
    x_str = re.sub(r'[^\d\-\.]', '', x_str)
    
    try:
        return float(x_str)
    except ValueError:
        return 0.0

def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize CSV column names to expected format"""
    if df.empty:
        return df
    
    # Mapping des colonnes courantes
    col_mapping = {
        # Dates
        'date opération': 'date_op',
        'date_operation': 'date_op',
        'date op': 'date_op',
        'dateop': 'date_op',
        'date': 'date_op',
        'date valeur': 'date_valeur',
        'date val': 'date_valeur',
        'dateval': 'date_valeur',
        'datevaleur': 'date_valeur',
        
        # Montants
        'montant': 'amount',
        'amount': 'amount',
        'crédit': 'amount',
        'débit': 'amount',
        
        # Libellés/Descriptions  
        'libellé': 'label',
        'libelle': 'label',
        'label': 'label',
        'description': 'label',
        
        # Catégories
        'catégorie': 'category',
        'categorie': 'category',
        'category': 'category',
        'categoryparent': 'category',
        'category parent': 'category',
        'sous-catégorie': 'subcategory',
        'sous_categorie': 'subcategory',
        'subcategory': 'subcategory',
        
        # Comptes
        'compte': 'account',
        'account': 'account',
        'accountlabel': 'account',
        'account label': 'account',
        'accountnum': 'account',
        'account num': 'account',
        'numéro de compte': 'account',
        'numero de compte': 'account',
        
        # Autres champs
        'commentaire': 'comment',
        'comment': 'comment',
        'solde': 'balance',
        'balance': 'balance',
        'accountbalance': 'balance',
        'account balance': 'balance',
        'fournisseur': 'supplier',
        'supplier': 'supplier',
        'supplierfound': 'supplier',
        'supplier found': 'supplier'
    }
    
    # Normalisation des noms
    df.columns = [col.lower().strip() for col in df.columns]
    
    # Application du mapping
    for old_name, new_name in col_mapping.items():
        if old_name in df.columns:
            df = df.rename(columns={old_name: new_name})
    
    return df

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for security"""
    if not filename:
        return "unknown"
    
    # Remove directory traversal
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove dangerous characters
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Limit length
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:90] + '.' + ext if ext else name[:100]
    
    return filename

def validate_file_security(file: UploadFile) -> bool:
    """Validate uploaded file for security"""
    try:
        # Check filename
        if not file.filename:
            logger.warning("No filename provided")
            return False
        
        # Sanitize filename
        safe_filename = sanitize_filename(file.filename)
        if not safe_filename.lower().endswith('.csv'):
            logger.warning(f"Invalid file extension: {safe_filename}")
            return False
        
        # Check file size (max 10MB)
        if hasattr(file, 'size') and file.size and file.size > 10 * 1024 * 1024:
            logger.warning(f"File too large: {file.size} bytes")
            return False
        
        # MIME type check if available
        if MAGIC_AVAILABLE:
            try:
                # Read first chunk for MIME detection
                file.file.seek(0)
                chunk = file.file.read(1024)
                file.file.seek(0)
                
                mime = magic.from_buffer(chunk, mime=True)
                if not mime.startswith('text/'):
                    logger.warning(f"Invalid MIME type: {mime}")
                    return False
            except Exception as e:
                logger.warning(f"MIME detection failed: {str(e)}")
                # Continue without MIME check
        
        return True
    except Exception as e:
        logger.error(f"File validation error: {str(e)}")
        return False

def robust_read_csv(file: UploadFile) -> pd.DataFrame:
    """Read CSV file with multiple encoding attempts"""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            file.file.seek(0)
            content = file.file.read()
            
            # Try to decode
            text_content = content.decode(encoding)
            
            # Create StringIO for pandas
            csv_buffer = io.StringIO(text_content)
            
            # Try different separators
            for sep in [';', ',', '\t']:
                csv_buffer.seek(0)
                try:
                    df = pd.read_csv(csv_buffer, sep=sep, low_memory=False)
                    if len(df.columns) > 1:  # Valid CSV should have multiple columns
                        logger.info(f"CSV read successfully with encoding {encoding} and separator '{sep}'")
                        return df
                except Exception:
                    continue
            
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.warning(f"Failed to read CSV with encoding {encoding}: {str(e)}")
            continue
    
    raise ValueError("Unable to read CSV file with any supported encoding")

def detect_months_with_metadata(df: pd.DataFrame) -> List[Dict]:
    """Detect months in DataFrame with metadata"""
    if df.empty:
        return []
    
    # Normalize columns
    df = normalize_cols(df)
    
    if 'date_op' not in df.columns:
        return []
    
    try:
        # Convert date column with French format support
        df['date_op'] = pd.to_datetime(df['date_op'], errors='coerce', dayfirst=True)
        df = df.dropna(subset=['date_op'])
        
        if df.empty:
            return []
        
        # Group by month
        df['month'] = df['date_op'].dt.strftime('%Y-%m')
        months_data = []
        
        for month in df['month'].unique():
            if pd.isna(month):
                continue
            
            month_df = df[df['month'] == month]
            
            # Calculate metadata
            date_range = {
                'start': month_df['date_op'].min().strftime('%Y-%m-%d'),
                'end': month_df['date_op'].max().strftime('%Y-%m-%d')
            }
            
            try:
                total_amount = month_df['amount'].sum() if 'amount' in month_df.columns else 0
            except Exception:
                total_amount = 0
            
            try:
                categories = month_df['category'].dropna().unique().tolist() if 'category' in month_df.columns else []
            except Exception:
                categories = []
            
            months_data.append({
                'month': month,
                'transaction_count': len(month_df),
                'date_range': date_range,
                'total_amount': total_amount,
                'categories': categories[:5]  # Limit to first 5 categories
            })
        
        return sorted(months_data, key=lambda x: x['month'], reverse=True)
    
    except Exception as e:
        logger.error(f"Error detecting months: {str(e)}")
        return []

def suggest_optimal_month(months_data: List[Dict]) -> Optional[str]:
    """Suggest the optimal month for import based on completeness"""
    if not months_data:
        return None
    
    # Score months based on transaction count and date range completeness
    scored_months = []
    
    for month_data in months_data:
        score = month_data['transaction_count']
        
        # Bonus for more recent months
        try:
            month_date = dt.datetime.strptime(month_data['month'], '%Y-%m')
            days_old = (dt.datetime.now() - month_date).days
            recency_bonus = max(0, 365 - days_old) / 365  # 0-1 bonus
            score += score * recency_bonus * 0.1
        except:
            pass
        
        scored_months.append((month_data['month'], score))
    
    # Return month with highest score
    scored_months.sort(key=lambda x: x[1], reverse=True)
    return scored_months[0][0]

def check_duplicate_transactions(df: pd.DataFrame, db: Session) -> Dict:
    """Check for duplicate transactions in database"""
    try:
        from models.database import Transaction
        
        duplicates_info = {
            'potential_duplicates': 0,
            'exact_matches': 0,
            'similar_transactions': []
        }
        
        if df.empty:
            return duplicates_info
        
        # Normalize columns
        df = normalize_cols(df)
        
        # Check for existing transactions
        for _, row in df.head(100).iterrows():  # Limit check to first 100 rows
            try:
                date_op = pd.to_datetime(row.get('date_op'), errors='coerce', dayfirst=True)
                amount = parse_number(row.get('amount', 0))
                label = str(row.get('label', ''))[:50]  # Limit label length
                
                if pd.isna(date_op) or amount == 0:
                    continue
                
                # Look for exact matches
                existing = db.query(Transaction).filter(
                    Transaction.date_op == date_op.date(),
                    Transaction.amount == amount,
                    Transaction.label.like(f'%{label[:20]}%')
                ).first()
                
                if existing:
                    duplicates_info['exact_matches'] += 1
                    duplicates_info['similar_transactions'].append({
                        'csv_row': {
                            'date': date_op.strftime('%Y-%m-%d'),
                            'amount': amount,
                            'label': label
                        },
                        'db_match': {
                            'id': existing.id,
                            'date': str(existing.date_op),
                            'amount': existing.amount,
                            'label': existing.label
                        }
                    })
            
            except Exception as e:
                logger.warning(f"Error checking duplicate for row: {str(e)}")
                continue
        
        duplicates_info['potential_duplicates'] = duplicates_info['exact_matches']
        return duplicates_info
    
    except Exception as e:
        logger.error(f"Error checking duplicates: {str(e)}")
        return {'potential_duplicates': 0, 'exact_matches': 0, 'similar_transactions': []}

def validate_csv_data(df: pd.DataFrame) -> List[str]:
    """Validate CSV data structure and content"""
    errors = []
    
    if df.empty:
        errors.append("CSV file is empty")
        return errors
    
    # Normalize columns
    df = normalize_cols(df)
    
    # Check required columns
    required_columns = ['date_op']
    for col in required_columns:
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")
    
    # Check date format
    if 'date_op' in df.columns:
        try:
            date_series = pd.to_datetime(df['date_op'], errors='coerce', dayfirst=True)
            null_dates = date_series.isna().sum()
            if null_dates > len(df) * 0.5:  # More than 50% invalid dates
                errors.append(f"Too many invalid dates: {null_dates}/{len(df)} (formats supportés: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD)")
        except Exception:
            errors.append("Invalid date format in date_op column")
    
    # Check amount column if present
    if 'amount' in df.columns:
        try:
            df['amount_parsed'] = df['amount'].apply(parse_number)
            zero_amounts = (df['amount_parsed'] == 0).sum()
            if zero_amounts > len(df) * 0.8:  # More than 80% zero amounts
                errors.append(f"Too many zero amounts: {zero_amounts}/{len(df)}")
        except Exception:
            errors.append("Invalid amount format in amount column")
    
    # Check minimum row count
    if len(df) < 1:
        errors.append("CSV must contain at least 1 transaction")
    
    # Check maximum row count (prevent memory issues)
    if len(df) > 50000:
        errors.append(f"CSV too large: {len(df)} rows (maximum 50,000)")
    
    return errors

def ensure_default_config(db: Session):
    """Ensure default configuration exists"""
    try:
        from models.database import Config
        
        config = db.query(Config).first()
        if not config:
            config = Config()
            db.add(config)
            db.commit()
            db.refresh(config)
        
        return config
    except Exception as e:
        logger.error(f"Error ensuring default config: {str(e)}")
        raise

def is_income_or_transfer(label: str, cat_parent: str) -> bool:
    """Determine if a transaction is income or transfer"""
    if not label:
        return False
    
    label = label.lower()
    cat_parent = cat_parent.lower() if cat_parent else ""
    
    income_keywords = ['salaire', 'virement', 'remboursement', 'prestation', 'allocation']
    
    for keyword in income_keywords:
        if keyword in label or keyword in cat_parent:
            return True
    
    return False

def get_split(cfg):
    """Calculate split ratios from configuration"""
    if cfg.split_mode == "manuel":
        return cfg.split1 * 100, cfg.split2 * 100
    else:  # revenus
        total_rev = cfg.rev1 + cfg.rev2
        if total_rev == 0:
            return 50.0, 50.0
        return (cfg.rev1 / total_rev) * 100, (cfg.rev2 / total_rev) * 100