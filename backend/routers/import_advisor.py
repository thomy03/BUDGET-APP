"""
Import Advisor Router - AI-powered post-import analysis
Provides intelligent insights after CSV/XLSX imports
"""
import logging
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel

from models.database import get_db, Transaction, ImportMetadata
from services.ai_cache import AICacheService, generate_cache_key
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/import-advisor",
    tags=["import-advisor"]
)


# Pydantic models
class ImportAnalysisRequest(BaseModel):
    import_id: str
    month: str  # YYYY-MM format


class AnomalyItem(BaseModel):
    type: str  # 'unusual_amount', 'duplicate_suspect', 'category_spike'
    description: str
    amount: Optional[float] = None
    transaction_id: Optional[int] = None
    severity: str = 'low'  # 'low', 'medium', 'high'


class ImportInsight(BaseModel):
    status: str  # 'ready', 'processing', 'error'
    import_id: str
    month: str
    narrative: Optional[str] = None
    anomalies: List[AnomalyItem] = []
    recommendations: List[str] = []
    comparison: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None


class MonthComparison(BaseModel):
    current_month: str
    previous_month: Optional[str] = None
    current_total: float
    previous_total: Optional[float] = None
    variance: Optional[float] = None
    variance_pct: Optional[float] = None
    categories_increased: List[str] = []
    categories_decreased: List[str] = []


# Helper functions
def get_month_stats(db: Session, month: str) -> Dict[str, Any]:
    """Get spending statistics for a month."""
    transactions = db.query(Transaction).filter(
        and_(
            Transaction.month == month,
            Transaction.exclude == False
        )
    ).all()

    if not transactions:
        return {
            'total_expenses': 0,
            'total_income': 0,
            'tx_count': 0,
            'by_category': {}
        }

    expenses = [t for t in transactions if t.amount < 0]
    income = [t for t in transactions if t.amount > 0]

    # Group by category/tags
    category_totals = {}
    for tx in expenses:
        tag = tx.tags.split(',')[0] if tx.tags else (tx.category or 'autres')
        tag = tag.strip().lower()
        if tag not in category_totals:
            category_totals[tag] = 0
        category_totals[tag] += abs(tx.amount)

    return {
        'total_expenses': sum(abs(t.amount) for t in expenses),
        'total_income': sum(t.amount for t in income),
        'tx_count': len(transactions),
        'by_category': category_totals
    }


def get_previous_month(month: str) -> str:
    """Get the previous month string (YYYY-MM)."""
    year, mon = map(int, month.split('-'))
    if mon == 1:
        return f"{year-1}-12"
    return f"{year}-{mon-1:02d}"


def detect_anomalies(db: Session, month: str, stats: Dict[str, Any]) -> List[AnomalyItem]:
    """Detect anomalies in the imported transactions."""
    anomalies = []

    transactions = db.query(Transaction).filter(
        and_(
            Transaction.month == month,
            Transaction.exclude == False,
            Transaction.amount < 0
        )
    ).all()

    if not transactions:
        return anomalies

    # Calculate average and std dev for amount detection
    amounts = [abs(t.amount) for t in transactions]
    if len(amounts) < 3:
        return anomalies

    avg_amount = sum(amounts) / len(amounts)
    variance = sum((a - avg_amount) ** 2 for a in amounts) / len(amounts)
    std_dev = variance ** 0.5

    # Detect unusually large transactions (> 2 std dev)
    threshold = avg_amount + (2 * std_dev)
    for tx in transactions:
        if abs(tx.amount) > threshold and abs(tx.amount) > 100:  # Min 100€
            anomalies.append(AnomalyItem(
                type='unusual_amount',
                description=f"Transaction inhabituelle: {tx.label[:50]} ({abs(tx.amount):.2f}€)",
                amount=abs(tx.amount),
                transaction_id=tx.id,
                severity='medium' if abs(tx.amount) > avg_amount * 3 else 'low'
            ))

    # Detect potential duplicates (same amount, similar label, same day)
    seen = {}
    for tx in transactions:
        key = f"{tx.date_op}:{abs(tx.amount)}"
        if key in seen:
            prev_tx = seen[key]
            if prev_tx.label[:20].lower() == tx.label[:20].lower():
                anomalies.append(AnomalyItem(
                    type='duplicate_suspect',
                    description=f"Doublon potentiel: {tx.label[:30]} ({abs(tx.amount):.2f}€)",
                    amount=abs(tx.amount),
                    transaction_id=tx.id,
                    severity='high'
                ))
        else:
            seen[key] = tx

    # Detect category spikes compared to previous month
    prev_month = get_previous_month(month)
    prev_stats = get_month_stats(db, prev_month)

    for category, total in stats['by_category'].items():
        prev_total = prev_stats['by_category'].get(category, 0)
        if prev_total > 0 and total > prev_total * 2 and total > 100:  # Doubled and > 100€
            anomalies.append(AnomalyItem(
                type='category_spike',
                description=f"Hausse importante: {category} (+{((total/prev_total)-1)*100:.0f}%)",
                amount=total - prev_total,
                severity='medium'
            ))

    return anomalies[:10]  # Limit to 10 anomalies


