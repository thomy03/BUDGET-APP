"""
Analytics router for Budget Famille v2.3
Handles analytics and reporting endpoints
"""
import logging
import datetime as dt
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from dependencies.database import get_db
from audit_logger import get_audit_logger

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    responses={404: {"description": "Not found"}}
)

# Import models, schemas and functions
from models.database import Transaction, CategoryBudget
from models.schemas import (
    KPISummary, MonthlyTrend, CategoryBreakdown, AnomalyDetection,
    SpendingPattern, VarianceAnalysisResponse, GlobalVariance, CategoryVariance, VarianceAlert
)
from services.calculations import (
    calculate_kpi_summary, calculate_monthly_trends, calculate_category_breakdown,
    detect_anomalies, calculate_spending_patterns
)
from dateutil.relativedelta import relativedelta

@router.get("/kpis", response_model=KPISummary)
def get_kpi_summary(
    months: str = "last3",  # "last3", "last6", "last12", "2024-01,2024-02" 
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get KPI summary for specified period
    
    Returns key performance indicators for the specified time period.
    Supports 'last3', 'last6', 'last12' or comma-separated months.
    """
    audit_logger = get_audit_logger()
    logger.info(f"Analytics KPIs demandés par utilisateur: {current_user.username}")
    
    # Déterminer les mois à analyser
    if months.startswith("last"):
        n_months = int(months.replace("last", ""))
        today = dt.date.today()
        months_list = []
        for i in range(n_months):
            month_date = today.replace(day=1) - dt.timedelta(days=i*30)
            months_list.append(month_date.strftime("%Y-%m"))
        months_list = list(set(months_list))  # Remove duplicates
    else:
        months_list = [m.strip() for m in months.split(",")]
    
    logger.info(f"Mois analysés: {months_list}")
    
    try:
        kpis = calculate_kpi_summary(db, months_list)
        audit_logger.log_event(
            "ANALYTICS_ACCESS",
            username=current_user.username,
            details={"type": "kpis", "months": len(months_list)},
            success=True
        )
        return kpis
    except Exception as e:
        logger.error(f"Erreur calcul KPIs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur calcul KPIs: {str(e)}")

@router.get("/trends", response_model=List[MonthlyTrend])
def get_monthly_trends(
    months: str = "last6",
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get monthly trend analysis
    
    Returns trend analysis showing evolution of spending patterns over time.
    """
    logger.info(f"Analytics trends demandés par utilisateur: {current_user.username}")
    
    # Parse months parameter
    if months.startswith("last"):
        n_months = int(months.replace("last", ""))
        today = dt.date.today()
        months_list = []
        for i in range(n_months):
            month_date = today.replace(day=1) - dt.timedelta(days=i*30)
            months_list.append(month_date.strftime("%Y-%m"))
        months_list = list(set(months_list))
    else:
        months_list = [m.strip() for m in months.split(",")]
    
    try:
        trends = calculate_monthly_trends(db, months_list)
        return trends
    except Exception as e:
        logger.error(f"Erreur calcul trends: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur calcul trends: {str(e)}")

@router.get("/categories", response_model=List[CategoryBreakdown])
def get_category_breakdown(
    month: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get category breakdown for a specific month
    
    Returns detailed breakdown of expenses by category for the specified month.
    """
    logger.info(f"Analytics catégories pour {month} par utilisateur: {current_user.username}")
    
    try:
        breakdown = calculate_category_breakdown(db, month)
        return breakdown
    except Exception as e:
        logger.error(f"Erreur breakdown catégories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur breakdown catégories: {str(e)}")

@router.get("/anomalies", response_model=List[AnomalyDetection])
def get_anomalies(
    month: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get anomaly detection for a specific month
    
    Returns transactions that are flagged as potential anomalies based on
    historical spending patterns.
    """
    logger.info(f"Analytics anomalies pour {month} par utilisateur: {current_user.username}")
    
    try:
        anomalies = detect_anomalies(db, month)
        return anomalies
    except Exception as e:
        logger.error(f"Erreur détection anomalies: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur détection anomalies: {str(e)}")

@router.get("/patterns", response_model=List[SpendingPattern])
def get_spending_patterns(
    months: str = "last3",
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get spending patterns by day of week
    
    Returns analysis of spending patterns by day of the week across
    the specified time period.
    """
    logger.info(f"Analytics patterns pour {months} par utilisateur: {current_user.username}")
    
    # Parse months parameter
    if months.startswith("last"):
        n_months = int(months.replace("last", ""))
        today = dt.date.today()
        months_list = []
        for i in range(n_months):
            month_date = today.replace(day=1) - dt.timedelta(days=i*30)
            months_list.append(month_date.strftime("%Y-%m"))
        months_list = list(set(months_list))
    else:
        months_list = [m.strip() for m in months.split(",")]
    
    try:
        patterns = calculate_spending_patterns(db, months_list)
        return patterns
    except Exception as e:
        logger.error(f"Erreur calcul patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur calcul patterns: {str(e)}")

@router.get("/available-months")
def get_available_months(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of available months for analysis
    
    Returns a list of all months that have transaction data available.
    """
    from sqlalchemy import distinct
    
    try:
        months = db.query(distinct(Transaction.month)).filter(
            Transaction.month.isnot(None)
        ).order_by(Transaction.month.desc()).all()
        
        month_list = [month[0] for month in months if month[0]]
        
        return {
            "available_months": month_list,
            "total_months": len(month_list),
            "latest_month": month_list[0] if month_list else None,
            "earliest_month": month_list[-1] if month_list else None
        }
    except Exception as e:
        logger.error(f"Erreur récupération mois disponibles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur récupération mois disponibles: {str(e)}")

@router.post("/export")
def export_analytics_legacy(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Legacy analytics export endpoint

    Maintains compatibility with the original analytics export functionality.
    """
    # This is a placeholder for the original analytics export functionality
    # that would be implemented based on the specific requirements
    return {
        "message": "Analytics export functionality - to be implemented",
        "user": current_user.username,
        "timestamp": dt.datetime.now().isoformat()
    }


@router.get("/variance", response_model=VarianceAnalysisResponse)
def get_variance_analysis(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="Month in YYYY-MM format"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get budget variance analysis for a specific month.

    Compares budgeted amounts vs actual spending for each category.
    Returns variance in euros and percentage, with status indicators.
    """
    logger.info(f"Variance analysis pour {month} demandee par: {current_user.username}")

    try:
        # Get budgets for this month (including defaults where month is NULL)
        budgets = db.query(CategoryBudget).filter(
            (CategoryBudget.month == month) | (CategoryBudget.month == None),
            CategoryBudget.is_active == True
        ).all()

        # Build budget map (month-specific takes precedence over default)
        budget_map = {}
        for b in budgets:
            if b.month == month:
                # Month-specific budget takes precedence
                budget_map[b.category.lower()] = b.budget_amount
            elif b.category.lower() not in budget_map:
                # Default budget only if no month-specific exists
                budget_map[b.category.lower()] = b.budget_amount

        # Get all expense transactions for the month
        transactions = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.amount < 0,
            Transaction.exclude == False
        ).all()

        # Group spending by tag/category
        spending_by_category = {}
        transactions_by_category = {}

        for tx in transactions:
            # Get tags, or use category if no tags
            tags = [t.strip().lower() for t in (tx.tags or "").split(",") if t.strip()]
            if not tags:
                tags = [tx.category.lower()] if tx.category else ["non-categorise"]

            for tag in tags:
                if tag not in spending_by_category:
                    spending_by_category[tag] = 0
                    transactions_by_category[tag] = []

                spending_by_category[tag] += abs(tx.amount)
                transactions_by_category[tag].append({
                    "id": tx.id,
                    "label": tx.label,
                    "amount": abs(tx.amount),
                    "date": tx.date_op.isoformat() if tx.date_op else None
                })

        # Get previous month for comparison
        month_date = dt.datetime.strptime(month, "%Y-%m")
        prev_month = (month_date - relativedelta(months=1)).strftime("%Y-%m")

        prev_transactions = db.query(Transaction).filter(
            Transaction.month == prev_month,
            Transaction.amount < 0,
            Transaction.exclude == False
        ).all()

        prev_spending_by_category = {}
        for tx in prev_transactions:
            tags = [t.strip().lower() for t in (tx.tags or "").split(",") if t.strip()]
            if not tags:
                tags = [tx.category.lower()] if tx.category else ["non-categorise"]
            for tag in tags:
                if tag not in prev_spending_by_category:
                    prev_spending_by_category[tag] = 0
                prev_spending_by_category[tag] += abs(tx.amount)

        # Build category variance list
        category_variances = []
        total_budgeted = 0
        total_actual = 0
        categories_over_budget = 0
        categories_on_track = 0
        alerts = []

        # Process all categories that have either a budget or spending
        all_categories = set(budget_map.keys()) | set(spending_by_category.keys())

        for category in all_categories:
            budgeted = budget_map.get(category, 0)
            actual = spending_by_category.get(category, 0)
            variance = actual - budgeted
            variance_pct = (variance / budgeted * 100) if budgeted > 0 else 0

            # Determine status
            if budgeted == 0:
                status = "no_budget"
            elif actual <= budgeted * 0.8:
                status = "under_budget"
                categories_on_track += 1
            elif actual <= budgeted:
                status = "on_track"
                categories_on_track += 1
            elif actual <= budgeted * 1.1:
                status = "warning"
            else:
                status = "over_budget"
                categories_over_budget += 1
                alerts.append(VarianceAlert(
                    type="budget_exceeded",
                    category=category,
                    message=f"Budget '{category}' depasse de {variance:.2f}EUR ({variance_pct:.1f}%)",
                    severity="critical" if variance_pct > 50 else "warning"
                ))

            # Get top 3 transactions
            cat_transactions = transactions_by_category.get(category, [])
            top_transactions = sorted(cat_transactions, key=lambda x: x["amount"], reverse=True)[:3]

            # Compare to last month
            prev_amount = prev_spending_by_category.get(category, 0)
            if prev_amount > 0:
                change_pct = (actual - prev_amount) / prev_amount * 100
                if change_pct > 0:
                    vs_last_month = f"+{change_pct:.0f}%"
                else:
                    vs_last_month = f"{change_pct:.0f}%"
            else:
                vs_last_month = None

            category_variances.append(CategoryVariance(
                category=category,
                budgeted=round(budgeted, 2),
                actual=round(actual, 2),
                variance=round(variance, 2),
                variance_pct=round(variance_pct, 2),
                status=status,
                top_transactions=top_transactions,
                vs_last_month=vs_last_month,
                transaction_count=len(cat_transactions)
            ))

            if budgeted > 0:
                total_budgeted += budgeted
            total_actual += actual

        # Sort by variance (most over budget first)
        category_variances.sort(key=lambda x: x.variance, reverse=True)

        # Calculate global variance
        global_variance_amount = total_actual - total_budgeted
        global_variance_pct = (global_variance_amount / total_budgeted * 100) if total_budgeted > 0 else 0

        if total_budgeted == 0:
            global_status = "no_budget"
        elif total_actual <= total_budgeted * 0.9:
            global_status = "under_budget"
        elif total_actual <= total_budgeted:
            global_status = "on_track"
        elif total_actual <= total_budgeted * 1.1:
            global_status = "warning"
        else:
            global_status = "over_budget"

        return VarianceAnalysisResponse(
            month=month,
            global_variance=GlobalVariance(
                budgeted=round(total_budgeted, 2),
                actual=round(total_actual, 2),
                variance=round(global_variance_amount, 2),
                variance_pct=round(global_variance_pct, 2),
                status=global_status
            ),
            by_category=category_variances,
            categories_over_budget=categories_over_budget,
            categories_on_track=categories_on_track,
            alerts=alerts
        )

    except Exception as e:
        logger.error(f"Erreur analyse variance: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur analyse variance: {str(e)}")