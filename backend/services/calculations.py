"""
Business logic calculations for Budget API with Redis caching
"""
import logging
import datetime as dt
from typing import List, Optional, Dict, Tuple
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from models.database import Config, Transaction, FixedLine, CustomProvision
from services.redis_cache import get_redis_cache
from services.query_performance import monitor_query_performance, query_monitor
from config.settings import settings

logger = logging.getLogger(__name__)

# Initialize Redis cache
redis_cache = get_redis_cache()


def _cache_key(func_name: str, user_id: Optional[str] = None, *args) -> str:
    """Generate cache key for function and arguments with user context"""
    key_parts = [func_name]
    if user_id:
        key_parts = ["user", user_id, func_name]
    key_parts.extend(str(arg) for arg in args)
    return ":".join(key_parts)


def _get_from_cache(cache_key: str, use_redis: bool = True):
    """Get value from cache with fallback to Redis"""
    if not use_redis or not settings.cache.enable_cache:
        return None
    
    try:
        return redis_cache.get(cache_key)
    except Exception as e:
        logger.warning(f"Redis cache get failed for key '{cache_key}': {e}")
        return None


def _set_to_cache(cache_key: str, value: any, ttl: Optional[int] = None, use_redis: bool = True) -> bool:
    """Set value in cache with fallback to Redis"""
    if not use_redis or not settings.cache.enable_cache:
        return False
    
    try:
        if ttl is None:
            ttl = settings.redis.default_ttl
        return redis_cache.set(cache_key, value, ttl)
    except Exception as e:
        logger.warning(f"Redis cache set failed for key '{cache_key}': {e}")
        return False


def get_split(cfg: Config) -> Tuple[float, float]:
    """
    Calculate split ratios based on configuration
    Returns: (ratio_member1, ratio_member2)
    """
    if cfg.split_mode == "revenus":
        tot = (cfg.rev1 or 0) + (cfg.rev2 or 0)
        if tot <= 0:
            return 0.5, 0.5
        r1 = (cfg.rev1 or 0) / tot
        return r1, 1 - r1
    else:
        return cfg.split1, cfg.split2


def calculate_provision_amount(provision: CustomProvision, config: Config) -> Tuple[float, float, float]:
    """
    Calculate monthly provision amount and distribution
    Returns: (total_amount, member1_amount, member2_amount)
    """
    # Calculate base amount
    if provision.base_calculation == "total":
        base = (config.rev1 or 0) + (config.rev2 or 0)
    elif provision.base_calculation == "member1":
        base = config.rev1 or 0
    elif provision.base_calculation == "member2":
        base = config.rev2 or 0
    elif provision.base_calculation == "fixed":
        base = provision.fixed_amount or 0
    else:
        base = 0
    
    # Calculate monthly amount
    if provision.base_calculation == "fixed":
        monthly_amount = base  # Already monthly
    else:
        # Les revenus dans config sont déjà mensuels, pas besoin de diviser par 12
        monthly_amount = (base * provision.percentage / 100.0) if base else 0.0
    
    # Calculate distribution
    if provision.split_mode == "key":
        # Calculer la répartition basée sur les revenus NETS après impôts
        rev1_net = (config.rev1 or 0) * (1 - (getattr(config, 'tax_rate1', 0) or 0) / 100)
        rev2_net = (config.rev2 or 0) * (1 - (getattr(config, 'tax_rate2', 0) or 0) / 100)
        total_rev_net = rev1_net + rev2_net
        
        if total_rev_net > 0:
            r1 = rev1_net / total_rev_net
            r2 = rev2_net / total_rev_net
        else:
            r1 = r2 = 0.5
        member1_amount = monthly_amount * r1
        member2_amount = monthly_amount * r2
    elif provision.split_mode == "50/50":
        member1_amount = monthly_amount * 0.5
        member2_amount = monthly_amount * 0.5
    elif provision.split_mode == "100/0":
        member1_amount = monthly_amount
        member2_amount = 0
    elif provision.split_mode == "0/100":
        member1_amount = 0
        member2_amount = monthly_amount
    elif provision.split_mode == "custom":
        member1_amount = monthly_amount * (provision.split_member1 / 100.0)
        member2_amount = monthly_amount * (provision.split_member2 / 100.0)
    else:
        member1_amount = member2_amount = monthly_amount * 0.5
    
    return monthly_amount, member1_amount, member2_amount


