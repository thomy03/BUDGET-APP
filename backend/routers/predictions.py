"""
Predictions Router for Budget Famille v4.0
Exposes ML-powered budget predictions and anomaly detection
"""
import logging
import threading
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

# Global state for ML training
_training_lock = threading.Lock()
_training_in_progress = False
_training_completed = False

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
    # Prophet confidence intervals
    confidence_lower: float = 0.0
    confidence_upper: float = 0.0
    seasonality_detected: bool = False
    seasonal_component: float = 0.0
    prediction_method: str = "linear"
    mae_score: float = 0.0


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
_advanced_budget_system = None
_anomaly_detector = None
_use_advanced_predictor = True  # Try Prophet first


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


def get_advanced_budget_system():
    """Get or create the advanced budget intelligence system with Prophet (singleton)"""
    global _advanced_budget_system
    if _advanced_budget_system is None:
        try:
            from ml_advanced_predictor import AdvancedBudgetIntelligenceSystem
            _advanced_budget_system = AdvancedBudgetIntelligenceSystem()
            logger.info("Advanced Budget Intelligence System (Prophet) initialized")
        except Exception as e:
            logger.warning(f"Advanced predictor unavailable, using basic: {e}")
            return None
    return _advanced_budget_system


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


def is_ml_ready() -> bool:
    """Check if ML models are trained and ready for predictions"""
    global _training_completed
    return _training_completed


def is_ml_training() -> bool:
    """Check if ML training is currently in progress"""
    global _training_in_progress
    return _training_in_progress


def train_systems_if_needed(db: Session, force: bool = False):
    """Train ML systems on transaction data if not already trained"""
    global _training_in_progress, _training_completed

    # Quick exit if already trained and not forcing
    if _training_completed and not force:
        logger.debug("ML systems already trained, skipping...")
        return

    # Quick exit if already training (non-blocking)
    with _training_lock:
        if _training_in_progress and not force:
            logger.debug("ML training already in progress, skipping...")
            return
        _training_in_progress = True

    try:
        budget_system = get_budget_system()
        advanced_system = get_advanced_budget_system()  # May be None if Prophet unavailable
        anomaly_detector = get_anomaly_detector()

        # Check if systems need training - check BOTH budget_system AND anomaly_detector
        budget_trained = hasattr(budget_system, 'historical_data') and budget_system.historical_data is not None
        anomaly_trained = hasattr(anomaly_detector, 'isolation_forest') and anomaly_detector.isolation_forest is not None

        if not force and budget_trained and anomaly_trained:
            logger.debug("ML systems already trained, skipping...")
            _training_completed = True
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
                'account_label': tx.account_label or "",
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
            logger.info(f"✅ Basic ML systems trained on {len(df)} transactions")
            _training_completed = True
        except Exception as e:
            logger.error(f"Basic ML training failed: {e}")

        # Train advanced Prophet system if available
        if advanced_system is not None:
            try:
                advanced_system.fit(df, budgets_config)
                logger.info(f"✅ Advanced Prophet system trained on {len(df)} transactions")
            except Exception as e:
                logger.warning(f"Advanced Prophet training failed (will use basic): {e}")

    finally:
        _training_in_progress = False


# Endpoints

class MLStatusResponse(BaseModel):
    """Response model for ML status endpoint"""
    ready: bool = Field(description="True if ML models are trained and ready")
    training: bool = Field(description="True if ML training is currently in progress")
    message: str = Field(description="Human-readable status message")


@router.get("/status", response_model=MLStatusResponse)
def get_ml_status():
    """
    Check if ML models are trained and ready for predictions.
    Use this endpoint to show loading state in the frontend.
    """
    ready = is_ml_ready()
    training = is_ml_training()

    if ready:
        message = "Modeles ML prets - predictions disponibles"
    elif training:
        message = "Entrainement ML en cours... Veuillez patienter"
    else:
        message = "Modeles ML non initialises - premier chargement en cours"

    return MLStatusResponse(ready=ready, training=training, message=message)


