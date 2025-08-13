"""
Optimized Calculation Engine for High-Performance Budget Operations
Designed for <200ms calculation times with intelligent caching
"""

import logging
import json
import time
import hashlib
from functools import lru_cache
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session
from sqlalchemy import text, func

from models.database import Config, CustomProvision, FixedLine, Transaction
from services.redis_cache import redis_cache

logger = logging.getLogger(__name__)

@dataclass
class CalculationContext:
    """Immutable calculation context for caching"""
    rev1: float
    rev2: float
    tax_rate1: float
    tax_rate2: float
    split_mode: str
    split1: float
    split2: float
    
    def __post_init__(self):
        # Ensure immutability by converting to hashable types
        object.__setattr__(self, 'cache_key', self._generate_cache_key())
    
    def _generate_cache_key(self) -> str:
        """Generate unique cache key for this configuration"""
        config_str = f"{self.rev1}:{self.rev2}:{self.tax_rate1}:{self.tax_rate2}:{self.split_mode}:{self.split1}:{self.split2}"
        return hashlib.md5(config_str.encode()).hexdigest()

class OptimizedCalculationEngine:
    """
    High-performance calculation engine with multi-level caching
    
    Features:
    - LRU cache for repeated calculations
    - Redis cache for cross-request persistence
    - Single-pass algorithms for complex computations
    - Decimal precision for financial accuracy
    """
    
    def __init__(self):
        self.calculation_cache = {}
        self.performance_metrics = {}
    
    def _start_timer(self) -> float:
        """Start performance timer"""
        return time.perf_counter()
    
    def _end_timer(self, operation: str, start_time: float):
        """End performance timer and log metrics"""
        duration = (time.perf_counter() - start_time) * 1000
        self.performance_metrics[operation] = {
            "duration_ms": round(duration, 2),
            "timestamp": time.time()
        }
        if duration > 100:  # Log slow operations
            logger.warning(f"Slow calculation: {operation} took {duration:.2f}ms")
    
    @lru_cache(maxsize=200)
    def calculate_net_revenues(self, rev1: float, rev2: float, tax_rate1: float, tax_rate2: float) -> Tuple[Decimal, Decimal]:
        """
        Calculate net revenues after taxes with high precision
        
        Args:
            rev1: Member 1 gross revenue
            rev2: Member 2 gross revenue  
            tax_rate1: Member 1 tax rate (percentage)
            tax_rate2: Member 2 tax rate (percentage)
            
        Returns:
            Tuple of (net_revenue_1, net_revenue_2) as Decimal for precision
        """
        # Use Decimal for financial precision
        gross1 = Decimal(str(rev1))
        gross2 = Decimal(str(rev2))
        rate1 = Decimal(str(tax_rate1)) / Decimal('100')
        rate2 = Decimal(str(tax_rate2)) / Decimal('100')
        
        net1 = gross1 * (Decimal('1') - rate1)
        net2 = gross2 * (Decimal('1') - rate2)
        
        # Round to 2 decimal places for currency
        return (
            net1.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            net2.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        )
    
    @lru_cache(maxsize=100)
    def calculate_split_ratios(self, split_mode: str, net1: float, net2: float, manual_split1: float = 0.5) -> Tuple[Decimal, Decimal]:
        """
        Calculate split ratios based on mode with caching
        
        Args:
            split_mode: "revenus" or "manuel" 
            net1: Net revenue member 1
            net2: Net revenue member 2
            manual_split1: Manual split for member 1 (if manual mode)
            
        Returns:
            Tuple of (split_ratio_1, split_ratio_2) as Decimal
        """
        if split_mode == "revenus":
            total_net = Decimal(str(net1)) + Decimal(str(net2))
            if total_net > 0:
                ratio1 = Decimal(str(net1)) / total_net
                ratio2 = Decimal(str(net2)) / total_net
            else:
                ratio1 = ratio2 = Decimal('0.5')
        else:  # manuel
            ratio1 = Decimal(str(manual_split1))
            ratio2 = Decimal('1') - ratio1
        
        return (
            ratio1.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP),
            ratio2.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        )
    
    async def get_base_calculations(self, context: CalculationContext) -> Dict[str, Any]:
        """
        Get or calculate base financial calculations with caching
        
        Returns cached base calculations or computes them if needed.
        Base calculations include net revenues and split ratios.
        """
        cache_key = f"base_calc:{context.cache_key}"
        
        # Try Redis cache first
        cached_result = await redis_cache.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        
        start_time = self._start_timer()
        
        # Calculate net revenues
        net1, net2 = self.calculate_net_revenues(
            context.rev1, context.rev2, 
            context.tax_rate1, context.tax_rate2
        )
        
        # Calculate split ratios
        split1, split2 = self.calculate_split_ratios(
            context.split_mode, float(net1), float(net2), context.split1
        )
        
        result = {
            "net_revenues": {
                "member1": float(net1),
                "member2": float(net2),
                "total": float(net1 + net2)
            },
            "split_ratios": {
                "member1": float(split1),
                "member2": float(split2)
            },
            "gross_revenues": {
                "member1": context.rev1,
                "member2": context.rev2,
                "total": context.rev1 + context.rev2
            },
            "tax_rates": {
                "member1": context.tax_rate1,
                "member2": context.tax_rate2
            }
        }
        
        # Cache for 30 minutes (config rarely changes)
        await redis_cache.setex(cache_key, 1800, json.dumps(result))
        
        self._end_timer("base_calculations", start_time)
        return result
    
    def calculate_provision_amount_optimized(self, provision: CustomProvision, base_calculations: Dict[str, Any]) -> Decimal:
        """
        Calculate provision amount with optimized algorithm
        
        Args:
            provision: Provision configuration
            base_calculations: Pre-calculated base values
            
        Returns:
            Monthly provision amount as Decimal
        """
        net_revenues = base_calculations["net_revenues"]
        
        if provision.base_calculation == "fixed":
            return Decimal(str(provision.fixed_amount or 0))
        elif provision.base_calculation == "member1":
            base_amount = Decimal(str(net_revenues["member1"]))
        elif provision.base_calculation == "member2":
            base_amount = Decimal(str(net_revenues["member2"]))
        else:  # "total"
            base_amount = Decimal(str(net_revenues["total"]))
        
        percentage = Decimal(str(provision.percentage or 0)) / Decimal('100')
        return (base_amount * percentage).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calculate_provision_split(self, provision: CustomProvision, monthly_amount: Decimal, split_ratios: Dict[str, float]) -> Tuple[Decimal, Decimal]:
        """
        Calculate provision split between members
        
        Args:
            provision: Provision configuration
            monthly_amount: Total monthly provision amount
            split_ratios: Base split ratios from configuration
            
        Returns:
            Tuple of (member1_amount, member2_amount)
        """
        if provision.split_mode == "50/50":
            member1_amount = monthly_amount * Decimal('0.5')
            member2_amount = monthly_amount * Decimal('0.5')
        elif provision.split_mode == "100/0":
            member1_amount = monthly_amount
            member2_amount = Decimal('0')
        elif provision.split_mode == "0/100":
            member1_amount = Decimal('0')
            member2_amount = monthly_amount
        elif provision.split_mode == "custom":
            split1 = Decimal(str(provision.split_member1 or 50)) / Decimal('100')
            split2 = Decimal(str(provision.split_member2 or 50)) / Decimal('100')
            member1_amount = monthly_amount * split1
            member2_amount = monthly_amount * split2
        else:  # "key" - use revenue-based split
            split1 = Decimal(str(split_ratios["member1"]))
            split2 = Decimal(str(split_ratios["member2"]))
            member1_amount = monthly_amount * split1
            member2_amount = monthly_amount * split2
        
        return (
            member1_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            member2_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        )
    
    def calculate_provision_progress(self, provision: CustomProvision) -> float:
        """Calculate provision progress percentage"""
        if not provision.target_amount or provision.target_amount <= 0:
            return 0.0
        
        current = provision.current_amount or 0
        progress = min(100.0, (current / provision.target_amount) * 100)
        return round(progress, 1)
    
    async def calculate_all_provisions_optimized(self, db: Session, context: CalculationContext) -> Dict[str, Any]:
        """
        Calculate all provisions with single-pass algorithm and caching
        
        This is the main high-performance provision calculation method.
        """
        cache_key = f"all_provisions:{context.cache_key}"
        
        # Try cache first
        cached_result = await redis_cache.get(cache_key)
        if cached_result:
            result = json.loads(cached_result)
            result["cache_hit"] = True
            return result
        
        start_time = self._start_timer()
        
        # Get base calculations (cached)
        base_calculations = await self.get_base_calculations(context)
        
        # Get active provisions with optimized query
        provisions = db.query(CustomProvision).filter(
            CustomProvision.is_active == True
        ).order_by(CustomProvision.display_order, CustomProvision.name).all()
        
        # Calculate all provisions in single pass
        provision_results = []
        totals = {
            "total_monthly_amount": Decimal('0'),
            "total_member1": Decimal('0'),
            "total_member2": Decimal('0')
        }
        
        for provision in provisions:
            # Calculate monthly amount
            monthly_amount = self.calculate_provision_amount_optimized(provision, base_calculations)
            
            # Calculate member splits
            member1_amount, member2_amount = self.calculate_provision_split(
                provision, monthly_amount, base_calculations["split_ratios"]
            )
            
            # Calculate progress
            progress_percentage = self.calculate_provision_progress(provision)
            
            provision_result = {
                "id": provision.id,
                "name": provision.name,
                "description": provision.description,
                "icon": provision.icon,
                "color": provision.color,
                "category": provision.category,
                "monthly_amount": float(monthly_amount),
                "member1_amount": float(member1_amount),
                "member2_amount": float(member2_amount),
                "progress_percentage": progress_percentage,
                "target_amount": provision.target_amount,
                "current_amount": provision.current_amount,
                "is_temporary": provision.is_temporary,
                "display_order": provision.display_order
            }
            
            provision_results.append(provision_result)
            
            # Update totals
            totals["total_monthly_amount"] += monthly_amount
            totals["total_member1"] += member1_amount
            totals["total_member2"] += member2_amount
        
        # Convert totals to float
        totals_float = {
            "total_monthly_amount": float(totals["total_monthly_amount"]),
            "total_member1": float(totals["total_member1"]),
            "total_member2": float(totals["total_member2"])
        }
        
        calculation_time = (time.perf_counter() - start_time) * 1000
        
        result = {
            "provisions": provision_results,
            "totals": totals_float,
            "base_calculations": base_calculations,
            "metadata": {
                "calculation_time_ms": round(calculation_time, 2),
                "active_provisions_count": len(provision_results),
                "cache_hit": False,
                "timestamp": time.time()
            }
        }
        
        # Cache for 15 minutes
        await redis_cache.setex(cache_key, 900, json.dumps(result))
        
        self._end_timer("all_provisions_calculation", start_time)
        return result
    
    async def calculate_fixed_expenses_optimized(self, db: Session, context: CalculationContext) -> Dict[str, Any]:
        """
        Calculate fixed expenses with optimized algorithm
        """
        cache_key = f"fixed_expenses:{context.cache_key}"
        
        # Try cache first
        cached_result = await redis_cache.get(cache_key)
        if cached_result:
            result = json.loads(cached_result)
            result["cache_hit"] = True
            return result
        
        start_time = self._start_timer()
        
        # Get base calculations
        base_calculations = await self.get_base_calculations(context)
        split_ratios = base_calculations["split_ratios"]
        
        # Get active fixed lines
        fixed_lines = db.query(FixedLine).filter(FixedLine.active == True).all()
        
        fixed_results = []
        totals = {
            "total_monthly_amount": Decimal('0'),
            "total_member1": Decimal('0'), 
            "total_member2": Decimal('0')
        }
        
        for line in fixed_lines:
            # Convert to monthly amount
            amount = Decimal(str(line.amount))
            if line.freq == "trimestrielle":
                monthly_amount = amount / Decimal('3')
            elif line.freq == "annuelle":
                monthly_amount = amount / Decimal('12')
            else:  # mensuelle
                monthly_amount = amount
            
            # Calculate splits
            if line.split_mode == "50/50":
                member1_amount = monthly_amount * Decimal('0.5')
                member2_amount = monthly_amount * Decimal('0.5')
            elif line.split_mode == "m1":
                member1_amount = monthly_amount
                member2_amount = Decimal('0')
            elif line.split_mode == "m2":
                member1_amount = Decimal('0')
                member2_amount = monthly_amount
            elif line.split_mode == "manuel":
                split1 = Decimal(str(line.split1)) / Decimal('100')
                split2 = Decimal(str(line.split2)) / Decimal('100')
                member1_amount = monthly_amount * split1
                member2_amount = monthly_amount * split2
            else:  # "clé" - use config split ratios
                split1 = Decimal(str(split_ratios["member1"]))
                split2 = Decimal(str(split_ratios["member2"]))
                member1_amount = monthly_amount * split1
                member2_amount = monthly_amount * split2
            
            fixed_result = {
                "id": line.id,
                "label": line.label,
                "category": line.category,
                "frequency": line.freq,
                "original_amount": float(amount),
                "monthly_amount": float(monthly_amount),
                "member1_amount": float(member1_amount),
                "member2_amount": float(member2_amount),
                "split_mode": line.split_mode
            }
            
            fixed_results.append(fixed_result)
            
            # Update totals
            totals["total_monthly_amount"] += monthly_amount
            totals["total_member1"] += member1_amount
            totals["total_member2"] += member2_amount
        
        # Convert totals to float
        totals_float = {
            "total_monthly_amount": float(totals["total_monthly_amount"]),
            "total_member1": float(totals["total_member1"]),
            "total_member2": float(totals["total_member2"])
        }
        
        calculation_time = (time.perf_counter() - start_time) * 1000
        
        result = {
            "fixed_expenses": fixed_results,
            "totals": totals_float,
            "metadata": {
                "calculation_time_ms": round(calculation_time, 2),
                "active_fixed_count": len(fixed_results),
                "cache_hit": False,
                "timestamp": time.time()
            }
        }
        
        # Cache for 15 minutes
        await redis_cache.setex(cache_key, 900, json.dumps(result))
        
        self._end_timer("fixed_expenses_calculation", start_time)
        return result
    
    async def calculate_monthly_aggregates_optimized(self, db: Session, month: str) -> Dict[str, Any]:
        """
        Calculate monthly transaction aggregates with single optimized query
        """
        cache_key = f"monthly_aggregates:{month}"
        
        # Try cache first
        cached_result = await redis_cache.get(cache_key)
        if cached_result:
            result = json.loads(cached_result)
            result["cache_hit"] = True
            return result
        
        start_time = self._start_timer()
        
        # Single optimized query for all aggregates
        query = text("""
            SELECT 
                -- Total aggregates
                COUNT(CASE WHEN exclude = 0 THEN 1 END) as total_transactions,
                COALESCE(SUM(CASE WHEN exclude = 0 THEN amount ELSE 0 END), 0) as total_amount,
                
                -- By expense type
                COALESCE(SUM(CASE WHEN expense_type = 'VARIABLE' AND exclude = 0 THEN amount ELSE 0 END), 0) as variable_total,
                COUNT(CASE WHEN expense_type = 'VARIABLE' AND exclude = 0 THEN 1 END) as variable_count,
                
                COALESCE(SUM(CASE WHEN expense_type = 'FIXED' AND exclude = 0 THEN amount ELSE 0 END), 0) as fixed_total,
                COUNT(CASE WHEN expense_type = 'FIXED' AND exclude = 0 THEN 1 END) as fixed_count,
                
                COALESCE(SUM(CASE WHEN expense_type = 'PROVISION' AND exclude = 0 THEN amount ELSE 0 END), 0) as provision_total,
                COUNT(CASE WHEN expense_type = 'PROVISION' AND exclude = 0 THEN 1 END) as provision_count,
                
                -- Category aggregates (top 10)
                GROUP_CONCAT(
                    DISTINCT category || ':' || 
                    COALESCE(SUM(CASE WHEN exclude = 0 THEN amount ELSE 0 END), 0)
                    ORDER BY SUM(CASE WHEN exclude = 0 THEN amount ELSE 0 END) DESC
                    LIMIT 10
                ) as top_categories,
                
                -- Date range
                MIN(date_op) as first_date,
                MAX(date_op) as last_date,
                
                -- Tagged vs untagged
                COUNT(CASE WHEN tags != '' AND exclude = 0 THEN 1 END) as tagged_count,
                COUNT(CASE WHEN (tags = '' OR tags IS NULL) AND exclude = 0 THEN 1 END) as untagged_count
                
            FROM transactions 
            WHERE month = :month
        """)
        
        result = db.execute(query, {"month": month}).first()
        
        # Parse category breakdown
        categories = {}
        if result.top_categories:
            for item in result.top_categories.split(','):
                if ':' in item:
                    cat, amount = item.split(':', 1)
                    categories[cat] = float(amount)
        
        aggregates = {
            "month": month,
            "totals": {
                "total_transactions": int(result.total_transactions or 0),
                "total_amount": float(result.total_amount or 0),
                "variable_total": float(result.variable_total or 0),
                "variable_count": int(result.variable_count or 0),
                "fixed_total": float(result.fixed_total or 0),
                "fixed_count": int(result.fixed_count or 0),
                "provision_total": float(result.provision_total or 0),
                "provision_count": int(result.provision_count or 0)
            },
            "categories": categories,
            "date_range": {
                "first": result.first_date.isoformat() if result.first_date else None,
                "last": result.last_date.isoformat() if result.last_date else None
            },
            "tagging_stats": {
                "tagged_count": int(result.tagged_count or 0),
                "untagged_count": int(result.untagged_count or 0),
                "tagging_rate": round((int(result.tagged_count or 0) / max(1, int(result.total_transactions or 1))) * 100, 1)
            },
            "metadata": {
                "calculation_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                "cache_hit": False,
                "timestamp": time.time()
            }
        }
        
        # Cache for 10 minutes
        await redis_cache.setex(cache_key, 600, json.dumps(aggregates))
        
        self._end_timer("monthly_aggregates", start_time)
        return aggregates
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get calculation performance metrics"""
        return {
            "metrics": self.performance_metrics,
            "cache_info": {
                "net_revenues_cache": self.calculate_net_revenues.cache_info()._asdict(),
                "split_ratios_cache": self.calculate_split_ratios.cache_info()._asdict()
            }
        }
    
    def clear_caches(self):
        """Clear all calculation caches"""
        self.calculation_cache.clear()
        self.calculate_net_revenues.cache_clear()
        self.calculate_split_ratios.cache_clear()
        logger.info("All calculation caches cleared")

# Global instance
optimized_calculator = OptimizedCalculationEngine()

# Convenience functions for easy import

async def calculate_provisions_fast(db: Session, config: Config) -> Dict[str, Any]:
    """Fast provision calculation with optimized engine"""
    context = CalculationContext(
        rev1=config.rev1,
        rev2=config.rev2,
        tax_rate1=config.tax_rate1 or 0,
        tax_rate2=config.tax_rate2 or 0,
        split_mode=config.split_mode,
        split1=config.split1,
        split2=config.split2
    )
    return await optimized_calculator.calculate_all_provisions_optimized(db, context)

async def calculate_fixed_expenses_fast(db: Session, config: Config) -> Dict[str, Any]:
    """Fast fixed expense calculation with optimized engine"""
    context = CalculationContext(
        rev1=config.rev1,
        rev2=config.rev2,
        tax_rate1=config.tax_rate1 or 0,
        tax_rate2=config.tax_rate2 or 0,
        split_mode=config.split_mode,
        split1=config.split1,
        split2=config.split2
    )
    return await optimized_calculator.calculate_fixed_expenses_optimized(db, context)

async def calculate_monthly_summary_fast(db: Session, month: str) -> Dict[str, Any]:
    """Fast monthly summary calculation"""
    return await optimized_calculator.calculate_monthly_aggregates_optimized(db, month)