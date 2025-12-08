"""
Predictions Router for Budget Famille v4.0
Exposes ML-powered budget predictions and anomaly detection
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import pandas as pd

from dependencies.auth import get_current_user
from dependencies.database import get_db
from models.database import Transaction, CategoryBudget

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/predictions",
    tags=["predictions"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "ML service error"}
    }
)


# Pydantic Schemas

class BudgetPredictionResponse(BaseModel):
    category: str
    current_spent: float
    predicted_month_end: float
    monthly_average: float
    trend_direction: str
    confidence: float
    recommendation: str


class BudgetAlertResponse(BaseModel):
    alert_type: str
    category: str
    severity: str
    message: str
    current_amount: float
    predicted_amount: float
    threshold: float
    days_remaining: int


class SmartRecommendationResponse(BaseModel):
    recommendation_type: str
    category: str
    current_budget: float
    suggested_budget: float
    reasoning: str
    impact_estimate: str
    confidence: float


class AnomalyResponse(BaseModel):
    transaction_id: str
    anomaly_type: str
    severity: float
    explanation: str
    confidence: float


class DuplicateGroupResponse(BaseModel):
    transaction_ids: List[str]
    similarity_score: float
    duplicate_type: str
    explanation: str


class PredictionsOverviewResponse(BaseModel):
    predictions: List[BudgetPredictionResponse]
    alerts: List[BudgetAlertResponse]
    recommendations: List[SmartRecommendationResponse]
    summary: Dict


class AnomaliesOverviewResponse(BaseModel):
    anomalies: List[AnomalyResponse]
    duplicate_groups: List[DuplicateGroupResponse]
    summary: Dict


# ML System initialization (lazy loading)
_budget_system = None
_anomaly_detector = None


def get_budget_system():
    """Get or create the budget intelligence system (singleton)"""
    global _budget_system
    if _budget_system is None:
        try:
            from ml_budget_predictor import BudgetIntelligenceSystem
            _budget_system = BudgetIntelligenceSystem()
            logger.info("Budget Intelligence System initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Budget Intelligence System: {e}")
            raise HTTPException(status_code=500, detail="ML system unavailable")
    return _budget_system


def get_anomaly_detector():
    """Get or create the anomaly detector (singleton)"""
    global _anomaly_detector
    if _anomaly_detector is None:
        try:
            from ml_anomaly_detector import TransactionAnomalyDetector
            _anomaly_detector = TransactionAnomalyDetector()
            logger.info("Anomaly Detector initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Anomaly Detector: {e}")
            raise HTTPException(status_code=500, detail="ML system unavailable")
    return _anomaly_detector


def train_systems_if_needed(db: Session, force: bool = False):
    """Train ML systems on transaction data if not already trained"""
    budget_system = get_budget_system()
    anomaly_detector = get_anomaly_detector()

    # Check if systems need training
    if not force and hasattr(budget_system, 'historical_data') and budget_system.historical_data is not None:
        return

    # Load transactions from database
    transactions = db.query(Transaction).filter(
        Transaction.amount < 0,
        Transaction.exclude == False
    ).all()

    if len(transactions) < 50:
        logger.warning("Insufficient transactions for ML training")
        return

    # Convert to DataFrame
    df_data = []
    for tx in transactions:
        tags = [t.strip().lower() for t in (tx.tags or "").split(",") if t.strip()]
        category = tags[0] if tags else (tx.category or "non-categorise")

        df_data.append({
            'id': tx.id,
            'label': tx.label,
            'amount': tx.amount,
            'date_op': tx.date_op.isoformat() if tx.date_op else None,
            'month': tx.month,
            'category': category,
            'account_label': tx.compte_label or "",
            'is_expense': 1 if tx.amount < 0 else 0
        })

    df = pd.DataFrame(df_data)

    # Load category budgets for configuration
    budgets = db.query(CategoryBudget).filter(CategoryBudget.is_active == True).all()
    budgets_config = {b.category: b.budget_amount for b in budgets}

    # Train systems
    try:
        budget_system.fit(df, budgets_config)
        anomaly_detector.fit(df)
        logger.info(f"ML systems trained on {len(df)} transactions")
    except Exception as e:
        logger.error(f"ML training failed: {e}")


# Endpoints

@router.get("/overview", response_model=PredictionsOverviewResponse)
def get_predictions_overview(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a comprehensive overview of budget predictions, alerts, and recommendations
    for the specified month.
    """
    logger.info(f"Predictions overview requested for {month} by {current_user.username}")

    try:
        # Train systems if needed
        train_systems_if_needed(db)

        budget_system = get_budget_system()

        # Calculate current spending by category
        transactions = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.amount < 0,
            Transaction.exclude == False
        ).all()

        current_spending = {}
        for tx in transactions:
            tags = [t.strip().lower() for t in (tx.tags or "").split(",") if t.strip()]
            category = tags[0] if tags else (tx.category or "non-categorise")

            if category not in current_spending:
                current_spending[category] = 0
            current_spending[category] += abs(tx.amount)

        if not current_spending:
            return PredictionsOverviewResponse(
                predictions=[],
                alerts=[],
                recommendations=[],
                summary={
                    "total_categories": 0,
                    "at_risk_count": 0,
                    "month": month,
                    "message": "Pas de donnees pour ce mois"
                }
            )

        # Parse month to datetime
        year, month_num = month.split('-')
        current_date = datetime(int(year), int(month_num), 15)  # Mid-month

        # Get predictions
        predictions_raw = budget_system.predict_month_end(current_date, current_spending)
        predictions = [
            BudgetPredictionResponse(
                category=p.category,
                current_spent=p.current_spent,
                predicted_month_end=round(p.predicted_month_end, 2),
                monthly_average=round(p.monthly_average, 2),
                trend_direction=p.trend_direction,
                confidence=round(p.confidence, 2),
                recommendation=p.recommendation
            )
            for p in predictions_raw[:10]  # Top 10
        ]

        # Get alerts
        alerts_raw = budget_system.generate_alerts(current_date, current_spending)
        alerts = [
            BudgetAlertResponse(
                alert_type=a.alert_type,
                category=a.category,
                severity=a.severity,
                message=a.message,
                current_amount=round(a.current_amount, 2),
                predicted_amount=round(a.predicted_amount, 2),
                threshold=round(a.threshold, 2),
                days_remaining=a.days_remaining
            )
            for a in alerts_raw[:5]  # Top 5 alerts
        ]

        # Get recommendations
        recommendations_raw = budget_system.generate_smart_recommendations(current_spending)
        recommendations = [
            SmartRecommendationResponse(
                recommendation_type=r.recommendation_type,
                category=r.category,
                current_budget=round(r.current_budget, 2),
                suggested_budget=round(r.suggested_budget, 2),
                reasoning=r.reasoning,
                impact_estimate=r.impact_estimate,
                confidence=round(r.confidence, 2)
            )
            for r in recommendations_raw[:5]  # Top 5
        ]

        # Summary
        at_risk = len([a for a in alerts_raw if a.severity in ['high', 'medium']])

        return PredictionsOverviewResponse(
            predictions=predictions,
            alerts=alerts,
            recommendations=recommendations,
            summary={
                "total_categories": len(current_spending),
                "total_spending": round(sum(current_spending.values()), 2),
                "at_risk_count": at_risk,
                "alerts_count": len(alerts_raw),
                "month": month
            }
        )

    except Exception as e:
        logger.error(f"Predictions error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating predictions: {str(e)}")


