"""
Optimized API Response Schemas for High-Performance Dashboard
Designed for minimal payload size and efficient serialization
"""

from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

# Enums for type safety and performance

class ExpenseType(str, Enum):
    FIXED = "FIXED"
    VARIABLE = "VARIABLE"
    PROVISION = "PROVISION"

class DrillDownLevel(str, Enum):
    SUMMARY = "summary"
    DETAILS = "details"
    TRANSACTIONS = "transactions"

class SplitMode(str, Enum):
    KEY = "key"
    FIFTY_FIFTY = "50/50"
    CUSTOM = "custom"
    MEMBER1_ONLY = "100/0"
    MEMBER2_ONLY = "0/100"

class CacheStatus(str, Enum):
    HIT = "hit"
    MISS = "miss"
    PARTIAL = "partial"

# Core Optimized Schemas

class BaseResponseMetadata(BaseModel):
    """Common metadata for all optimized responses"""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    calculation_time_ms: float = Field(description="Server-side calculation time")
    cache_status: CacheStatus = Field(description="Cache hit/miss status")
    api_version: str = Field(default="2.0", description="API version for compatibility")

class PaginationMetadata(BaseModel):
    """Efficient pagination metadata"""
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)
    total: Optional[int] = Field(None, description="Total items (if known)")
    has_more: bool = Field(description="Whether more items are available")
    next_offset: Optional[int] = Field(None, description="Next pagination offset")

class DrillDownUrls(BaseModel):
    """Pre-computed drill-down URLs for efficient navigation"""
    provisions: Optional[str] = None
    fixed_expenses: Optional[str] = None
    variable_expenses: Optional[str] = None
    categories: Dict[str, str] = Field(default_factory=dict)
    transactions: Optional[str] = None

# Lightweight Entity Schemas

class SlimProvision(BaseModel):
    """Minimal provision data for dashboard overview"""
    id: int
    name: str = Field(max_length=100)
    icon: str = Field(max_length=10)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    monthly_amount: float = Field(description="Monthly provision amount")
    member1_amount: float = Field(description="Member 1 share")
    member2_amount: float = Field(description="Member 2 share")
    progress: float = Field(ge=0, le=100, description="Progress percentage")
    category: str = Field(max_length=50)
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "name": "Vacation Fund",
                "icon": "🏖️",
                "color": "#3B82F6",
                "monthly_amount": 300.0,
                "member1_amount": 180.0,
                "member2_amount": 120.0,
                "progress": 65.5,
                "category": "savings"
            }
        }

class SlimFixedExpense(BaseModel):
    """Minimal fixed expense data for dashboard"""
    id: int
    label: str = Field(max_length=200)
    category: str = Field(max_length=50)
    monthly_amount: float = Field(description="Monthly equivalent amount")
    member1_amount: float
    member2_amount: float
    frequency: str = Field(description="Original frequency")
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "label": "Internet Subscription",
                "category": "services",
                "monthly_amount": 39.99,
                "member1_amount": 20.0,
                "member2_amount": 19.99,
                "frequency": "mensuelle"
            }
        }

class CategorySummary(BaseModel):
    """Category aggregation data for drill-down"""
    name: str = Field(max_length=100)
    total_amount: float
    transaction_count: int = Field(ge=0)
    avg_amount: float
    expense_type: Optional[ExpenseType] = None
    percentage_of_total: Optional[float] = Field(None, ge=0, le=100)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Alimentation",
                "total_amount": 450.75,
                "transaction_count": 23,
                "avg_amount": 19.60,
                "expense_type": "VARIABLE",
                "percentage_of_total": 15.2
            }
        }

class TransactionSummary(BaseModel):
    """Slim transaction data for lists"""
    id: int
    date: Optional[str] = Field(None, description="Transaction date (YYYY-MM-DD)")
    label: str = Field(max_length=500)
    amount: float
    category: str = Field(max_length=100)
    expense_type: ExpenseType
    tags: List[str] = Field(default_factory=list, max_items=10)
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1234,
                "date": "2025-08-13",
                "label": "CHEZ PAUL RESTAURANT",
                "amount": 35.50,
                "category": "Alimentation",
                "expense_type": "VARIABLE",
                "tags": ["restaurant", "sortie"]
            }
        }

# Core Dashboard Response Schemas