def get_active_provisions(db: Session, current_date: dt.datetime = None) -> List[CustomProvision]:
    """Get all active provisions at a given date"""
    if current_date is None:
        current_date = dt.datetime.now()
    
    query = db.query(CustomProvision).filter(CustomProvision.is_active == True)
    
    # Filter by dates if applicable
    query = query.filter(
        (CustomProvision.start_date == None) | (CustomProvision.start_date <= current_date)
    ).filter(
        (CustomProvision.end_date == None) | (CustomProvision.end_date >= current_date)
    )
    
    return query.order_by(CustomProvision.display_order, CustomProvision.name).all()


def is_income_or_transfer(label: str, cat_parent: str) -> bool:
    """Check if transaction is income or transfer"""
    l = (label or "").lower()
    cp = (cat_parent or "").lower()
    
    if any(keyword in l for keyword in ["virement", "vir ", "vir/"]):
        return True
    if "virements emis" in cp:
        return True
    if any(keyword in l for keyword in ["rembourse", "refund"]):
        return True
    if "remboursement" in cp:
        return True
    if any(keyword in l for keyword in ["salaire", "payroll", "paye"]):
        return True
    
    return False


def split_amount(amount: float, mode: str, r1: float, r2: float, s1: float, s2: float) -> Tuple[float, float]:
    """Split amount according to mode"""
    if mode == "50/50":
        return amount / 2.0, amount / 2.0
    elif mode == "clé":
        return amount * r1, amount * r2
    elif mode == "m1":
        return amount, 0.0
    elif mode == "m2":
        return 0.0, amount
    elif mode == "manuel":
        return amount * (s1 or 0.0), amount * (s2 or 0.0)
    else:
        return amount * r1, amount * r2


def calculate_monthly_trends(db: Session, months: List[str], user_id: Optional[str] = None) -> List[Dict]:
    """Calculate monthly trends for specified months with Redis caching"""
    cache_key = _cache_key("monthly_trends", user_id, *months)
    
    # Check Redis cache
    cached_data = _get_from_cache(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache hit for monthly trends: {cache_key}")
        return cached_data
    
    logger.debug(f"Cache miss for monthly trends: {cache_key}")
    
    trends = []
    for month in months:
        expenses_result = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.is_expense == True,
            Transaction.exclude == False,
            Transaction.amount < 0
        ).all()
        
        income_result = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.is_expense == False,
            Transaction.exclude == False,
            Transaction.amount > 0
        ).all()
        
        total_expenses = sum(abs(tx.amount or 0) for tx in expenses_result)
        total_income = sum(tx.amount or 0 for tx in income_result)
        net = total_income - total_expenses
        transaction_count = len(expenses_result) + len(income_result)
        
        from models.schemas import MonthlyTrend
        trends.append(MonthlyTrend(
            month=month,
            total_expenses=total_expenses,
            total_income=total_income,
            net_balance=net,
            expense_trend=0.0  # Would need previous month comparison
        ))
    
    # Cache result in Redis with specific TTL for trends
    _set_to_cache(cache_key, trends, ttl=settings.redis.trends_ttl)
    return trends


