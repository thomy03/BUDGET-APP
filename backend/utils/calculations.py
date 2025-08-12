"""
Centralized calculation utilities for Budget Famille v2.3
Eliminates duplicate calculation patterns across the application
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SplitMode(Enum):
    """Split mode enumeration"""
    REVENUS = "revenus"
    MANUEL = "manuel"
    FIFTY_FIFTY = "50/50"
    CLE = "clé"
    MEMBER1_ONLY = "100/0"
    MEMBER2_ONLY = "0/100"

class FrequencyType(Enum):
    """Frequency type enumeration"""
    MONTHLY = "mensuelle"
    QUARTERLY = "trimestrielle"
    ANNUAL = "annuelle"

@dataclass
class MemberConfig:
    """Configuration for budget members"""
    name: str
    revenue: float
    split_percentage: float = 50.0

@dataclass
class SplitResult:
    """Result of a split calculation"""
    member1_amount: float
    member2_amount: float
    total_amount: float
    split_percentage1: float
    split_percentage2: float

@dataclass
class BudgetSummary:
    """Complete budget summary"""
    month: str
    total_income: float
    total_expenses: float
    variable_total: float
    fixed_total: float
    provisions_total: float
    member1_share: float
    member2_share: float
    member1_balance: float
    member2_balance: float
    remaining_budget: float
    details: Dict[str, Any]

def round_currency(amount: float, decimals: int = 2) -> float:
    """
    Round amount to specified decimal places using proper rounding
    
    Args:
        amount: Amount to round
        decimals: Number of decimal places
        
    Returns:
        Rounded amount
    """
    if amount is None:
        return 0.0
    
    decimal_amount = Decimal(str(amount))
    rounded = decimal_amount.quantize(
        Decimal('0.01' if decimals == 2 else f'0.{"0" * decimals}'),
        rounding=ROUND_HALF_UP
    )
    return float(rounded)

def calculate_percentage_split(
    total_amount: float,
    percentage1: float,
    percentage2: Optional[float] = None
) -> SplitResult:
    """
    Calculate split based on percentages
    
    Args:
        total_amount: Total amount to split
        percentage1: Percentage for member 1 (0-100)
        percentage2: Percentage for member 2 (auto-calculated if not provided)
        
    Returns:
        SplitResult with calculated amounts
    """
    if percentage2 is None:
        percentage2 = 100.0 - percentage1
    
    # Validate percentages
    if abs((percentage1 + percentage2) - 100.0) > 0.01:
        logger.warning(f"Percentages don't add to 100%: {percentage1} + {percentage2}")
        # Normalize percentages
        total_pct = percentage1 + percentage2
        percentage1 = (percentage1 / total_pct) * 100.0
        percentage2 = (percentage2 / total_pct) * 100.0
    
    member1_amount = round_currency(total_amount * percentage1 / 100.0)
    member2_amount = round_currency(total_amount * percentage2 / 100.0)
    
    # Adjust for rounding differences
    calculated_total = member1_amount + member2_amount
    if abs(calculated_total - total_amount) > 0.01:
        difference = total_amount - calculated_total
        # Add difference to the larger share
        if member1_amount >= member2_amount:
            member1_amount += difference
        else:
            member2_amount += difference
    
    return SplitResult(
        member1_amount=round_currency(member1_amount),
        member2_amount=round_currency(member2_amount),
        total_amount=total_amount,
        split_percentage1=percentage1,
        split_percentage2=percentage2
    )

def calculate_revenue_based_split(
    total_amount: float,
    revenue1: float,
    revenue2: float
) -> SplitResult:
    """
    Calculate split based on revenue proportions
    
    Args:
        total_amount: Total amount to split
        revenue1: Revenue for member 1
        revenue2: Revenue for member 2
        
    Returns:
        SplitResult with calculated amounts
    """
    total_revenue = revenue1 + revenue2
    
    if total_revenue == 0:
        # Equal split if no revenues
        return calculate_percentage_split(total_amount, 50.0, 50.0)
    
    percentage1 = (revenue1 / total_revenue) * 100.0
    percentage2 = (revenue2 / total_revenue) * 100.0
    
    return calculate_percentage_split(total_amount, percentage1, percentage2)

def calculate_split_amounts(
    total_amount: float,
    split_mode: str,
    revenue1: float = 0.0,
    revenue2: float = 0.0,
    manual_split1: Optional[float] = None,
    manual_split2: Optional[float] = None
) -> SplitResult:
    """
    Calculate split amounts based on split mode
    
    Args:
        total_amount: Total amount to split
        split_mode: Split mode (revenus, manuel, 50/50, etc.)
        revenue1: Revenue for member 1 (for revenue-based split)
        revenue2: Revenue for member 2 (for revenue-based split)
        manual_split1: Manual split percentage for member 1
        manual_split2: Manual split percentage for member 2
        
    Returns:
        SplitResult with calculated amounts
    """
    try:
        mode = SplitMode(split_mode)
    except ValueError:
        logger.warning(f"Unknown split mode: {split_mode}, defaulting to 50/50")
        mode = SplitMode.FIFTY_FIFTY
    
    if mode == SplitMode.REVENUS or mode == SplitMode.CLE:
        return calculate_revenue_based_split(total_amount, revenue1, revenue2)
    
    elif mode == SplitMode.MANUEL:
        if manual_split1 is None or manual_split2 is None:
            logger.warning("Manual split mode requires split percentages, defaulting to 50/50")
            return calculate_percentage_split(total_amount, 50.0, 50.0)
        return calculate_percentage_split(total_amount, manual_split1, manual_split2)
    
    elif mode == SplitMode.FIFTY_FIFTY:
        return calculate_percentage_split(total_amount, 50.0, 50.0)
    
    elif mode == SplitMode.MEMBER1_ONLY:
        return calculate_percentage_split(total_amount, 100.0, 0.0)
    
    elif mode == SplitMode.MEMBER2_ONLY:
        return calculate_percentage_split(total_amount, 0.0, 100.0)
    
    else:
        logger.warning(f"Unhandled split mode: {mode}, defaulting to 50/50")
        return calculate_percentage_split(total_amount, 50.0, 50.0)

def calculate_monthly_amount(
    annual_amount: float,
    frequency: str
) -> float:
    """
    Convert amount to monthly equivalent based on frequency
    
    Args:
        annual_amount: Annual amount
        frequency: Frequency type (mensuelle, trimestrielle, annuelle)
        
    Returns:
        Monthly amount
    """
    try:
        freq = FrequencyType(frequency)
    except ValueError:
        logger.warning(f"Unknown frequency: {frequency}, defaulting to annual")
        freq = FrequencyType.ANNUAL
    
    if freq == FrequencyType.MONTHLY:
        return annual_amount
    elif freq == FrequencyType.QUARTERLY:
        return round_currency(annual_amount / 3.0)
    elif freq == FrequencyType.ANNUAL:
        return round_currency(annual_amount / 12.0)
    
    return annual_amount

def calculate_annual_amount(
    amount: float,
    frequency: str
) -> float:
    """
    Convert amount to annual equivalent based on frequency
    
    Args:
        amount: Amount in the given frequency
        frequency: Frequency type (mensuelle, trimestrielle, annuelle)
        
    Returns:
        Annual amount
    """
    try:
        freq = FrequencyType(frequency)
    except ValueError:
        logger.warning(f"Unknown frequency: {frequency}, defaulting to annual")
        freq = FrequencyType.ANNUAL
    
    if freq == FrequencyType.MONTHLY:
        return round_currency(amount * 12.0)
    elif freq == FrequencyType.QUARTERLY:
        return round_currency(amount * 4.0)
    elif freq == FrequencyType.ANNUAL:
        return amount
    
    return amount

def calculate_fixed_expenses(
    fixed_lines: List[Dict[str, Any]],
    revenue1: float = 0.0,
    revenue2: float = 0.0
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate total fixed expenses and split details
    
    Args:
        fixed_lines: List of fixed expense configurations
        revenue1: Revenue for member 1
        revenue2: Revenue for member 2
        
    Returns:
        Tuple of (total_monthly, details_dict)
    """
    total_monthly = 0.0
    total_member1 = 0.0
    total_member2 = 0.0
    details = {
        "lines": [],
        "total_monthly": 0.0,
        "member1_total": 0.0,
        "member2_total": 0.0
    }
    
    for line in fixed_lines:
        if not line.get("active", True):
            continue
        
        # Convert to monthly amount
        monthly_amount = calculate_monthly_amount(
            line.get("amount", 0.0),
            line.get("freq", "mensuelle")
        )
        
        # Calculate split
        split_result = calculate_split_amounts(
            monthly_amount,
            line.get("split_mode", "50/50"),
            revenue1,
            revenue2,
            line.get("split1"),
            line.get("split2")
        )
        
        line_details = {
            "id": line.get("id"),
            "label": line.get("label", ""),
            "amount": line.get("amount", 0.0),
            "frequency": line.get("freq", "mensuelle"),
            "monthly_amount": monthly_amount,
            "member1_amount": split_result.member1_amount,
            "member2_amount": split_result.member2_amount,
            "split_mode": line.get("split_mode", "50/50")
        }
        
        details["lines"].append(line_details)
        total_monthly += monthly_amount
        total_member1 += split_result.member1_amount
        total_member2 += split_result.member2_amount
    
    details.update({
        "total_monthly": round_currency(total_monthly),
        "member1_total": round_currency(total_member1),
        "member2_total": round_currency(total_member2)
    })
    
    return round_currency(total_monthly), details