@router.get("/overview", response_model=PredictionsOverviewResponse)
def get_predictions_overview(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a comprehensive overview of budget predictions, alerts, and recommendations
    for the specified month. Uses Prophet for advanced predictions when available.
    """
    logger.info(f"Predictions overview requested for {month} by {current_user.username}")

    # Quick check: if ML is training in background, return immediately with placeholder
    if is_ml_training() and not is_ml_ready():
        logger.info("ML training in progress, returning placeholder response")
        return PredictionsOverviewResponse(
            predictions=[],
            alerts=[],
            recommendations=[],
            summary={
                "total_categories": 0,
                "at_risk_count": 0,
                "month": month,
                "message": "Modeles ML en cours d'entrainement... Veuillez reessayer dans quelques secondes.",
                "prediction_method": "training"
            }
        )

    try:
        # Train systems if needed
        train_systems_if_needed(db)

        # Try advanced Prophet system first, fallback to basic
        advanced_system = get_advanced_budget_system()
        budget_system = get_budget_system()
        use_advanced = advanced_system is not None and advanced_system.is_trained

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
                    "message": "Pas de donnees pour ce mois",
                    "prediction_method": "none"
                }
            )

        # Parse month to datetime
        year, month_num = month.split('-')
        current_date = datetime(int(year), int(month_num), 15)  # Mid-month

        # Get predictions (use advanced if available)
        if use_advanced:
            predictions_raw = advanced_system.predict_month_end(current_date, current_spending)
            predictions = [
                BudgetPredictionResponse(
                    category=p.category,
                    current_spent=p.current_spent,
                    predicted_month_end=round(p.predicted_month_end, 2),
                    monthly_average=round(p.monthly_average, 2),
                    trend_direction=p.trend_direction,
                    confidence=round(p.confidence, 2),
                    recommendation=p.recommendation,
                    confidence_lower=round(p.confidence_lower, 2),
                    confidence_upper=round(p.confidence_upper, 2),
                    seasonality_detected=p.seasonality_detected,
                    seasonal_component=round(p.seasonal_component, 2),
                    prediction_method=p.prediction_method,
                    mae_score=round(p.mae_score, 2)
                )
                for p in predictions_raw[:10]  # Top 10
            ]
            alerts_raw = advanced_system.generate_alerts(current_date, current_spending)
            recommendations_raw = advanced_system.generate_smart_recommendations(current_spending)
        else:
            # Fallback to basic system
            predictions_raw = budget_system.predict_month_end(current_date, current_spending)
            predictions = [
                BudgetPredictionResponse(
                    category=p.category,
                    current_spent=p.current_spent,
                    predicted_month_end=round(p.predicted_month_end, 2),
                    monthly_average=round(p.monthly_average, 2),
                    trend_direction=p.trend_direction,
                    confidence=round(p.confidence, 2),
                    recommendation=p.recommendation,
                    confidence_lower=round(p.predicted_month_end * 0.8, 2),  # Basic interval
                    confidence_upper=round(p.predicted_month_end * 1.2, 2),
                    prediction_method="linear"
                )
                for p in predictions_raw[:10]  # Top 10
            ]
            alerts_raw = budget_system.generate_alerts(current_date, current_spending)
            recommendations_raw = budget_system.generate_smart_recommendations(current_spending)

        # Format alerts
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

        # Format recommendations
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
        prophet_count = sum(1 for p in predictions if p.prediction_method == "prophet")

        return PredictionsOverviewResponse(
            predictions=predictions,
            alerts=alerts,
            recommendations=recommendations,
            summary={
                "total_categories": len(current_spending),
                "total_spending": round(sum(current_spending.values()), 2),
                "at_risk_count": at_risk,
                "alerts_count": len(alerts_raw),
                "month": month,
                "prediction_method": "prophet" if use_advanced else "linear",
                "prophet_categories": prophet_count
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

    # Quick check: if ML is training in background, return immediately
    if is_ml_training() and not is_ml_ready():
        logger.info("ML training in progress, returning placeholder response")
        return AnomaliesOverviewResponse(
            anomalies=[],
            duplicate_groups=[],
            summary={
                "total_transactions": 0,
                "anomalies_found": 0,
                "duplicates_found": 0,
                "message": "Modeles ML en cours d'entrainement... Veuillez reessayer dans quelques secondes."
            }
        )

    try:
        # Try to train ML systems (may fail if not enough data)
        try:
            train_systems_if_needed(db)
        except Exception as train_error:
            logger.warning(f"ML training skipped: {train_error}")
            # Return empty result if training fails - don't block the request
            return AnomaliesOverviewResponse(
                anomalies=[],
                duplicate_groups=[],
                summary={
                    "total_transactions": 0,
                    "anomalies_found": 0,
                    "duplicates_found": 0,
                    "message": f"ML non disponible: {str(train_error)[:100]}"
                }
            )

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
                'account_label': tx.account_label or ""
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
    async_mode: bool = Query(True, description="Run training asynchronously in background"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrain ML systems on latest data.

    **Modes:**
    - async_mode=true (default): Submits training job to background, returns immediately with job_id
    - async_mode=false: Trains synchronously (blocks request, may timeout for large datasets)

    **Response (async mode):**
    - job_id: Use with /predictions/retrain/status/{job_id} to check progress
    - status: "submitted"
    """
    logger.info(f"ML retraining requested by {current_user.username} (async={async_mode})")

    if async_mode:
        # Submit to background scheduler
        try:
            from services.scheduler_service import submit_ml_training_job
            from models.database import DATABASE_URL

            job_id = submit_ml_training_job(DATABASE_URL, force=True)

            return {
                "status": "submitted",
                "message": "ML training job submitted to background queue",
                "job_id": job_id,
                "check_status_url": f"/api/predictions/retrain/status/{job_id}"
            }
        except Exception as e:
            logger.error(f"Failed to submit async training: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to submit training job: {str(e)}")
    else:
        # Synchronous training (legacy behavior)
        try:
            train_systems_if_needed(db, force=True)
            return {"status": "success", "message": "ML systems retrained successfully"}
        except Exception as e:
            logger.error(f"Retraining error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/retrain/status/{job_id}")
def get_retrain_status(
    job_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get status of a background ML training job.

    **Response fields:**
    - status: pending, running, completed, failed, cancelled
    - started_at: When the job started
    - completed_at: When the job finished
    - result: Training results (when completed)
    - error: Error message (when failed)
    - duration_seconds: How long the job took
    """
    from services.scheduler_service import get_scheduler_service

    scheduler = get_scheduler_service()
    status = scheduler.get_job_status(job_id)

    if status is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return status


@router.get("/retrain/jobs")
def list_training_jobs(
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user)
):
    """
    List recent ML training jobs.

    Returns the most recent training jobs with their status.
    """
    from services.scheduler_service import get_scheduler_service

    scheduler = get_scheduler_service()
    jobs = scheduler.list_jobs(limit=limit)

    # Filter to only ML training jobs
    ml_jobs = [j for j in jobs if j.get("job_id", "").startswith("ml_training")]

    return {
        "jobs": ml_jobs,
        "total": len(ml_jobs)
    }
