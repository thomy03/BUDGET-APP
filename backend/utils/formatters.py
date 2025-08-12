"""
Centralized formatting utilities for Budget Famille v2.3
Eliminates duplicate formatting patterns across the application
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
import locale
import json

logger = logging.getLogger(__name__)

# Try to set French locale for currency formatting
try:
    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'fr_FR')
    except locale.Error:
        logger.warning("French locale not available, using default")

def format_currency(
    amount: Union[float, int, str],
    currency_symbol: str = "€",
    decimal_places: int = 2,
    thousands_separator: str = " ",
    decimal_separator: str = ","
) -> str:
    """
    Format amount as currency with French formatting
    
    Args:
        amount: Amount to format
        currency_symbol: Currency symbol to use
        decimal_places: Number of decimal places
        thousands_separator: Thousands separator character
        decimal_separator: Decimal separator character
        
    Returns:
        Formatted currency string
    """
    try:
        # Convert to float
        if isinstance(amount, str):
            amount = float(amount.replace(',', '.').replace(' ', ''))
        amount = float(amount)
        
        # Format with specified decimal places
        formatted = f"{amount:.{decimal_places}f}"
        
        # Split into integer and decimal parts
        if '.' in formatted:
            integer_part, decimal_part = formatted.split('.')
        else:
            integer_part, decimal_part = formatted, "00"
        
        # Add thousands separators
        if len(integer_part) > 3:
            # Add separator every 3 digits from right
            reversed_int = integer_part[::-1]
            chunks = [reversed_int[i:i+3] for i in range(0, len(reversed_int), 3)]
            integer_part = thousands_separator.join(chunks)[::-1]
        
        # Combine parts
        if decimal_places > 0:
            result = f"{integer_part}{decimal_separator}{decimal_part} {currency_symbol}"
        else:
            result = f"{integer_part} {currency_symbol}"
        
        return result
        
    except (ValueError, TypeError) as e:
        logger.error(f"Currency formatting error: {e}")
        return f"0{decimal_separator}00 {currency_symbol}"

def format_percentage(
    value: Union[float, int],
    decimal_places: int = 1,
    include_symbol: bool = True
) -> str:
    """
    Format value as percentage
    
    Args:
        value: Percentage value (0-100)
        decimal_places: Number of decimal places
        include_symbol: Whether to include % symbol
        
    Returns:
        Formatted percentage string
    """
    try:
        formatted = f"{float(value):.{decimal_places}f}"
        return f"{formatted} %" if include_symbol else formatted
    except (ValueError, TypeError) as e:
        logger.error(f"Percentage formatting error: {e}")
        return "0,0 %" if include_symbol else "0,0"

def format_date(
    date_value: Union[datetime, date, str],
    format_type: str = "short"
) -> str:
    """
    Format date with various formats
    
    Args:
        date_value: Date to format
        format_type: Format type (short, long, iso, display)
        
    Returns:
        Formatted date string
    """
    try:
        # Convert string to date if needed
        if isinstance(date_value, str):
            if len(date_value) == 10:  # YYYY-MM-DD
                date_value = datetime.strptime(date_value, '%Y-%m-%d').date()
            else:  # ISO datetime
                date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        
        # Convert datetime to date if needed
        if isinstance(date_value, datetime):
            date_obj = date_value.date() if format_type != "iso" else date_value
        else:
            date_obj = date_value
        
        # Format based on type
        if format_type == "short":
            return date_obj.strftime("%d/%m/%Y")
        elif format_type == "long":
            # French month names
            months_fr = [
                "janvier", "février", "mars", "avril", "mai", "juin",
                "juillet", "août", "septembre", "octobre", "novembre", "décembre"
            ]
            month_name = months_fr[date_obj.month - 1]
            return f"{date_obj.day} {month_name} {date_obj.year}"
        elif format_type == "iso":
            if isinstance(date_obj, datetime):
                return date_obj.isoformat()
            else:
                return date_obj.isoformat()
        elif format_type == "display":
            return date_obj.strftime("%d/%m/%Y")
        else:
            return date_obj.strftime("%d/%m/%Y")
            
    except (ValueError, AttributeError) as e:
        logger.error(f"Date formatting error: {e}")
        return "Invalid date"

def format_month_display(month_str: str) -> str:
    """
    Format month string (YYYY-MM) for display
    
    Args:
        month_str: Month string in YYYY-MM format
        
    Returns:
        Formatted month display string
    """
    try:
        year, month = month_str.split('-')
        month_int = int(month)
        
        months_fr = [
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
        ]
        
        month_name = months_fr[month_int - 1]
        return f"{month_name} {year}"
        
    except (ValueError, IndexError) as e:
        logger.error(f"Month formatting error: {e}")
        return month_str

def format_api_response(
    data: Any = None,
    message: Optional[str] = None,
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format standardized API response
    
    Args:
        data: Response data
        message: Optional message
        success: Success status
        metadata: Optional metadata
        
    Returns:
        Formatted API response dictionary
    """
    response = {
        "success": success,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    if data is not None:
        response["data"] = data
    
    if message:
        response["message"] = message
    
    if metadata:
        response["meta"] = metadata
    
    return response

def format_error_response(
    message: str,
    code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status_code: Optional[int] = None
) -> Dict[str, Any]:
    """
    Format standardized error response
    
    Args:
        message: Error message
        code: Optional error code
        details: Optional error details
        status_code: Optional HTTP status code
        
    Returns:
        Formatted error response dictionary
    """
    response = {
        "success": False,
        "error": {
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }
    
    if code:
        response["error"]["code"] = code
    
    if details:
        response["error"]["details"] = details
    
    if status_code:
        response["error"]["status_code"] = status_code
    
    return response

def format_transaction_data(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format transaction data for API response
    
    Args:
        transaction: Raw transaction data
        
    Returns:
        Formatted transaction data
    """
    formatted = transaction.copy()
    
    # Format amount
    if "amount" in formatted:
        formatted["amount_formatted"] = format_currency(formatted["amount"])
    
    # Format date
    if "date_op" in formatted:
        formatted["date_formatted"] = format_date(formatted["date_op"], "display")
    
    # Format tags as list
    if "tags" in formatted and isinstance(formatted["tags"], str):
        formatted["tags"] = [tag.strip() for tag in formatted["tags"].split(",") if tag.strip()]
    
    # Add display fields
    formatted["is_income"] = not formatted.get("is_expense", False)
    formatted["amount_display"] = format_currency(abs(formatted.get("amount", 0)))
    
    return formatted

def format_budget_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format budget summary for API response
    
    Args:
        summary: Raw budget summary data
        
    Returns:
        Formatted budget summary
    """
    formatted = summary.copy()
    
    # Format currency amounts
    currency_fields = [
        "total_income", "total_expenses", "variable_total", "fixed_total",
        "provisions_total", "member1_share", "member2_share",
        "member1_balance", "member2_balance", "remaining_budget"
    ]
    
    for field in currency_fields:
        if field in formatted:
            formatted[f"{field}_formatted"] = format_currency(formatted[field])
    
    # Format month display
    if "month" in formatted:
        formatted["month_display"] = format_month_display(formatted["month"])
    
    return formatted

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted file size string
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"

def format_duration(seconds: float) -> str:
    """
    Format duration in human readable format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    elif seconds < 60:
        return f"{seconds:.1f} s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} min"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} h"

def format_validation_errors(errors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Format validation errors for API response
    
    Args:
        errors: List of validation errors
        
    Returns:
        Formatted validation error response
    """
    formatted_errors = []
    
    for error in errors:
        formatted_error = {
            "field": error.get("field", "unknown"),
            "message": error.get("message", "Validation error"),
            "code": error.get("code", "VALIDATION_ERROR")
        }
        
        if "value" in error:
            formatted_error["rejected_value"] = error["value"]
        
        formatted_errors.append(formatted_error)
    
    return {
        "success": False,
        "error": {
            "message": "Validation failed",
            "code": "VALIDATION_FAILED",
            "validation_errors": formatted_errors,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }

def format_pagination_meta(
    page: int,
    limit: int,
    total_items: int,
    total_pages: int
) -> Dict[str, Any]:
    """
    Format pagination metadata
    
    Args:
        page: Current page number
        limit: Items per page
        total_items: Total number of items
        total_pages: Total number of pages
        
    Returns:
        Pagination metadata dictionary
    """
    return {
        "pagination": {
            "current_page": page,
            "per_page": limit,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "previous_page": page - 1 if page > 1 else None
        }
    }

def sanitize_for_json(data: Any) -> Any:
    """
    Sanitize data for JSON serialization
    
    Args:
        data: Data to sanitize
        
    Returns:
        JSON-serializable data
    """
    if isinstance(data, (datetime, date)):
        return data.isoformat()
    elif isinstance(data, dict):
        return {k: sanitize_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_json(item) for item in data]
    elif hasattr(data, '__dict__'):
        # For dataclass or similar objects
        return sanitize_for_json(data.__dict__)
    else:
        return data

def format_csv_export_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format data for CSV export
    
    Args:
        data: List of data dictionaries
        
    Returns:
        Formatted data suitable for CSV export
    """
    if not data:
        return []
    
    formatted_data = []
    
    for row in data:
        formatted_row = {}
        
        for key, value in row.items():
            # Skip complex nested objects
            if isinstance(value, (dict, list)):
                continue
            
            # Format dates
            if isinstance(value, (datetime, date)):
                formatted_row[key] = format_date(value, "iso")
            # Format currency amounts
            elif key.endswith(('_amount', '_total', '_balance')) and isinstance(value, (int, float)):
                formatted_row[key] = value  # Keep numeric for CSV
                formatted_row[f"{key}_formatted"] = format_currency(value)
            # Format boolean values
            elif isinstance(value, bool):
                formatted_row[key] = "Oui" if value else "Non"
            else:
                formatted_row[key] = str(value) if value is not None else ""
        
        formatted_data.append(formatted_row)
    
    return formatted_data

def format_search_results(
    results: List[Dict[str, Any]],
    query: str,
    total_results: int,
    search_time_ms: float
) -> Dict[str, Any]:
    """
    Format search results for API response
    
    Args:
        results: List of search results
        query: Search query
        total_results: Total number of results
        search_time_ms: Search execution time in milliseconds
        
    Returns:
        Formatted search response
    """
    return {
        "success": True,
        "data": {
            "results": results,
            "query": query,
            "total_results": total_results,
            "returned_results": len(results),
            "search_time": f"{search_time_ms:.2f} ms"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }