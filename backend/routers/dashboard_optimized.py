"""
Optimized Dashboard Router for High-Performance Provision-Centered Navigation
Designed for <500ms response times with efficient drill-down capabilities
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text, func, case, and_, or_
from pydantic import BaseModel, Field

from models.database import get_db, Transaction, CustomProvision, FixedLine, Config
from models.schemas import ConfigOut, CustomProvisionResponse, FixedLineOut
from auth import get_current_user
from services.redis_cache import redis_cache, get_cache_key
from services.calculations import calculate_provision_amount
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Performance monitoring
class PerformanceMetrics:
    def __init__(self):
        self.metrics = {}
    
    @asynccontextmanager
    async def measure(self, operation: str):
        start_time = time.time()
        try:
            yield
        finally:
            duration = (time.time() - start_time) * 1000
            self.metrics[operation] = {
                "duration_ms": duration,
                "timestamp": datetime.now().isoformat(),
                "status": "slow" if duration > 500 else "normal"
            }
            if duration > 500:
                logger.warning(f"Slow operation: {operation} took {duration:.2f}ms")

performance_monitor = PerformanceMetrics()

# Response Models for Optimized Endpoints

class SlimProvisionResponse(BaseModel):
    """Lightweight provision response for dashboard overview"""
    id: int
    name: str
    icon: str
    color: str
    monthly_amount: float
    member1_amount: float
    member2_amount: float
    progress_percentage: float = 0.0
    category: str

class OptimizedDashboardSummary(BaseModel):
    """Ultra-fast dashboard summary with minimal data"""
    month: str
    member1: str
    member2: str
    
    # Core totals
    total_expenses: float
    total_provisions: float
    total_fixed: float
    total_variable: float
    
    # Member splits
    member1_total: float
    member2_total: float
    
    # Metadata for drill-down
    active_provisions_count: int
    active_fixed_count: int
    transaction_count: int
    
    # Performance data
    calculation_timestamp: str
    cache_hit: bool = False
    
    # Drill-down URLs for efficient navigation
    drill_down_urls: Dict[str, str] = Field(default_factory=dict)

class CategoryDrillDownResponse(BaseModel):
    """Efficient drill-down response with pagination"""
    category: str
    month: str
    level: str  # "summary", "details", "transactions"
    
    # Summary data
    total_amount: float
    transaction_count: int
    avg_amount: float
    
    # Detailed data (when level != "summary")
    items: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Pagination
    pagination: Dict[str, Any] = Field(default_factory=dict)
    
    # Navigation options
    drill_down_options: List[str] = Field(default_factory=list)
    parent_category: Optional[str] = None

class ProvisionCalculationResult(BaseModel):
    """Fast provision calculation with caching metadata"""
    month: str
    provisions: List[SlimProvisionResponse]
    
    # Totals
    total_monthly_amount: float
    total_member1: float
    total_member2: float
    
    # Tax calculation details
    net_revenues: Dict[str, float]
    split_ratios: Dict[str, float]
    
    # Performance metadata
    calculation_time_ms: float
    cache_hit: bool = False

# Utility Functions

def get_config_hash(config: Config) -> str:
    """Generate hash for config to enable effective caching"""
    config_data = f"{config.rev1}:{config.rev2}:{config.tax_rate1}:{config.tax_rate2}:{config.split_mode}:{config.split1}:{config.split2}"
    return str(hash(config_data))

async def get_monthly_cache_key(month: str, cache_type: str) -> str:
    """Generate cache keys for monthly data"""
    return f"dashboard_v2:{cache_type}:{month}"

async def execute_optimized_aggregation(db: Session, month: str) -> Dict[str, Any]:
    """Single optimized query for all dashboard aggregations"""
    
    query = text("""
        SELECT 
            -- Variable expenses aggregation
            COALESCE(SUM(CASE WHEN expense_type = 'VARIABLE' AND exclude = 0 THEN amount ELSE 0 END), 0) as var_total,
            COUNT(CASE WHEN expense_type = 'VARIABLE' AND exclude = 0 THEN 1 END) as var_count,
            
            -- Fixed expenses aggregation  
            COALESCE(SUM(CASE WHEN expense_type = 'FIXED' AND exclude = 0 THEN amount ELSE 0 END), 0) as fixed_total,
            COUNT(CASE WHEN expense_type = 'FIXED' AND exclude = 0 THEN 1 END) as fixed_count,
            
            -- Total transaction count
            COUNT(CASE WHEN exclude = 0 THEN 1 END) as total_transactions,
            
            -- Category breakdown as JSON-like string for parsing
            GROUP_CONCAT(
                DISTINCT category || ':' || 
                COALESCE(SUM(CASE WHEN exclude = 0 THEN amount ELSE 0 END), 0)
            ) as category_breakdown,
            
            -- Date range for validation
            MIN(date_op) as first_date,
            MAX(date_op) as last_date
            
        FROM transactions 
        WHERE month = :month
    """)
    
    result = db.execute(query, {"month": month}).first()
    
    if not result:
        return {
            "var_total": 0.0, "var_count": 0,
            "fixed_total": 0.0, "fixed_count": 0,
            "total_transactions": 0,
            "category_breakdown": {},
            "date_range": {"first": None, "last": None}
        }
    
    # Parse category breakdown
    categories = {}
    if result.category_breakdown:
        for item in result.category_breakdown.split(','):
            if ':' in item:
                cat, amount = item.split(':', 1)
                categories[cat] = float(amount)
    
    return {
        "var_total": float(result.var_total or 0),
        "var_count": int(result.var_count or 0),
        "fixed_total": float(result.fixed_total or 0),
        "fixed_count": int(result.fixed_count or 0),
        "total_transactions": int(result.total_transactions or 0),
        "category_breakdown": categories,
        "date_range": {
            "first": result.first_date.isoformat() if result.first_date else None,
            "last": result.last_date.isoformat() if result.last_date else None
        }
    }

async def calculate_provisions_optimized(db: Session, config: Config) -> Dict[str, Any]:
    """Optimized provision calculation with caching"""
    
    config_hash = get_config_hash(config)
    cache_key = f"provisions_calc:{config_hash}"
    
    # Try cache first
    cached_result = await redis_cache.get(cache_key)
    if cached_result:
        return {"cache_hit": True, **json.loads(cached_result)}
    
    start_time = time.time()
    
    # Calculate net revenues (with tax rates)
    net1 = config.rev1 * (1 - (config.tax_rate1 or 0) / 100)
    net2 = config.rev2 * (1 - (config.tax_rate2 or 0) / 100)
    total_net = net1 + net2
    
    # Calculate split ratios
    if config.split_mode == "revenus" and total_net > 0:
        split1, split2 = net1 / total_net, net2 / total_net
    else:
        split1, split2 = config.split1, config.split2
    
    # Get active provisions with single query
    provisions = db.query(CustomProvision).filter(
        CustomProvision.is_active == True
    ).order_by(CustomProvision.display_order, CustomProvision.name).all()
    
    # Calculate provision amounts
    provision_results = []
    total_monthly = 0.0
    total_member1 = 0.0
    total_member2 = 0.0
    
    base_calculations = {
        "net_revenues": {"member1": net1, "member2": net2, "total": total_net},
        "split_ratios": {"member1": split1, "member2": split2}
    }
    
    for provision in provisions:
        # Calculate monthly amount based on provision settings
        if provision.base_calculation == "fixed":
            monthly_amount = provision.fixed_amount or 0
        elif provision.base_calculation == "member1":
            monthly_amount = net1 * (provision.percentage or 0) / 100
        elif provision.base_calculation == "member2":
            monthly_amount = net2 * (provision.percentage or 0) / 100
        else:  # "total"
            monthly_amount = total_net * (provision.percentage or 0) / 100
        
        # Calculate member splits
        if provision.split_mode == "50/50":
            member1_amount = monthly_amount * 0.5
            member2_amount = monthly_amount * 0.5
        elif provision.split_mode == "100/0":
            member1_amount = monthly_amount
            member2_amount = 0
        elif provision.split_mode == "0/100":
            member1_amount = 0
            member2_amount = monthly_amount
        elif provision.split_mode == "custom":
            member1_amount = monthly_amount * (provision.split_member1 or 50) / 100
            member2_amount = monthly_amount * (provision.split_member2 or 50) / 100
        else:  # "key" - use revenue-based split
            member1_amount = monthly_amount * split1
            member2_amount = monthly_amount * split2
        
        # Calculate progress percentage
        progress_percentage = 0.0
        if provision.target_amount and provision.target_amount > 0:
            progress_percentage = min(100.0, (provision.current_amount or 0) / provision.target_amount * 100)
        
        provision_result = {
            "id": provision.id,
            "name": provision.name,
            "icon": provision.icon,
            "color": provision.color,
            "monthly_amount": round(monthly_amount, 2),
            "member1_amount": round(member1_amount, 2),
            "member2_amount": round(member2_amount, 2),
            "progress_percentage": round(progress_percentage, 1),
            "category": provision.category
        }
        
        provision_results.append(provision_result)
        total_monthly += monthly_amount
        total_member1 += member1_amount
        total_member2 += member2_amount
    
    calculation_time = (time.time() - start_time) * 1000
    
    result = {
        "provisions": provision_results,
        "totals": {
            "total_monthly_amount": round(total_monthly, 2),
            "total_member1": round(total_member1, 2),
            "total_member2": round(total_member2, 2)
        },
        "base_calculations": base_calculations,
        "calculation_time_ms": round(calculation_time, 2),
        "cache_hit": False
    }
    
    # Cache for 10 minutes (config rarely changes)
    await redis_cache.setex(cache_key, 600, json.dumps(result))
    
    return result

# Optimized Endpoints

@router.get("/dashboard/summary/optimized", response_model=OptimizedDashboardSummary)
async def get_optimized_dashboard_summary(
    month: str = Query(..., description="Month in YYYY-MM format"),
    force_refresh: bool = Query(False, description="Force cache refresh"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ultra-fast dashboard summary optimized for <200ms response time
    
    Features:
    - Single database query for all aggregations
    - Aggressive caching with smart invalidation
    - Minimal response payload
    - Pre-computed drill-down URLs
    """
    
    async with performance_monitor.measure("dashboard_summary_optimized"):
        # Check cache first (unless force refresh)
        cache_key = await get_monthly_cache_key(month, "summary_optimized")
        
        if not force_refresh:
            cached_result = await redis_cache.get(cache_key)
            if cached_result:
                data = json.loads(cached_result)
                data["cache_hit"] = True
                return OptimizedDashboardSummary(**data)
        
        # Get config for member names and calculations
        config = db.query(Config).first()
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        # Execute optimized aggregation query
        aggregation_data = await execute_optimized_aggregation(db, month)
        
        # Get provision calculations (cached separately)
        provision_data = await calculate_provisions_optimized(db, config)
        
        # Get active counts
        active_provisions_count = db.query(CustomProvision).filter(CustomProvision.is_active == True).count()
        active_fixed_count = db.query(FixedLine).filter(FixedLine.active == True).count()
        
        # Calculate member totals (simple split for now - can be enhanced)
        split1 = config.split1 if config.split_mode == "manuel" else 0.5
        split2 = config.split2 if config.split_mode == "manuel" else 0.5
        
        total_expenses = aggregation_data["var_total"] + aggregation_data["fixed_total"] + provision_data["totals"]["total_monthly_amount"]
        
        # Build response
        response_data = {
            "month": month,
            "member1": config.member1,
            "member2": config.member2,
            "total_expenses": round(total_expenses, 2),
            "total_provisions": provision_data["totals"]["total_monthly_amount"],
            "total_fixed": aggregation_data["fixed_total"],
            "total_variable": aggregation_data["var_total"],
            "member1_total": round(total_expenses * split1, 2),
            "member2_total": round(total_expenses * split2, 2),
            "active_provisions_count": active_provisions_count,
            "active_fixed_count": active_fixed_count,
            "transaction_count": aggregation_data["total_transactions"],
            "calculation_timestamp": datetime.now().isoformat(),
            "cache_hit": False,
            "drill_down_urls": {
                "provisions": f"/dashboard/provisions/details?month={month}",
                "fixed": f"/dashboard/fixed/details?month={month}",
                "variable": f"/dashboard/variable/details?month={month}",
                "categories": f"/dashboard/drill-down/categories?month={month}"
            }
        }
        
        # Cache for 5 minutes
        await redis_cache.setex(cache_key, 300, json.dumps(response_data))
        
        return OptimizedDashboardSummary(**response_data)