def calculate_provision_amounts(
    provisions: List[Dict[str, Any]],
    total_income: float,
    member1_income: float,
    member2_income: float
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate provision amounts based on configuration
    
    Args:
        provisions: List of provision configurations
        total_income: Total household income
        member1_income: Member 1 income
        member2_income: Member 2 income
        
    Returns:
        Tuple of (total_provisions, details_dict)
    """
    total_provisions = 0.0
    total_member1 = 0.0
    total_member2 = 0.0
    details = {
        "provisions": [],
        "total_monthly": 0.0,
        "member1_total": 0.0,
        "member2_total": 0.0
    }
    
    for provision in provisions:
        if not provision.get("is_active", True):
            continue
        
        # Calculate base amount
        base_calc = provision.get("base_calculation", "total")
        percentage = provision.get("percentage", 0.0)
        
        if base_calc == "total":
            base_amount = total_income * percentage / 100.0
        elif base_calc == "member1":
            base_amount = member1_income * percentage / 100.0
        elif base_calc == "member2":
            base_amount = member2_income * percentage / 100.0
        elif base_calc == "fixed":
            base_amount = provision.get("fixed_amount", 0.0)
        else:
            base_amount = total_income * percentage / 100.0
        
        # Calculate split
        split_mode = provision.get("split_mode", "key")
        if split_mode == "key" or split_mode == "revenus":
            split_result = calculate_revenue_based_split(
                base_amount, member1_income, member2_income
            )
        elif split_mode == "50/50":
            split_result = calculate_percentage_split(base_amount, 50.0, 50.0)
        elif split_mode == "100/0":
            split_result = calculate_percentage_split(base_amount, 100.0, 0.0)
        elif split_mode == "0/100":
            split_result = calculate_percentage_split(base_amount, 0.0, 100.0)
        elif split_mode == "custom":
            split_result = calculate_percentage_split(
                base_amount,
                provision.get("split_member1", 50.0),
                provision.get("split_member2", 50.0)
            )
        else:
            split_result = calculate_percentage_split(base_amount, 50.0, 50.0)
        
        provision_details = {
            "id": provision.get("id"),
            "name": provision.get("name", ""),
            "percentage": percentage,
            "base_calculation": base_calc,
            "base_amount": round_currency(base_amount),
            "member1_amount": split_result.member1_amount,
            "member2_amount": split_result.member2_amount,
            "split_mode": split_mode
        }
        
        details["provisions"].append(provision_details)
        total_provisions += base_amount
        total_member1 += split_result.member1_amount
        total_member2 += split_result.member2_amount
    
    details.update({
        "total_monthly": round_currency(total_provisions),
        "member1_total": round_currency(total_member1),
        "member2_total": round_currency(total_member2)
    })
    
    return round_currency(total_provisions), details

def calculate_variable_expenses(
    transactions: List[Dict[str, Any]],
    exclude_categories: List[str] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate variable expenses from transactions
    
    Args:
        transactions: List of transaction data
        exclude_categories: Categories to exclude from calculation
        
    Returns:
        Tuple of (total_variable, details_dict)
    """
    if exclude_categories is None:
        exclude_categories = []
    
    total_variable = 0.0
    category_totals = {}
    
    for tx in transactions:
        if tx.get("exclude", False):
            continue
        
        if not tx.get("is_expense", False):
            continue
        
        category = tx.get("category", "autres")
        if category in exclude_categories:
            continue
        
        amount = abs(tx.get("amount", 0.0))  # Ensure positive
        total_variable += amount
        
        if category not in category_totals:
            category_totals[category] = 0.0
        category_totals[category] += amount
    
    details = {
        "total_variable": round_currency(total_variable),
        "categories": {k: round_currency(v) for k, v in category_totals.items()},
        "transaction_count": len([tx for tx in transactions if tx.get("is_expense") and not tx.get("exclude")])
    }
    
    return round_currency(total_variable), details

def calculate_budget_summary(
    config: Dict[str, Any],
    transactions: List[Dict[str, Any]],
    fixed_lines: List[Dict[str, Any]],
    provisions: List[Dict[str, Any]],
    month: str
) -> BudgetSummary:
    """
    Calculate complete budget summary for a month
    
    Args:
        config: Budget configuration
        transactions: List of transactions for the month
        fixed_lines: List of fixed expense lines
        provisions: List of provision configurations
        month: Month in YYYY-MM format
        
    Returns:
        BudgetSummary object
    """
    # Get member configuration
    member1_revenue = config.get("rev1", 0.0)
    member2_revenue = config.get("rev2", 0.0)
    total_income = member1_revenue + member2_revenue
    
    # Calculate variable expenses
    variable_total, variable_details = calculate_variable_expenses(transactions)
    
    # Calculate fixed expenses
    fixed_total, fixed_details = calculate_fixed_expenses(
        fixed_lines, member1_revenue, member2_revenue
    )
    
    # Calculate provisions
    provisions_total, provisions_details = calculate_provision_amounts(
        provisions, total_income, member1_revenue, member2_revenue
    )
    
    # Calculate total expenses
    total_expenses = variable_total + fixed_total + provisions_total
    
    # Calculate member shares for variable expenses
    variable_split = calculate_split_amounts(
        variable_total,
        config.get("split_mode", "50/50"),
        member1_revenue,
        member2_revenue,
        config.get("split1"),
        config.get("split2")
    )
    
    # Calculate total member shares
    member1_share = (
        variable_split.member1_amount +
        fixed_details["member1_total"] +
        provisions_details["member1_total"]
    )
    
    member2_share = (
        variable_split.member2_amount +
        fixed_details["member2_total"] +
        provisions_details["member2_total"]
    )
    
    # Calculate balances
    member1_balance = member1_revenue - member1_share
    member2_balance = member2_revenue - member2_share
    remaining_budget = total_income - total_expenses
    
    # Compile details
    details = {
        "income": {
            "member1": member1_revenue,
            "member2": member2_revenue,
            "total": total_income
        },
        "expenses": {
            "variable": variable_details,
            "fixed": fixed_details,
            "provisions": provisions_details,
            "total": round_currency(total_expenses)
        },
        "splits": {
            "variable": {
                "member1": variable_split.member1_amount,
                "member2": variable_split.member2_amount,
                "mode": config.get("split_mode", "50/50")
            }
        }
    }
    
    return BudgetSummary(
        month=month,
        total_income=round_currency(total_income),
        total_expenses=round_currency(total_expenses),
        variable_total=round_currency(variable_total),
        fixed_total=round_currency(fixed_total),
        provisions_total=round_currency(provisions_total),
        member1_share=round_currency(member1_share),
        member2_share=round_currency(member2_share),
        member1_balance=round_currency(member1_balance),
        member2_balance=round_currency(member2_balance),
        remaining_budget=round_currency(remaining_budget),
        details=details
    )

def calculate_monthly_totals(
    transactions: List[Dict[str, Any]],
    group_by: str = "category"
) -> Dict[str, float]:
    """
    Calculate monthly totals grouped by specified field
    
    Args:
        transactions: List of transactions
        group_by: Field to group by (category, account_label, etc.)
        
    Returns:
        Dictionary of totals by group
    """
    totals = {}
    
    for tx in transactions:
        if tx.get("exclude", False):
            continue
        
        group_key = tx.get(group_by, "autres")
        amount = tx.get("amount", 0.0)
        
        if group_key not in totals:
            totals[group_key] = 0.0
        
        totals[group_key] += amount
    
    # Round all totals
    return {k: round_currency(v) for k, v in totals.items()}

def calculate_budget_variance(
    actual_expenses: float,
    budgeted_expenses: float
) -> Dict[str, Any]:
    """
    Calculate budget variance analysis
    
    Args:
        actual_expenses: Actual expenses amount
        budgeted_expenses: Budgeted expenses amount
        
    Returns:
        Variance analysis dictionary
    """
    variance = actual_expenses - budgeted_expenses
    variance_percentage = (variance / budgeted_expenses * 100.0) if budgeted_expenses != 0 else 0.0
    
    return {
        "actual": round_currency(actual_expenses),
        "budgeted": round_currency(budgeted_expenses),
        "variance": round_currency(variance),
        "variance_percentage": round_currency(variance_percentage, 1),
        "status": "over" if variance > 0 else "under" if variance < 0 else "on_target"
    }