@router.get("/alerts", response_model=List[BudgetAlertResponse])
def get_budget_alerts(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get budget alerts for the specified month."""
    logger.info(f"Alerts requested for {month} by {current_user.username}")

    try:
        train_systems_if_needed(db)
        budget_system = get_budget_system()

        # Calculate current spending
        transactions = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.amount < 0,
            Transaction.exclude == False
        ).all()

        current_spending = {}
        for tx in transactions:
            tags = [t.strip().lower() for t in (tx.tags or "").split(",") if t.strip()]
            category = tags[0] if tags else (tx.category or "non-categorise")

            if category not in current_spending:
                current_spending[category] = 0
            current_spending[category] += abs(tx.amount)

        year, month_num = month.split('-')
        current_date = datetime(int(year), int(month_num), 15)

        alerts_raw = budget_system.generate_alerts(current_date, current_spending)

        # Filter by severity if specified
        if severity:
            alerts_raw = [a for a in alerts_raw if a.severity == severity]

        return [
            BudgetAlertResponse(
                alert_type=a.alert_type,
                category=a.category,
                severity=a.severity,
                message=a.message,
                current_amount=round(a.current_amount, 2),
                predicted_amount=round(a.predicted_amount, 2),
                threshold=round(a.threshold, 2),
                days_remaining=a.days_remaining
            )
            for a in alerts_raw
        ]

    except Exception as e:
        logger.error(f"Alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalies", response_model=AnomaliesOverviewResponse)
def detect_anomalies(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detect anomalies and duplicates in transactions for the specified month."""
    logger.info(f"Anomaly detection requested for {month} by {current_user.username}")

    try:
        train_systems_if_needed(db)
        anomaly_detector = get_anomaly_detector()

        # Get transactions for the month
        transactions = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.exclude == False
        ).order_by(Transaction.date_op.desc()).limit(limit).all()

        if not transactions:
            return AnomaliesOverviewResponse(
                anomalies=[],
                duplicate_groups=[],
                summary={"total_transactions": 0, "anomalies_found": 0, "duplicates_found": 0}
            )

        # Convert to dict format for ML
        tx_dicts = [
            {
                'id': tx.id,
                'label': tx.label,
                'amount': tx.amount,
                'date_op': tx.date_op.isoformat() if tx.date_op else None,
                'month': tx.month,
                'category': tx.category or "",
                'account_label': tx.compte_label or ""
            }
            for tx in transactions
        ]

        # Batch analyze
        anomalies_raw, duplicates_raw = anomaly_detector.batch_analyze(tx_dicts)

        anomalies = [
            AnomalyResponse(
                transaction_id=str(a.transaction_id),
                anomaly_type=a.anomaly_type,
                severity=round(a.severity, 2),
                explanation=a.explanation,
                confidence=round(a.confidence, 2)
            )
            for a in anomalies_raw[:20]  # Limit to 20
        ]

        duplicate_groups = [
            DuplicateGroupResponse(
                transaction_ids=[str(tx.get('id', '')) for tx in dg.transactions],
                similarity_score=round(dg.similarity_score, 1),
                duplicate_type=dg.duplicate_type,
                explanation=dg.explanation
            )
            for dg in duplicates_raw[:10]  # Limit to 10 groups
        ]

        return AnomaliesOverviewResponse(
            anomalies=anomalies,
            duplicate_groups=duplicate_groups,
            summary={
                "total_transactions": len(transactions),
                "anomalies_found": len(anomalies_raw),
                "duplicates_found": len(duplicates_raw),
                "high_severity_count": len([a for a in anomalies_raw if a.severity > 0.7])
            }
        )

    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrain")
def retrain_ml_systems(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Force retraining of ML systems on latest data."""
    logger.info(f"ML retraining requested by {current_user.username}")

    try:
        train_systems_if_needed(db, force=True)
        return {"status": "success", "message": "ML systems retrained successfully"}
    except Exception as e:
        logger.error(f"Retraining error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