@router.get("/dashboard/drill-down/{category}", response_model=CategoryDrillDownResponse)
async def get_drill_down_data(
    category: str,
    month: str = Query(..., description="Month in YYYY-MM format"),
    level: str = Query("summary", description="Drill-down level: summary, details, transactions"),
    limit: int = Query(50, ge=1, le=200, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    expense_type: Optional[str] = Query(None, description="Filter by expense type: FIXED, VARIABLE"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Intelligent drill-down endpoint with efficient pagination
    Target: <300ms response time
    
    Levels:
    - summary: Basic category statistics
    - details: Subcategory breakdown 
    - transactions: Individual transactions
    """
    
    async with performance_monitor.measure(f"drill_down_{level}"):
        # Build cache key
        cache_key = f"drill_down:{category}:{month}:{level}:{expense_type}:{limit}:{offset}"
        
        # Check cache
        cached_result = await redis_cache.get(cache_key)
        if cached_result:
            return CategoryDrillDownResponse(**json.loads(cached_result))
        
        # Base query filters
        filters = [
            Transaction.month == month,
            Transaction.exclude == False
        ]
        
        if category.lower() != "all":
            filters.append(Transaction.category.ilike(f"%{category}%"))
        
        if expense_type:
            filters.append(Transaction.expense_type == expense_type.upper())
        
        # Build response based on level
        if level == "summary":
            # Category summary statistics
            query = db.query(
                func.sum(Transaction.amount).label('total_amount'),
                func.count(Transaction.id).label('transaction_count'),
                func.avg(Transaction.amount).label('avg_amount'),
                func.min(Transaction.amount).label('min_amount'),
                func.max(Transaction.amount).label('max_amount')
            ).filter(and_(*filters))
            
            result = query.first()
            
            response_data = {
                "category": category,
                "month": month,
                "level": level,
                "total_amount": float(result.total_amount or 0),
                "transaction_count": int(result.transaction_count or 0),
                "avg_amount": float(result.avg_amount or 0),
                "items": [{
                    "total_amount": float(result.total_amount or 0),
                    "transaction_count": int(result.transaction_count or 0),
                    "avg_amount": float(result.avg_amount or 0),
                    "min_amount": float(result.min_amount or 0),
                    "max_amount": float(result.max_amount or 0)
                }],
                "pagination": {"limit": limit, "offset": offset, "has_more": False},
                "drill_down_options": ["details", "transactions"]
            }
            
        elif level == "details":
            # Subcategory/tag breakdown
            query = db.query(
                Transaction.category_parent,
                func.sum(Transaction.amount).label('total_amount'),
                func.count(Transaction.id).label('transaction_count'),
                func.avg(Transaction.amount).label('avg_amount')
            ).filter(and_(*filters)).group_by(Transaction.category_parent)
            
            # Apply pagination
            total_count = query.count()
            results = query.offset(offset).limit(limit).all()
            
            items = [{
                "subcategory": result.category_parent or "Unknown",
                "total_amount": float(result.total_amount),
                "transaction_count": int(result.transaction_count),
                "avg_amount": float(result.avg_amount)
            } for result in results]
            
            response_data = {
                "category": category,
                "month": month,
                "level": level,
                "total_amount": sum(item["total_amount"] for item in items),
                "transaction_count": sum(item["transaction_count"] for item in items),
                "avg_amount": sum(item["total_amount"] for item in items) / len(items) if items else 0,
                "items": items,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total_count,
                    "has_more": (offset + limit) < total_count
                },
                "drill_down_options": ["transactions"],
                "parent_category": None
            }
            
        else:  # transactions
            # Individual transaction details
            query = db.query(Transaction).filter(and_(*filters))
            
            # Apply pagination
            total_count = query.count()
            transactions = query.order_by(Transaction.date_op.desc()).offset(offset).limit(limit).all()
            
            items = [{
                "id": tx.id,
                "date_op": tx.date_op.isoformat() if tx.date_op else None,
                "label": tx.label,
                "amount": float(tx.amount),
                "category": tx.category,
                "subcategory": tx.category_parent,
                "expense_type": tx.expense_type,
                "tags": tx.tags.split(',') if tx.tags else []
            } for tx in transactions]
            
            response_data = {
                "category": category,
                "month": month,
                "level": level,
                "total_amount": sum(item["amount"] for item in items),
                "transaction_count": len(items),
                "avg_amount": sum(item["amount"] for item in items) / len(items) if items else 0,
                "items": items,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total_count,
                    "has_more": (offset + limit) < total_count
                },
                "drill_down_options": [],
                "parent_category": category
            }
        
        # Cache for 3 minutes
        await redis_cache.setex(cache_key, 180, json.dumps(response_data))
        
        return CategoryDrillDownResponse(**response_data)

@router.get("/provisions/calculate/optimized", response_model=ProvisionCalculationResult)
async def calculate_provisions_optimized_endpoint(
    month: str = Query(..., description="Month for calculation context"),
    force_refresh: bool = Query(False, description="Force cache refresh"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ultra-fast provision calculation endpoint
    Target: <150ms response time
    
    Features:
    - Cached calculation results based on config hash
    - Single-pass calculation algorithm
    - Optimized tax rate and split computations
    """
    
    async with performance_monitor.measure("provisions_calculate_optimized"):
        # Get configuration
        config = db.query(Config).first()
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        # Calculate provisions with caching
        calculation_result = await calculate_provisions_optimized(db, config)
        
        return ProvisionCalculationResult(
            month=month,
            provisions=[SlimProvisionResponse(**p) for p in calculation_result["provisions"]],
            total_monthly_amount=calculation_result["totals"]["total_monthly_amount"],
            total_member1=calculation_result["totals"]["total_member1"],
            total_member2=calculation_result["totals"]["total_member2"],
            net_revenues=calculation_result["base_calculations"]["net_revenues"],
            split_ratios=calculation_result["base_calculations"]["split_ratios"],
            calculation_time_ms=calculation_result["calculation_time_ms"],
            cache_hit=calculation_result["cache_hit"]
        )

@router.get("/dashboard/performance/metrics")
async def get_performance_metrics(
    current_user = Depends(get_current_user)
):
    """
    Get performance metrics for monitoring dashboard
    """
    return {
        "metrics": performance_monitor.metrics,
        "cache_stats": await redis_cache.get_stats() if hasattr(redis_cache, 'get_stats') else {},
        "timestamp": datetime.now().isoformat()
    }

@router.post("/dashboard/cache/warm")
async def warm_dashboard_cache(
    background_tasks: BackgroundTasks,
    months: List[str] = Query(..., description="Months to warm cache for"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Background task to warm cache for specified months
    """
    
    async def warm_cache_task():
        for month in months:
            try:
                # Warm summary cache
                await get_optimized_dashboard_summary(month, True, current_user, db)
                
                # Warm common drill-down categories
                common_categories = ["alimentation", "transport", "logement", "loisirs"]
                for category in common_categories:
                    await get_drill_down_data(category, month, "summary", 50, 0, None, current_user, db)
                
                logger.info(f"Cache warmed for month: {month}")
            except Exception as e:
                logger.error(f"Cache warming failed for month {month}: {e}")
    
    background_tasks.add_task(warm_cache_task)
    
    return {
        "message": f"Cache warming initiated for {len(months)} months",
        "months": months,
        "status": "background_task_started"
    }

@router.delete("/dashboard/cache/invalidate")
async def invalidate_dashboard_cache(
    month: Optional[str] = Query(None, description="Specific month to invalidate, or all if not specified"),
    current_user = Depends(get_current_user)
):
    """
    Invalidate dashboard cache for specific month or all months
    """
    
    if month:
        # Invalidate specific month
        patterns = [
            f"dashboard_v2:*:{month}",
            f"drill_down:*:{month}:*",
            f"provisions_calc:*"  # Config-based, might affect all months
        ]
    else:
        # Invalidate all dashboard cache
        patterns = [
            "dashboard_v2:*",
            "drill_down:*",
            "provisions_calc:*"
        ]
    
    invalidated_count = 0
    for pattern in patterns:
        count = await redis_cache.delete_pattern(pattern) if hasattr(redis_cache, 'delete_pattern') else 0
        invalidated_count += count
    
    return {
        "message": f"Cache invalidated for {month if month else 'all months'}",
        "invalidated_keys": invalidated_count,
        "patterns": patterns
    }