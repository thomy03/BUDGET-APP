"""
Centralized validation utilities for Budget Famille v2.3
Eliminates duplicate validation patterns across the application
"""

import re
import datetime as dt
from typing import Any, Dict, List, Optional, Union, Tuple
from decimal import Decimal, InvalidOperation
import csv
import io
import magic

from .error_handlers import ValidationError

# Regex patterns for common validations
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
MONTH_PATTERN = re.compile(r'^\d{4}-\d{2}$')
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
CURRENCY_PATTERN = re.compile(r'^-?\d+(\.\d{1,2})?$')

# Valid file MIME types for uploads
ALLOWED_FILE_TYPES = {
    'text/csv',
    'application/csv',
    'text/plain',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

# Required CSV headers for transaction import
REQUIRED_CSV_HEADERS = [
    'date_op',
    'label', 
    'category',
    'amount'
]

def validate_date_string(date_str: str, field_name: str = "date") -> dt.date:
    """
    Validate and parse date string in YYYY-MM-DD format
    
    Args:
        date_str: Date string to validate
        field_name: Field name for error messages
        
    Returns:
        Parsed date object
        
    Raises:
        ValidationError: If date format is invalid
    """
    if not isinstance(date_str, str):
        raise ValidationError(f"{field_name} must be a string")
    
    if not DATE_PATTERN.match(date_str):
        raise ValidationError(f"{field_name} must be in YYYY-MM-DD format")
    
    try:
        return dt.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError as e:
        raise ValidationError(f"Invalid {field_name}: {str(e)}")

def validate_month_format(month_str: str, field_name: str = "month") -> str:
    """
    Validate month string in YYYY-MM format
    
    Args:
        month_str: Month string to validate
        field_name: Field name for error messages
        
    Returns:
        Validated month string
        
    Raises:
        ValidationError: If month format is invalid
    """
    if not isinstance(month_str, str):
        raise ValidationError(f"{field_name} must be a string")
    
    if not MONTH_PATTERN.match(month_str):
        raise ValidationError(f"{field_name} must be in YYYY-MM format")
    
    try:
        # Validate that it's a real month
        year, month = map(int, month_str.split('-'))
        if not (1 <= month <= 12):
            raise ValueError("Month must be between 01 and 12")
        dt.date(year, month, 1)  # Validate year/month combination
        return month_str
    except ValueError as e:
        raise ValidationError(f"Invalid {field_name}: {str(e)}")

def validate_amount(amount: Union[str, int, float, Decimal], field_name: str = "amount") -> float:
    """
    Validate and convert amount to float
    
    Args:
        amount: Amount to validate
        field_name: Field name for error messages
        
    Returns:
        Validated amount as float
        
    Raises:
        ValidationError: If amount is invalid
    """
    if amount is None:
        raise ValidationError(f"{field_name} is required")
    
    # Handle different input types
    if isinstance(amount, str):
        # Remove common currency symbols and spaces
        cleaned = amount.strip().replace('€', '').replace(',', '.').replace(' ', '')
        
        if not CURRENCY_PATTERN.match(cleaned):
            raise ValidationError(f"{field_name} must be a valid number")
        
        try:
            amount = float(cleaned)
        except ValueError:
            raise ValidationError(f"{field_name} must be a valid number")
    
    elif isinstance(amount, Decimal):
        try:
            amount = float(amount)
        except (ValueError, InvalidOperation):
            raise ValidationError(f"{field_name} must be a valid number")
    
    elif not isinstance(amount, (int, float)):
        raise ValidationError(f"{field_name} must be a number")
    
    # Validate range (reasonable budget amounts)
    if abs(amount) > 1_000_000:
        raise ValidationError(f"{field_name} exceeds maximum allowed value")
    
    return float(amount)

def validate_percentage(percentage: Union[str, int, float], field_name: str = "percentage") -> float:
    """
    Validate percentage value (0-100)
    
    Args:
        percentage: Percentage to validate
        field_name: Field name for error messages
        
    Returns:
        Validated percentage as float
        
    Raises:
        ValidationError: If percentage is invalid
    """
    value = validate_amount(percentage, field_name)
    
    if not (0 <= value <= 100):
        raise ValidationError(f"{field_name} must be between 0 and 100")
    
    return value

def validate_email(email: str, field_name: str = "email") -> str:
    """
    Validate email address format
    
    Args:
        email: Email to validate
        field_name: Field name for error messages
        
    Returns:
        Validated email string
        
    Raises:
        ValidationError: If email format is invalid
    """
    if not isinstance(email, str):
        raise ValidationError(f"{field_name} must be a string")
    
    email = email.strip().lower()
    
    if not email:
        raise ValidationError(f"{field_name} is required")
    
    if not EMAIL_PATTERN.match(email):
        raise ValidationError(f"{field_name} must be a valid email address")
    
    if len(email) > 100:
        raise ValidationError(f"{field_name} must be less than 100 characters")
    
    return email

def validate_string_length(
    value: str,
    min_length: int = 0,
    max_length: int = 255,
    field_name: str = "field"
) -> str:
    """
    Validate string length
    
    Args:
        value: String to validate
        min_length: Minimum length
        max_length: Maximum length
        field_name: Field name for error messages
        
    Returns:
        Validated string
        
    Raises:
        ValidationError: If length is invalid
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    
    value = value.strip()
    length = len(value)
    
    if length < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters long")
    
    if length > max_length:
        raise ValidationError(f"{field_name} must be at most {max_length} characters long")
    
    return value

def validate_choice(
    value: str,
    choices: List[str],
    field_name: str = "field"
) -> str:
    """
    Validate value is in allowed choices
    
    Args:
        value: Value to validate
        choices: List of allowed choices
        field_name: Field name for error messages
        
    Returns:
        Validated choice
        
    Raises:
        ValidationError: If choice is invalid
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    
    if value not in choices:
        choices_str = ", ".join(choices)
        raise ValidationError(f"{field_name} must be one of: {choices_str}")
    
    return value

def validate_file_type(file_content: bytes, filename: str = "") -> str:
    """
    Validate file type using magic bytes
    
    Args:
        file_content: File content as bytes
        filename: Optional filename for context
        
    Returns:
        Detected MIME type
        
    Raises:
        ValidationError: If file type is not allowed
    """
    if not file_content:
        raise ValidationError("File is empty")
    
    try:
        # Try to detect MIME type
        mime_type = magic.from_buffer(file_content, mime=True)
    except Exception:
        # Fallback based on file extension
        if filename.lower().endswith('.csv'):
            mime_type = 'text/csv'
        elif filename.lower().endswith('.xlsx'):
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif filename.lower().endswith('.xls'):
            mime_type = 'application/vnd.ms-excel'
        else:
            raise ValidationError("Unable to determine file type")
    
    if mime_type not in ALLOWED_FILE_TYPES:
        raise ValidationError(f"File type '{mime_type}' is not allowed")
    
    return mime_type

def validate_csv_headers(csv_content: str, required_headers: List[str] = None) -> List[str]:
    """
    Validate CSV file headers
    
    Args:
        csv_content: CSV content as string
        required_headers: Required header names (defaults to REQUIRED_CSV_HEADERS)
        
    Returns:
        List of detected headers
        
    Raises:
        ValidationError: If required headers are missing
    """
    if required_headers is None:
        required_headers = REQUIRED_CSV_HEADERS
    
    try:
        # Parse CSV headers
        reader = csv.reader(io.StringIO(csv_content))
        headers = next(reader)
        headers = [h.strip().lower() for h in headers]
    except Exception as e:
        raise ValidationError(f"Unable to parse CSV headers: {str(e)}")
    
    # Check for required headers
    missing_headers = []
    for required_header in required_headers:
        if required_header.lower() not in headers:
            missing_headers.append(required_header)
    
    if missing_headers:
        missing_str = ", ".join(missing_headers)
        raise ValidationError(f"Missing required CSV headers: {missing_str}")
    
    return headers

def validate_json_payload(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """
    Validate JSON payload has required fields
    
    Args:
        data: JSON payload dictionary
        required_fields: List of required field names
        
    Returns:
        Validated data dictionary
        
    Raises:
        ValidationError: If required fields are missing
    """
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")
    
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        missing_str = ", ".join(missing_fields)
        raise ValidationError(f"Missing required fields: {missing_str}")
    
    return data

def validate_pagination_params(
    page: Optional[int] = None,
    limit: Optional[int] = None,
    max_limit: int = 1000
) -> Tuple[int, int]:
    """
    Validate pagination parameters
    
    Args:
        page: Page number (1-based)
        limit: Number of items per page
        max_limit: Maximum allowed limit
        
    Returns:
        Tuple of (page, limit)
        
    Raises:
        ValidationError: If parameters are invalid
    """
    # Default values
    if page is None:
        page = 1
    if limit is None:
        limit = 50
    
    # Validate page
    if not isinstance(page, int) or page < 1:
        raise ValidationError("Page must be a positive integer")
    
    # Validate limit
    if not isinstance(limit, int) or limit < 1:
        raise ValidationError("Limit must be a positive integer")
    
    if limit > max_limit:
        raise ValidationError(f"Limit cannot exceed {max_limit}")
    
    return page, limit

def validate_date_range(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Tuple[Optional[dt.date], Optional[dt.date]]:
    """
    Validate date range parameters
    
    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        
    Returns:
        Tuple of (start_date, end_date) as date objects
        
    Raises:
        ValidationError: If date range is invalid
    """
    start = None
    end = None
    
    if start_date:
        start = validate_date_string(start_date, "start_date")
    
    if end_date:
        end = validate_date_string(end_date, "end_date")
    
    # Validate range
    if start and end and start > end:
        raise ValidationError("Start date must be before end date")
    
    # Validate reasonable range (not more than 10 years)
    if start and end:
        days_diff = (end - start).days
        if days_diff > 3650:  # ~10 years
            raise ValidationError("Date range cannot exceed 10 years")
    
    return start, end

def validate_split_configuration(
    split_mode: str,
    split1: Optional[float] = None,
    split2: Optional[float] = None
) -> Tuple[str, float, float]:
    """
    Validate split configuration for budget calculations
    
    Args:
        split_mode: Split mode ("revenus", "manuel", "50/50", etc.)
        split1: Split percentage for member 1
        split2: Split percentage for member 2
        
    Returns:
        Tuple of (split_mode, split1, split2)
        
    Raises:
        ValidationError: If split configuration is invalid
    """
    valid_modes = ["revenus", "manuel", "50/50", "clé", "100/0", "0/100"]
    split_mode = validate_choice(split_mode, valid_modes, "split_mode")
    
    # For manual split mode, validate percentages
    if split_mode == "manuel":
        if split1 is None or split2 is None:
            raise ValidationError("Manual split mode requires split1 and split2 values")
        
        split1 = validate_percentage(split1, "split1")
        split2 = validate_percentage(split2, "split2")
        
        # Validate they add up to 100%
        total = split1 + split2
        if abs(total - 100) > 0.01:  # Allow small floating point errors
            raise ValidationError("Split percentages must add up to 100%")
    
    # Set default values for non-manual modes
    elif split_mode == "50/50":
        split1, split2 = 50.0, 50.0
    elif split_mode == "100/0":
        split1, split2 = 100.0, 0.0
    elif split_mode == "0/100":
        split1, split2 = 0.0, 100.0
    else:
        # For "revenus" and "clé" modes, splits are calculated dynamically
        split1 = split1 or 50.0
        split2 = split2 or 50.0
    
    return split_mode, split1, split2

def validate_transaction_data(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate transaction data
    
    Args:
        transaction: Transaction data dictionary
        
    Returns:
        Validated transaction data
        
    Raises:
        ValidationError: If transaction data is invalid
    """
    validated = {}
    
    # Required fields
    required_fields = ["date_op", "label", "amount"]
    validate_json_payload(transaction, required_fields)
    
    # Validate date
    validated["date_op"] = validate_date_string(transaction["date_op"], "date_op")
    
    # Derive month from date
    validated["month"] = validated["date_op"].strftime("%Y-%m")
    
    # Validate label
    validated["label"] = validate_string_length(
        transaction["label"], 
        min_length=1, 
        max_length=500,
        field_name="label"
    )
    
    # Validate amount
    validated["amount"] = validate_amount(transaction["amount"], "amount")
    
    # Optional fields with defaults
    validated["category"] = validate_string_length(
        transaction.get("category", ""), 
        max_length=100,
        field_name="category"
    )
    
    validated["category_parent"] = validate_string_length(
        transaction.get("category_parent", ""), 
        max_length=100,
        field_name="category_parent"
    )
    
    validated["account_label"] = validate_string_length(
        transaction.get("account_label", ""), 
        max_length=100,
        field_name="account_label"
    )
    
    # Boolean fields
    validated["is_expense"] = bool(transaction.get("is_expense", False))
    validated["exclude"] = bool(transaction.get("exclude", False))
    
    # Tags - convert to string if list
    tags = transaction.get("tags", "")
    if isinstance(tags, list):
        tags = ",".join(str(tag) for tag in tags)
    validated["tags"] = validate_string_length(str(tags), max_length=500, field_name="tags")
    
    return validated