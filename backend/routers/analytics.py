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
from models.database import Transaction
from models.schemas import (
    KPISummary, MonthlyTrend, CategoryBreakdown, AnomalyDetection,
    SpendingPattern
)
from services.calculations import (
    calculate_kpi_summary, calculate_monthly_trends, calculate_category_breakdown,
    detect_anomalies, calculate_spending_patterns
)

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