class OptimizedDashboardTotals(BaseModel):
    """Optimized totals structure for dashboard"""
    # Expense totals
    total_expenses: float = Field(description="Sum of all expenses (provisions + fixed + variable)")
    total_provisions: float = Field(description="Total monthly provisions")
    total_fixed: float = Field(description="Total monthly fixed expenses")
    total_variable: float = Field(description="Total variable expenses")
    
    # Member splits
    member1_total: float = Field(description="Member 1 total share")
    member2_total: float = Field(description="Member 2 total share")
    
    # Revenue context
    net_revenues: Optional[Dict[str, float]] = Field(None, description="Net revenues after tax")
    split_ratios: Optional[Dict[str, float]] = Field(None, description="Current split ratios")
    
    class Config:
        schema_extra = {
            "example": {
                "total_expenses": 2850.75,
                "total_provisions": 800.0,
                "total_fixed": 1250.75,
                "total_variable": 800.0,
                "member1_total": 1710.45,
                "member2_total": 1140.30,
                "net_revenues": {"member1": 2800.0, "member2": 2200.0, "total": 5000.0},
                "split_ratios": {"member1": 0.6, "member2": 0.4}
            }
        }

class OptimizedDashboardSummary(BaseModel):
    """Ultra-fast dashboard summary response"""
    # Basic info
    month: str = Field(pattern=r"^\d{4}-\d{2}$", description="Month in YYYY-MM format")
    member1: str = Field(max_length=50)
    member2: str = Field(max_length=50)
    
    # Financial totals
    totals: OptimizedDashboardTotals
    
    # Counts for UI badges
    counts: Dict[str, int] = Field(description="Entity counts for UI")
    
    # Navigation
    drill_down_urls: DrillDownUrls = Field(description="Pre-computed navigation URLs")
    
    # Metadata
    metadata: BaseResponseMetadata
    
    class Config:
        schema_extra = {
            "example": {
                "month": "2025-08",
                "member1": "Diana",
                "member2": "Thomas",
                "totals": {
                    "total_expenses": 2850.75,
                    "total_provisions": 800.0,
                    "total_fixed": 1250.75,
                    "total_variable": 800.0,
                    "member1_total": 1710.45,
                    "member2_total": 1140.30
                },
                "counts": {
                    "active_provisions": 5,
                    "active_fixed": 8,
                    "transactions": 156
                },
                "drill_down_urls": {
                    "provisions": "/api/provisions/details?month=2025-08",
                    "categories": {}
                },
                "metadata": {
                    "timestamp": "2025-08-13T10:30:00Z",
                    "calculation_time_ms": 145.5,
                    "cache_status": "hit",
                    "api_version": "2.0"
                }
            }
        }

class CategoryDrillDownResponse(BaseModel):
    """Efficient category drill-down response"""
    # Context
    category: str = Field(max_length=100)
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    level: DrillDownLevel
    
    # Aggregated data
    summary: CategorySummary
    
    # Detailed items (context-dependent)
    items: List[Union[CategorySummary, TransactionSummary]] = Field(
        default_factory=list,
        description="Items depend on drill-down level"
    )
    
    # Pagination
    pagination: PaginationMetadata
    
    # Navigation options
    available_levels: List[DrillDownLevel] = Field(description="Available drill-down levels")
    parent_category: Optional[str] = Field(None, description="Parent category if drilling down")
    
    # Metadata
    metadata: BaseResponseMetadata
    
    class Config:
        schema_extra = {
            "example": {
                "category": "Alimentation",
                "month": "2025-08",
                "level": "details",
                "summary": {
                    "name": "Alimentation",
                    "total_amount": 450.75,
                    "transaction_count": 23,
                    "avg_amount": 19.60,
                    "expense_type": "VARIABLE"
                },
                "items": [],
                "pagination": {
                    "limit": 50,
                    "offset": 0,
                    "total": 23,
                    "has_more": false
                },
                "available_levels": ["summary", "details", "transactions"],
                "metadata": {
                    "calculation_time_ms": 89.2,
                    "cache_status": "miss"
                }
            }
        }

class ProvisionCalculationResponse(BaseModel):
    """Fast provision calculation response"""
    # Context
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    
    # Provision data
    provisions: List[SlimProvision] = Field(description="Calculated provisions")
    
    # Totals
    totals: Dict[str, float] = Field(description="Provision totals")
    
    # Base calculation context
    base_calculations: Dict[str, Any] = Field(description="Underlying financial calculations")
    
    # Metadata
    metadata: BaseResponseMetadata
    
    class Config:
        schema_extra = {
            "example": {
                "month": "2025-08",
                "provisions": [],
                "totals": {
                    "total_monthly_amount": 800.0,
                    "total_member1": 480.0,
                    "total_member2": 320.0
                },
                "base_calculations": {
                    "net_revenues": {"member1": 2800.0, "member2": 2200.0},
                    "split_ratios": {"member1": 0.6, "member2": 0.4}
                },
                "metadata": {
                    "calculation_time_ms": 67.3,
                    "cache_status": "hit"
                }
            }
        }

