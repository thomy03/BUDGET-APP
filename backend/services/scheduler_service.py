"""
Scheduler Service for Budget Famille v4.2
Background task scheduler using APScheduler for async ML training.

This service handles:
- Periodic ML model retraining
- Background task execution
- Job status tracking

Author: Claude Code - Phase 3 Performance
Date: 2026-01-26
"""
import logging
import threading
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobResult:
    """Result container for background jobs"""
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.status = JobStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Any = None
        self.error: Optional[str] = None
        self.progress: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "progress": self.progress,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.completed_at and self.started_at else None
            )
        }


class SchedulerService:
    """
    Background task scheduler service.

    Uses threading for SQLite compatibility (SQLite doesn't support
    concurrent writes from multiple processes like Celery would require).

    For production with PostgreSQL, consider migrating to Celery or RQ.
    """

    _instance: Optional['SchedulerService'] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern for scheduler service"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._jobs: Dict[str, JobResult] = {}
        self._job_counter = 0
        self._scheduler_lock = threading.Lock()
        self._initialized = True
        logger.info("SchedulerService initialized")

    def _generate_job_id(self, prefix: str = "job") -> str:
        """Generate unique job ID"""
        with self._scheduler_lock:
            self._job_counter += 1
            return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._job_counter}"

    def submit_job(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        job_type: str = "task"
    ) -> str:
        """
        Submit a job to run in background thread.

        Args:
            func: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            job_type: Type prefix for job ID

        Returns:
            job_id: Unique identifier for tracking the job
        """
        kwargs = kwargs or {}
        job_id = self._generate_job_id(job_type)
        job_result = JobResult(job_id)

        with self._scheduler_lock:
            self._jobs[job_id] = job_result

        def run_job():
            job_result.status = JobStatus.RUNNING
            job_result.started_at = datetime.now()

            try:
                logger.info(f"Starting background job: {job_id}")
                result = func(*args, **kwargs)
                job_result.result = result
                job_result.status = JobStatus.COMPLETED
                job_result.progress = 100.0
                logger.info(f"Background job completed: {job_id}")
            except Exception as e:
                job_result.status = JobStatus.FAILED
                job_result.error = str(e)
                logger.error(f"Background job failed: {job_id} - {e}")
            finally:
                job_result.completed_at = datetime.now()

        # Start background thread
        thread = threading.Thread(target=run_job, daemon=True)
        thread.start()

        logger.info(f"Job submitted: {job_id}")
        return job_id

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a background job"""
        job = self._jobs.get(job_id)
        if job:
            return job.to_dict()
        return None

    def list_jobs(self, limit: int = 50) -> list:
        """List recent jobs"""
        jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j.started_at or datetime.min, reverse=True)
        return [j.to_dict() for j in jobs[:limit]]

    def cancel_job(self, job_id: str) -> bool:
        """
        Mark a job as cancelled.
        Note: This doesn't actually stop a running thread in Python,
        but marks it as cancelled for status purposes.
        """
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.PENDING:
            job.status = JobStatus.CANCELLED
            return True
        return False

    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove completed jobs older than max_age_hours"""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)

        with self._scheduler_lock:
            to_remove = []
            for job_id, job in self._jobs.items():
                if job.completed_at and job.completed_at.timestamp() < cutoff:
                    to_remove.append(job_id)

            for job_id in to_remove:
                del self._jobs[job_id]

            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old jobs")


# Singleton instance
_scheduler_service: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    """Get the global scheduler service instance"""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service


# =============================================================================
# ML Training Background Tasks
# =============================================================================

def train_ml_systems_background(db_url: str, force: bool = False) -> Dict[str, Any]:
    """
    Train ML systems in background thread.

    This function creates its own database session to avoid SQLite threading issues.

    Args:
        db_url: Database connection URL
        force: Force retraining even if already trained

    Returns:
        Dict with training results
    """
    import pandas as pd
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Create new engine and session for this thread
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False}  # Required for SQLite
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        from models.database import Transaction, CategoryBudget

        # Import ML systems
        try:
            from ml_budget_predictor import BudgetIntelligenceSystem
            budget_system = BudgetIntelligenceSystem()
        except Exception as e:
            logger.error(f"Failed to import BudgetIntelligenceSystem: {e}")
            budget_system = None

        try:
            from ml_anomaly_detector import TransactionAnomalyDetector
            anomaly_detector = TransactionAnomalyDetector()
        except Exception as e:
            logger.error(f"Failed to import TransactionAnomalyDetector: {e}")
            anomaly_detector = None

        try:
            from ml_advanced_predictor import AdvancedBudgetIntelligenceSystem
            advanced_system = AdvancedBudgetIntelligenceSystem()
        except Exception as e:
            logger.warning(f"Advanced predictor unavailable: {e}")
            advanced_system = None

        # Load transactions
        transactions = db.query(Transaction).filter(
            Transaction.amount < 0,
            Transaction.exclude == False
        ).all()

        if len(transactions) < 50:
            return {
                "status": "skipped",
                "reason": f"Insufficient transactions ({len(transactions)} < 50)",
                "transactions_count": len(transactions)
            }

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

        # Load category budgets
        budgets = db.query(CategoryBudget).filter(CategoryBudget.is_active == True).all()
        budgets_config = {b.category: b.budget_amount for b in budgets}

        results = {
            "status": "success",
            "transactions_count": len(df),
            "categories_count": len(budgets_config),
            "systems_trained": []
        }

        # Train budget system
        if budget_system:
            try:
                budget_system.fit(df, budgets_config)
                results["systems_trained"].append("budget_predictor")
                logger.info(f"Budget predictor trained on {len(df)} transactions")
            except Exception as e:
                logger.error(f"Budget predictor training failed: {e}")
                results["budget_predictor_error"] = str(e)

        # Train anomaly detector
        if anomaly_detector:
            try:
                anomaly_detector.fit(df)
                results["systems_trained"].append("anomaly_detector")
                logger.info(f"Anomaly detector trained on {len(df)} transactions")
            except Exception as e:
                logger.error(f"Anomaly detector training failed: {e}")
                results["anomaly_detector_error"] = str(e)

        # Train advanced Prophet system
        if advanced_system:
            try:
                advanced_system.fit(df, budgets_config)
                results["systems_trained"].append("prophet_predictor")
                logger.info(f"Prophet predictor trained on {len(df)} transactions")
            except Exception as e:
                logger.warning(f"Prophet training failed: {e}")
                results["prophet_error"] = str(e)

        return results

    except Exception as e:
        logger.error(f"Background ML training failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }
    finally:
        db.close()


def submit_ml_training_job(db_url: str, force: bool = False) -> str:
    """
    Submit ML training job to run in background.

    Args:
        db_url: Database connection URL
        force: Force retraining

    Returns:
        job_id for tracking
    """
    scheduler = get_scheduler_service()
    return scheduler.submit_job(
        func=train_ml_systems_background,
        args=(db_url, force),
        job_type="ml_training"
    )