def generate_narrative(stats: Dict[str, Any], comparison: MonthComparison, anomalies: List[AnomalyItem]) -> str:
    """Generate a narrative summary of the import analysis."""
    parts = []

    # Opening emoji based on overall health
    if comparison.variance_pct and comparison.variance_pct > 10:
        emoji = "⚠️"
    elif comparison.variance_pct and comparison.variance_pct < -10:
        emoji = "✨"
    else:
        emoji = "📊"

    # Total summary
    parts.append(f"{emoji} Ce mois-ci, vous avez enregistré {stats['tx_count']} transactions pour un total de {stats['total_expenses']:.2f}€ de dépenses.")

    # Comparison with previous month
    if comparison.variance is not None and comparison.previous_total:
        if comparison.variance > 0:
            parts.append(f"C'est {abs(comparison.variance):.2f}€ de plus que le mois dernier (+{abs(comparison.variance_pct):.1f}%).")
        elif comparison.variance < 0:
            parts.append(f"Bonne nouvelle ! C'est {abs(comparison.variance):.2f}€ de moins que le mois dernier (-{abs(comparison.variance_pct):.1f}%).")
        else:
            parts.append("Vos dépenses sont stables par rapport au mois dernier.")

    # Top categories
    if stats['by_category']:
        top_cats = sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True)[:3]
        top_str = ', '.join([f"{cat} ({amount:.0f}€)" for cat, amount in top_cats])
        parts.append(f"Vos principales catégories: {top_str}.")

    # Anomalies summary
    high_anomalies = [a for a in anomalies if a.severity == 'high']
    if high_anomalies:
        parts.append(f"⚠️ Attention: {len(high_anomalies)} point(s) nécessitant votre attention.")

    return ' '.join(parts)


def generate_recommendations(stats: Dict[str, Any], comparison: MonthComparison, anomalies: List[AnomalyItem]) -> List[str]:
    """Generate actionable recommendations."""
    recommendations = []

    # Budget increase warning
    if comparison.variance_pct and comparison.variance_pct > 15:
        recommendations.append(f"Vos dépenses ont augmenté de {comparison.variance_pct:.0f}%. Identifiez les postes qui ont le plus augmenté.")

    # Category-specific recommendations
    if comparison.categories_increased:
        top_increase = comparison.categories_increased[0] if comparison.categories_increased else None
        if top_increase:
            recommendations.append(f"La catégorie '{top_increase}' a significativement augmenté. Vérifiez s'il s'agit d'une dépense exceptionnelle.")

    # Duplicate check
    duplicates = [a for a in anomalies if a.type == 'duplicate_suspect']
    if duplicates:
        recommendations.append(f"Vérifiez {len(duplicates)} transaction(s) qui pourraient être des doublons.")

    # Tag recommendation
    untagged_estimate = stats['tx_count'] * 0.2  # Assume 20% might be untagged
    if untagged_estimate > 5:
        recommendations.append("Pensez à taguer vos transactions pour un meilleur suivi par catégorie.")

    # Savings opportunity
    if stats['total_income'] > 0 and stats['total_expenses'] < stats['total_income'] * 0.7:
        recommendations.append("Votre ratio dépenses/revenus est bon. Envisagez d'épargner la différence.")

    return recommendations[:5]  # Limit to 5 recommendations