def calculate_category_breakdown(db: Session, month: str, user_id: Optional[str] = None) -> List[Dict]:
    """Calculate category breakdown for a month with Redis caching"""
    cache_key = _cache_key("category_breakdown", user_id, month)
    
    # Check Redis cache
    cached_data = _get_from_cache(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache hit for category breakdown: {cache_key}")
        return cached_data
    
    logger.debug(f"Cache miss for category breakdown: {cache_key}")
    
    transactions = db.query(Transaction).filter(
        Transaction.month == month,
        Transaction.exclude == False,
        Transaction.amount < 0  # Only expenses
    ).all()
    
    # Group by category
    category_data = {}
    total_expenses = 0
    
    for tx in transactions:
        category = tx.category or "Non classé"
        amount = abs(tx.amount or 0)
        
        if category not in category_data:
            category_data[category] = {
                "category": category,
                "amount": 0,
                "transaction_count": 0,
                "transactions": []
            }
        
        category_data[category]["amount"] += amount
        category_data[category]["transaction_count"] += 1
        # Don't store full transaction objects in cache - just the summary
        total_expenses += amount
    
    # Calculate percentages and averages
    breakdown = []
    for category, data in category_data.items():
        percentage = (data["amount"] / total_expenses * 100) if total_expenses > 0 else 0
        avg_transaction = data["amount"] / data["transaction_count"] if data["transaction_count"] > 0 else 0
        
        from models.schemas import CategoryBreakdown as CategoryBreakdownSchema
        breakdown.append(CategoryBreakdownSchema(
            category=category,
            amount=data["amount"],
            percentage=percentage,
            transaction_count=data["transaction_count"],
            avg_transaction=avg_transaction
        ))
    
    # Sort by amount descending
    breakdown.sort(key=lambda x: x.amount, reverse=True)
    
    # Cache result in Redis
    _set_to_cache(cache_key, breakdown, ttl=settings.redis.default_ttl)
    return breakdown


def calculate_kpi_summary(db: Session, months: List[str], user_id: Optional[str] = None) -> Dict:
    """Calculate KPI summary for given months with Redis caching"""
    cache_key = _cache_key("kpi_summary", user_id, *months)
    
    # Check Redis cache
    cached_data = _get_from_cache(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache hit for KPI summary: {cache_key}")
        return cached_data
    
    logger.debug(f"Cache miss for KPI summary: {cache_key}")
    
    if not months:
        return {
            "period_start": "",
            "period_end": "",
            "total_expenses": 0,
            "total_income": 0,
            "net_balance": 0,
            "avg_monthly_expenses": 0,
            "avg_monthly_income": 0,
            "expense_growth_rate": 0,
            "income_growth_rate": 0,
            "savings_rate": 0
        }
    
    # Get all transactions for the period
    transactions = db.query(Transaction).filter(
        Transaction.month.in_(months),
        Transaction.exclude == False
    ).all()
    
    total_expenses = sum(abs(tx.amount or 0) for tx in transactions if (tx.amount or 0) < 0)
    total_income = sum(tx.amount or 0 for tx in transactions if (tx.amount or 0) > 0)
    net_balance = total_income - total_expenses
    
    num_months = len(months)
    avg_monthly_expenses = total_expenses / num_months if num_months > 0 else 0
    avg_monthly_income = total_income / num_months if num_months > 0 else 0
    savings_rate = (net_balance / total_income * 100) if total_income > 0 else 0
    
    # Calculate growth rates if we have enough months
    expense_growth_rate = 0
    income_growth_rate = 0
    
    if len(months) >= 2:
        months_sorted = sorted(months)
        first_month = months_sorted[0]
        last_month = months_sorted[-1]
        
        first_month_expenses = sum(
            abs(tx.amount or 0) for tx in transactions 
            if tx.month == first_month and (tx.amount or 0) < 0
        )
        last_month_expenses = sum(
            abs(tx.amount or 0) for tx in transactions 
            if tx.month == last_month and (tx.amount or 0) < 0
        )
        
        first_month_income = sum(
            tx.amount or 0 for tx in transactions 
            if tx.month == first_month and (tx.amount or 0) > 0
        )
        last_month_income = sum(
            tx.amount or 0 for tx in transactions 
            if tx.month == last_month and (tx.amount or 0) > 0
        )
        
        if first_month_expenses > 0:
            expense_growth_rate = ((last_month_expenses - first_month_expenses) / first_month_expenses) * 100
        
        if first_month_income > 0:
            income_growth_rate = ((last_month_income - first_month_income) / first_month_income) * 100
    
    # Import schema here to avoid circular imports
    from models.schemas import KPISummary, CategoryBreakdown
    
    # Create top categories (stub for now - would need actual category breakdown)
    top_categories = []
    
    result = KPISummary(
        total_income=total_income,
        total_expenses=total_expenses,
        net_balance=net_balance,
        savings_rate=savings_rate,
        avg_monthly_expense=avg_monthly_expenses,
        expense_trend=expense_growth_rate,
        top_categories=top_categories,
        months_analyzed=months
    )
    
    # Cache result in Redis with summary TTL (longer for expensive calculations)
    _set_to_cache(cache_key, result, ttl=settings.redis.summary_ttl)
    return result


def detect_anomalies(db: Session, month: str, user_id: Optional[str] = None) -> List[Dict]:
    """Detect spending anomalies for a month with Redis caching"""
    cache_key = _cache_key("anomalies", user_id, month)
    
    # Check Redis cache
    cached_data = _get_from_cache(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache hit for anomalies: {cache_key}")
        return cached_data
    
    logger.debug(f"Cache miss for anomalies: {cache_key}")
    
    # Get transactions for the month
    current_month_txs = db.query(Transaction).filter(
        Transaction.month == month,
        Transaction.exclude == False,
        Transaction.amount < 0  # Only expenses
    ).all()
    
    if not current_month_txs:
        return []
    
    # Get historical data for comparison (last 6 months)
    try:
        year, month_num = map(int, month.split('-'))
        historical_months = []
        
        for i in range(1, 7):  # Last 6 months
            hist_month_num = month_num - i
            hist_year = year
            
            if hist_month_num <= 0:
                hist_month_num += 12
                hist_year -= 1
            
            historical_months.append(f"{hist_year:04d}-{hist_month_num:02d}")
        
        historical_txs = db.query(Transaction).filter(
            Transaction.month.in_(historical_months),
            Transaction.exclude == False,
            Transaction.amount < 0
        ).all()
        
    except Exception as e:
        logger.error(f"Error calculating historical data: {e}")
        return []
    
    # Calculate category averages and standard deviations
    category_stats = {}
    for tx in historical_txs:
        category = tx.category or "Non classé"
        amount = abs(tx.amount or 0)
        
        if category not in category_stats:
            category_stats[category] = []
        category_stats[category].append(amount)
    
    # Calculate statistics
    for category in category_stats:
        amounts = category_stats[category]
        if len(amounts) > 1:
            category_stats[category] = {
                'mean': np.mean(amounts),
                'std': np.std(amounts),
                'count': len(amounts)
            }
        else:
            category_stats[category] = {
                'mean': amounts[0] if amounts else 0,
                'std': 0,
                'count': len(amounts)
            }
    
    # Detect anomalies (transactions > 2 standard deviations from mean)
    anomalies = []
    for tx in current_month_txs:
        category = tx.category or "Non classé"
        amount = abs(tx.amount or 0)
        
        if category in category_stats:
            stats = category_stats[category]
            if stats['std'] > 0:
                z_score = (amount - stats['mean']) / stats['std']
                if abs(z_score) > 2:  # Anomaly threshold
                    from models.schemas import AnomalyDetection
                    anomalies.append(AnomalyDetection(
                        transaction_id=tx.id,
                        date=str(tx.date_op) if tx.date_op else "",
                        amount=tx.amount or 0,
                        category=tx.category or "",
                        label=tx.label or "",
                        anomaly_type="high_amount" if z_score > 2 else "low_amount",
                        score=abs(z_score) / 3.0  # Normalize to 0-1
                    ))
    
    # Sort by score (most anomalous first)
    anomalies.sort(key=lambda x: x.score, reverse=True)
    
    # Cache result in Redis with anomaly TTL
    _set_to_cache(cache_key, anomalies, ttl=settings.redis.anomaly_ttl)
    return anomalies


def calculate_spending_patterns(db: Session, months: List[str], user_id: Optional[str] = None) -> List[Dict]:
    """Calculate spending patterns by day of week with Redis caching"""
    cache_key = _cache_key("spending_patterns", user_id, *months)
    
    # Check Redis cache
    cached_data = _get_from_cache(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache hit for spending patterns: {cache_key}")
        return cached_data
    
    logger.debug(f"Cache miss for spending patterns: {cache_key}")
    
    transactions = db.query(Transaction).filter(
        Transaction.month.in_(months),
        Transaction.exclude == False,
        Transaction.amount < 0,  # Only expenses
        Transaction.date_op != None
    ).all()
    
    # Group by day of week
    day_patterns = {}
    day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    
    for tx in transactions:
        if tx.date_op:
            day_of_week = tx.date_op.weekday()  # 0 = Monday
            amount = abs(tx.amount or 0)
            
            if day_of_week not in day_patterns:
                day_patterns[day_of_week] = {
                    "amounts": [],
                    "count": 0
                }
            
            day_patterns[day_of_week]["amounts"].append(amount)
            day_patterns[day_of_week]["count"] += 1
    
    # Calculate averages
    patterns = []
    for day_num in range(7):
        if day_num in day_patterns:
            amounts = day_patterns[day_num]["amounts"]
            avg_amount = sum(amounts) / len(amounts) if amounts else 0
            transaction_count = len(amounts)
        else:
            avg_amount = 0
            transaction_count = 0
        
        from models.schemas import SpendingPattern
        patterns.append(SpendingPattern(
            day_of_week=day_num,
            day_name=day_names[day_num],
            avg_amount=avg_amount,
            transaction_count=transaction_count
        ))
    
    # Cache result in Redis with trends TTL
    _set_to_cache(cache_key, patterns, ttl=settings.redis.trends_ttl)
    return patterns


def calculate_fixed_lines_total(db: Session, config: Config) -> Tuple[float, float, float]:
    """
    Calculate total fixed lines amounts for the month
    Returns: (total_monthly, member1_share, member2_share)
    """
    fixed_lines = db.query(FixedLine).filter(FixedLine.active == True).all()
    
    total_monthly = 0.0
    member1_total = 0.0
    member2_total = 0.0
    
    r1, r2 = get_split(config)
    
    for line in fixed_lines:
        # Convert to monthly amount
        if line.freq == "mensuelle":
            monthly_amount = line.amount
        elif line.freq == "trimestrielle":
            monthly_amount = line.amount / 3.0
        elif line.freq == "annuelle":
            monthly_amount = line.amount / 12.0
        else:
            monthly_amount = line.amount
        
        # Split amount
        member1_share, member2_share = split_amount(
            monthly_amount, line.split_mode, r1, r2, line.split1, line.split2
        )
        
        total_monthly += monthly_amount
        member1_total += member1_share
        member2_total += member2_share
    
    return total_monthly, member1_total, member2_total


def calculate_provisions_total(db: Session, config: Config) -> Tuple[float, float, float]:
    """
    Calculate total provisions amounts for the month
    Returns: (total_monthly, member1_share, member2_share)
    """
    provisions = get_active_provisions(db)
    
    total_monthly = 0.0
    member1_total = 0.0
    member2_total = 0.0
    
    for provision in provisions:
        monthly_amount, member1_share, member2_share = calculate_provision_amount(provision, config)
        
        total_monthly += monthly_amount
        member1_total += member1_share
        member2_total += member2_share
    
    return total_monthly, member1_total, member2_total


def get_previous_month(month: str) -> Optional[str]:
    """Get previous month string (YYYY-MM format)"""
    try:
        year, month_num = map(int, month.split('-'))
        
        if month_num == 1:
            return f"{year-1:04d}-12"
        else:
            return f"{year:04d}-{month_num-1:02d}"
    except Exception:
        return None


def clear_calculation_cache(user_id: Optional[str] = None):
    """Clear the calculation cache in Redis"""
    try:
        if user_id:
            # Clear cache for specific user
            pattern = f"user:{user_id}:*"
        else:
            # Clear all calculation cache
            pattern = "*"
        
        deleted_count = redis_cache.delete_pattern(pattern)
        logger.info(f"Calculation cache cleared: {deleted_count} entries deleted for pattern '{pattern}'")
        return deleted_count
    except Exception as e:
        logger.error(f"Failed to clear calculation cache: {e}")
        return 0


def get_cache_stats():
    """Get Redis cache statistics"""
    try:
        stats = redis_cache.get_stats()
        health = redis_cache.health_check()
        
        return {
            "type": "redis",
            "stats": stats,
            "health": health,
            "default_ttl_seconds": settings.redis.default_ttl,
            "summary_ttl_seconds": settings.redis.summary_ttl,
            "trends_ttl_seconds": settings.redis.trends_ttl,
            "anomaly_ttl_seconds": settings.redis.anomaly_ttl
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {
            "type": "redis",
            "error": str(e),
            "fallback": True
        }


def invalidate_calculations_for_month(month: str, user_id: Optional[str] = None):
    """Invalidate all calculation cache entries for a specific month"""
    try:
        from services.redis_cache import invalidate_cache_for_month
        deleted_count = invalidate_cache_for_month(month, user_id)
        logger.info(f"Invalidated {deleted_count} calculation entries for month {month}")
        return deleted_count
    except Exception as e:
        logger.error(f"Failed to invalidate cache for month {month}: {e}")
        return 0


def warm_calculations_cache(db: Session, month: str, user_id: Optional[str] = None):
    """Warm up calculation cache for a specific month"""
    try:
        # Pre-compute common calculations to warm the cache
        logger.info(f"Warming calculation cache for month {month}")
        
        # Monthly trends (single month)
        calculate_monthly_trends(db, [month], user_id)
        
        # Category breakdown
        calculate_category_breakdown(db, month, user_id)
        
        # KPI summary for current month
        calculate_kpi_summary(db, [month], user_id)
        
        # Anomaly detection
        detect_anomalies(db, month, user_id)
        
        # Spending patterns (last 3 months including current)
        try:
            year, month_num = map(int, month.split('-'))
            months = []
            for i in range(3):
                calc_month_num = month_num - i
                calc_year = year
                if calc_month_num <= 0:
                    calc_month_num += 12
                    calc_year -= 1
                months.append(f"{calc_year:04d}-{calc_month_num:02d}")
            
            calculate_spending_patterns(db, months, user_id)
            
        except Exception as e:
            logger.warning(f"Failed to warm spending patterns cache: {e}")
        
        logger.info(f"Successfully warmed calculation cache for month {month}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to warm calculation cache for month {month}: {e}")
        return False


def calculate_provisions_summary(db: Session, config: Config) -> Dict:
    """Calculate provisions summary statistics"""
    try:
        provisions = get_active_provisions(db)
        
        total_monthly_amount = 0.0
        total_target_amount = 0.0
        total_current_amount = 0.0
        provisions_by_category = {}
        progress_percentages = []
        
        for provision in provisions:
            monthly_amount, _, _ = calculate_provision_amount(provision, config)
            total_monthly_amount += monthly_amount
            
            if provision.target_amount:
                total_target_amount += provision.target_amount
            
            if provision.current_amount:
                total_current_amount += provision.current_amount
            
            # Calculate progress percentage
            if provision.target_amount and provision.target_amount > 0:
                progress = min(100.0, (provision.current_amount / provision.target_amount) * 100)
                progress_percentages.append(progress)
            
            # Group by category
            category = provision.category or "épargne"
            if category not in provisions_by_category:
                provisions_by_category[category] = {
                    "count": 0,
                    "monthly_amount": 0.0,
                    "target_amount": 0.0,
                    "current_amount": 0.0
                }
            
            provisions_by_category[category]["count"] += 1
            provisions_by_category[category]["monthly_amount"] += monthly_amount
            provisions_by_category[category]["target_amount"] += provision.target_amount or 0
            provisions_by_category[category]["current_amount"] += provision.current_amount or 0
        
        average_progress = sum(progress_percentages) / len(progress_percentages) if progress_percentages else 0.0
        
        from models.schemas import CustomProvisionSummary
        return CustomProvisionSummary(
            total_active_provisions=len(provisions),
            total_monthly_amount=total_monthly_amount,
            total_target_amount=total_target_amount,
            total_current_amount=total_current_amount,
            average_progress_percentage=average_progress,
            provisions_by_category=provisions_by_category
        )
        
    except Exception as e:
        logger.error(f"Error calculating provisions summary: {str(e)}")
        raise