class FixedExpenseResponse(BaseModel):
    """Fast fixed expense calculation response"""
    # Fixed expenses
    fixed_expenses: List[SlimFixedExpense] = Field(description="Active fixed expenses")
    
    # Totals
    totals: Dict[str, float] = Field(description="Fixed expense totals")
    
    # Metadata
    metadata: BaseResponseMetadata
    
    class Config:
        schema_extra = {
            "example": {
                "fixed_expenses": [],
                "totals": {
                    "total_monthly_amount": 1250.75,
                    "total_member1": 750.45,
                    "total_member2": 500.30
                },
                "metadata": {
                    "calculation_time_ms": 45.1,
                    "cache_status": "hit"
                }
            }
        }

# Analytics and Performance Schemas

class PerformanceMetrics(BaseModel):
    """API performance metrics"""
    endpoint: str
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    total_requests: int
    cache_hit_rate: float = Field(ge=0, le=1, description="Cache hit rate (0-1)")
    error_rate: float = Field(ge=0, le=1, description="Error rate (0-1)")
    last_updated: str
    
    class Config:
        schema_extra = {
            "example": {
                "endpoint": "/dashboard/summary/optimized",
                "avg_response_time_ms": 125.5,
                "p95_response_time_ms": 280.0,
                "p99_response_time_ms": 450.0,
                "total_requests": 1247,
                "cache_hit_rate": 0.85,
                "error_rate": 0.002,
                "last_updated": "2025-08-13T10:30:00Z"
            }
        }

class SystemHealth(BaseModel):
    """System health and performance overview"""
    status: str = Field(description="Overall system status")
    performance_metrics: List[PerformanceMetrics]
    cache_efficiency: Dict[str, float] = Field(description="Cache efficiency by type")
    database_health: Dict[str, Any] = Field(description="Database performance metrics")
    response_time_target_compliance: float = Field(
        ge=0, le=1, 
        description="Percentage of requests meeting <500ms target"
    )
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "performance_metrics": [],
                "cache_efficiency": {
                    "dashboard": 0.87,
                    "provisions": 0.92,
                    "drill_down": 0.78
                },
                "database_health": {
                    "avg_query_time_ms": 45.2,
                    "active_connections": 12,
                    "slow_queries_count": 2
                },
                "response_time_target_compliance": 0.94,
                "timestamp": "2025-08-13T10:30:00Z"
            }
        }

# Batch Operations Schemas

class BatchOperationStatus(BaseModel):
    """Status for batch operations (cache warming, etc.)"""
    operation_id: str
    operation_type: str = Field(description="Type of batch operation")
    status: str = Field(description="Current status")
    progress: float = Field(ge=0, le=100, description="Progress percentage")
    items_processed: int = Field(ge=0)
    items_total: int = Field(ge=0)
    started_at: str
    estimated_completion: Optional[str] = None
    error_count: int = Field(default=0, ge=0)
    
    class Config:
        schema_extra = {
            "example": {
                "operation_id": "cache_warm_2025_08",
                "operation_type": "cache_warming",
                "status": "processing",
                "progress": 75.5,
                "items_processed": 151,
                "items_total": 200,
                "started_at": "2025-08-13T10:25:00Z",
                "estimated_completion": "2025-08-13T10:35:00Z",
                "error_count": 0
            }
        }

# Error Response Schemas

class OptimizedErrorResponse(BaseModel):
    """Standardized error response for optimized endpoints"""
    error_code: str = Field(description="Machine-readable error code")
    error_message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    endpoint: str = Field(description="Endpoint that generated the error")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    
    class Config:
        schema_extra = {
            "example": {
                "error_code": "CALCULATION_TIMEOUT",
                "error_message": "Dashboard calculation exceeded 500ms timeout",
                "details": {
                    "calculation_time_ms": 652.3,
                    "timeout_threshold_ms": 500,
                    "month": "2025-08"
                },
                "endpoint": "/dashboard/summary/optimized",
                "timestamp": "2025-08-13T10:30:00Z",
                "request_id": "req_123456"
            }
        }

# Validation Functions

def validate_month_format(month: str) -> str:
    """Validate month format is YYYY-MM"""
    import re
    if not re.match(r"^\d{4}-\d{2}$", month):
        raise ValueError("Month must be in YYYY-MM format")
    return month

def validate_positive_amount(amount: float) -> float:
    """Validate amount is positive"""
    if amount < 0:
        raise ValueError("Amount must be positive")
    return round(amount, 2)

# Export commonly used schemas
__all__ = [
    "OptimizedDashboardSummary",
    "CategoryDrillDownResponse", 
    "ProvisionCalculationResponse",
    "FixedExpenseResponse",
    "SlimProvision",
    "SlimFixedExpense",
    "CategorySummary",
    "TransactionSummary",
    "PerformanceMetrics",
    "SystemHealth",
    "BatchOperationStatus",
    "OptimizedErrorResponse",
    "DrillDownLevel",
    "ExpenseType",
    "CacheStatus"
]