async def process_import_analysis(import_id: str, month: str, db: Session):
    """Background task to process import analysis."""
    try:
        logger.info(f"Processing import analysis for {import_id}, month {month}")

        # Get statistics
        stats = get_month_stats(db, month)
        prev_month = get_previous_month(month)
        prev_stats = get_month_stats(db, prev_month)

        # Build comparison
        variance = stats['total_expenses'] - prev_stats['total_expenses'] if prev_stats['total_expenses'] else None
        variance_pct = (variance / prev_stats['total_expenses'] * 100) if prev_stats['total_expenses'] and variance else None

        # Determine category changes
        categories_increased = []
        categories_decreased = []
        for cat, total in stats['by_category'].items():
            prev_total = prev_stats['by_category'].get(cat, 0)
            if prev_total > 0:
                change_pct = (total - prev_total) / prev_total * 100
                if change_pct > 20:
                    categories_increased.append(cat)
                elif change_pct < -20:
                    categories_decreased.append(cat)

        comparison = MonthComparison(
            current_month=month,
            previous_month=prev_month if prev_stats['tx_count'] > 0 else None,
            current_total=stats['total_expenses'],
            previous_total=prev_stats['total_expenses'] if prev_stats['tx_count'] > 0 else None,
            variance=variance,
            variance_pct=variance_pct,
            categories_increased=categories_increased,
            categories_decreased=categories_decreased
        )

        # Detect anomalies
        anomalies = detect_anomalies(db, month, stats)

        # Generate narrative and recommendations
        narrative = generate_narrative(stats, comparison, anomalies)
        recommendations = generate_recommendations(stats, comparison, anomalies)

        # Build insight result
        insight = ImportInsight(
            status='ready',
            import_id=import_id,
            month=month,
            narrative=narrative,
            anomalies=anomalies,
            recommendations=recommendations,
            comparison=comparison.model_dump(),
            summary={
                'total_expenses': stats['total_expenses'],
                'total_income': stats['total_income'],
                'transaction_count': stats['tx_count'],
                'top_categories': dict(sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True)[:5])
            }
        )

        # Cache the result
        cache_service = AICacheService(db)
        cache_key = generate_cache_key('import', import_id, month)
        cache_service.set_cached(
            cache_key=cache_key,
            cache_type='import',
            data=insight.model_dump(),
            month=month
        )

        logger.info(f"Import analysis completed and cached for {import_id}")

    except Exception as e:
        logger.error(f"Error processing import analysis: {e}")
        # Cache error state
        try:
            cache_service = AICacheService(db)
            cache_key = generate_cache_key('import', import_id, month)
            cache_service.set_cached(
                cache_key=cache_key,
                cache_type='import',
                data={'status': 'error', 'error': str(e), 'import_id': import_id, 'month': month},
                ttl_hours=0.5  # Short TTL for errors
            )
        except Exception:
            pass


# Endpoints
@router.post("/analyze", response_model=dict)
async def analyze_import(
    request: ImportAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger AI analysis for a completed import.
    Analysis runs in background and results are cached.
    """
    # Check if already cached
    cache_service = AICacheService(db)
    cache_key = generate_cache_key('import', request.import_id, request.month)
    cached = cache_service.get_cached(cache_key, 'import')

    if cached and cached.get('status') == 'ready':
        return {"status": "ready", "import_id": request.import_id, "cached": True}

    # Start background analysis
    background_tasks.add_task(
        process_import_analysis,
        request.import_id,
        request.month,
        db
    )

    return {
        "status": "processing",
        "import_id": request.import_id,
        "message": "Analysis started. Poll /insights/{import_id} for results."
    }


@router.get("/insights/{import_id}", response_model=ImportInsight)
async def get_insights(
    import_id: str,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get import analysis insights.
    Returns cached results or 202 if still processing.
    """
    cache_service = AICacheService(db)

    # Try to find cached insights
    if month:
        cache_key = generate_cache_key('import', import_id, month)
        cached = cache_service.get_cached(cache_key, 'import')
    else:
        # Search for any cached insight with this import_id
        cached = None
        # Try recent months
        from datetime import datetime
        current = datetime.now()
        for i in range(3):
            test_month = f"{current.year}-{(current.month - i - 1) % 12 + 1:02d}"
            cache_key = generate_cache_key('import', import_id, test_month)
            cached = cache_service.get_cached(cache_key, 'import')
            if cached:
                break

    if not cached:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail={"status": "processing", "import_id": import_id, "message": "Analysis still in progress"}
        )

    return ImportInsight(**cached)


@router.delete("/insights/{import_id}")
async def invalidate_insights(
    import_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Invalidate cached insights for an import."""
    cache_service = AICacheService(db)
    count = cache_service.invalidate(f"import:{import_id}:%")

    return {"invalidated": count, "import_id": import_id}
