"""
Coach Router - AI-powered budget coaching
Provides dashboard tips, daily insights, and quick actions
"""
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel

from models.database import get_db, Transaction, Config, CategoryBudget
from services.ai_cache import AICacheService, generate_cache_key
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/coach",
    tags=["ai-coach"]
)


# Pydantic models
class CoachTip(BaseModel):
    id: str
    message: str
    category: str  # 'insight', 'warning', 'tip', 'motivation'
    icon: str
    priority: int = 0


class QuickAction(BaseModel):
    id: str
    label: str
    action_type: str  # 'navigate', 'trigger'
    target: str
    icon: str


class DailyInsight(BaseModel):
    message: str
    emoji: str
    data_point: Optional[str] = None


class DashboardTipsResponse(BaseModel):
    tips: List[CoachTip]
    refresh_at: str  # ISO timestamp for next refresh


class DailyInsightResponse(BaseModel):
    insight: DailyInsight
    valid_until: str  # ISO timestamp


class QuickActionsResponse(BaseModel):
    actions: List[QuickAction]


# Static tip templates
TIP_TEMPLATES = {
    'high_spending': [
        CoachTip(id='hs1', message="Vos dépenses {category} sont {pct}% au-dessus de la moyenne. Petit audit?", category='warning', icon='⚠️', priority=2),
        CoachTip(id='hs2', message="Cette semaine, {category} représente {amount}€. C'est plus que d'habitude!", category='insight', icon='📊', priority=1),
    ],
    'good_progress': [
        CoachTip(id='gp1', message="Bravo! Vous êtes à {pct}% de votre objectif {category}. Continuez!", category='motivation', icon='🎯', priority=1),
        CoachTip(id='gp2', message="Vous avez économisé {amount}€ ce mois-ci. Belle performance!", category='motivation', icon='💪', priority=2),
    ],
    'general': [
        CoachTip(id='gen1', message="Saviez-vous que les dépenses impulsives représentent en moyenne 23% du budget?", category='tip', icon='💡', priority=0),
        CoachTip(id='gen2', message="Astuce: Attendre 24h avant un achat non-essentiel réduit les achats impulsifs de 50%.", category='tip', icon='⏰', priority=0),
        CoachTip(id='gen3', message="Les petits montants s'additionnent: 5€/jour = 150€/mois = 1800€/an!", category='insight', icon='🔢', priority=0),
        CoachTip(id='gen4', message="Pensez à revoir vos abonnements mensuels. Des économies cachées vous attendent!", category='tip', icon='🔍', priority=0),
        CoachTip(id='gen5', message="Le meilleur moment pour planifier votre budget? Le dimanche soir!", category='tip', icon='📅', priority=0),
    ],
    'tagging': [
        CoachTip(id='tag1', message="Taguer vos transactions aide l'IA à mieux vous conseiller.", category='tip', icon='🏷️', priority=0),
        CoachTip(id='tag2', message="{untagged} transactions n'ont pas de tag. Quelques clics suffisent!", category='insight', icon='📝', priority=1),
    ],
}

DAILY_INSIGHT_TEMPLATES = [
    DailyInsight(message="Début de semaine! C'est le bon moment pour vérifier vos dernières transactions.", emoji="🌅"),
    DailyInsight(message="Milieu de mois: vous avez dépensé {spent}€ sur {budget}€ prévus.", emoji="📊"),
    DailyInsight(message="Fin de mois: bilan en vue! Prenez 5 minutes pour analyser vos dépenses.", emoji="🔚"),
    DailyInsight(message="Week-end = dépenses loisirs! Gardez un œil sur votre budget sorties.", emoji="🎉"),
    DailyInsight(message="Pensez à vérifier vos prélèvements automatiques ce mois-ci.", emoji="🔄"),
]

QUICK_ACTIONS_BASE = [
    QuickAction(id='qa1', label="Voir anomalies", action_type='navigate', target='/analytics?tab=anomalies', icon='🔍'),
    QuickAction(id='qa2', label="Taguer transactions", action_type='navigate', target='/transactions?filter=untagged', icon='🏷️'),
    QuickAction(id='qa3', label="Définir objectif", action_type='navigate', target='/settings?section=budgets', icon='🎯'),
]


# Helper functions
def get_month_spending(db: Session, month: str) -> Dict[str, float]:
    """Get spending by category for the month."""
    transactions = db.query(Transaction).filter(
        and_(
            Transaction.month == month,
            Transaction.exclude == False,
            Transaction.amount < 0
        )
    ).all()

    by_category = {}
    for tx in transactions:
        tag = tx.tags.split(',')[0] if tx.tags else 'autres'
        tag = tag.strip().lower()
        if tag not in by_category:
            by_category[tag] = 0
        by_category[tag] += abs(tx.amount)

    return by_category


def get_budget_progress(db: Session, month: str) -> List[Dict[str, Any]]:
    """Get budget vs actual spending progress."""
    budgets = db.query(CategoryBudget).filter(
        and_(
            CategoryBudget.is_active == True,
            (CategoryBudget.month == month) | (CategoryBudget.month == None)
        )
    ).all()

    spending = get_month_spending(db, month)
    progress = []

    for budget in budgets:
        spent = spending.get(budget.category.lower(), 0)
        pct = (spent / budget.budget_amount * 100) if budget.budget_amount > 0 else 0
        progress.append({
            'category': budget.category,
            'budget': budget.budget_amount,
            'spent': spent,
            'pct': pct,
            'remaining': max(0, budget.budget_amount - spent)
        })

    return progress


def count_untagged_transactions(db: Session, month: str) -> int:
    """Count transactions without tags."""
    return db.query(Transaction).filter(
        and_(
            Transaction.month == month,
            Transaction.exclude == False,
            (Transaction.tags == None) | (Transaction.tags == '')
        )
    ).count()


def generate_contextual_tips(db: Session, month: str) -> List[CoachTip]:
    """Generate tips based on current context."""
    tips = []
    spending = get_month_spending(db, month)
    progress = get_budget_progress(db, month)
    untagged = count_untagged_transactions(db, month)

    # Add tips based on budget progress
    for p in progress:
        if p['pct'] > 90:
            tip = TIP_TEMPLATES['high_spending'][0].model_copy()
            tip.message = tip.message.format(category=p['category'], pct=int(p['pct']))
            tip.id = f"hs_{p['category']}"
            tips.append(tip)
        elif p['pct'] < 50 and p['spent'] > 0:
            tip = TIP_TEMPLATES['good_progress'][0].model_copy()
            tip.message = tip.message.format(category=p['category'], pct=int(p['pct']))
            tip.id = f"gp_{p['category']}"
            tips.append(tip)

    # Add tagging tip if many untagged
    if untagged > 5:
        tip = TIP_TEMPLATES['tagging'][1].model_copy()
        tip.message = tip.message.format(untagged=untagged)
        tips.append(tip)

    # Always add some general tips
    general_tips = random.sample(TIP_TEMPLATES['general'], min(2, len(TIP_TEMPLATES['general'])))
    tips.extend(general_tips)

    # Sort by priority and limit
    tips.sort(key=lambda x: x.priority, reverse=True)
    return tips[:5]


def generate_daily_insight(db: Session, month: str) -> DailyInsight:
    """Generate the daily insight message."""
    today = datetime.now()

    # Get spending stats
    spending = get_month_spending(db, month)
    total_spent = sum(spending.values())

    # Get budget total (only for the current month or defaults)
    budgets = db.query(CategoryBudget).filter(
        and_(
            CategoryBudget.is_active == True,
            (CategoryBudget.month == month) | (CategoryBudget.month == None)
        )
    ).all()
    total_budget = sum(b.budget_amount for b in budgets) if budgets else 0

    # Check if budget is meaningfully defined (at least 100€)
    has_budget = total_budget >= 100

    # Select appropriate template based on day
    day_of_month = today.day
    day_of_week = today.weekday()

    # IMPORTANT: If no meaningful budget, show simple spending info (avoid crazy percentages)
    if not has_budget:
        # No budget defined - encourage user to set one
        insight = DailyInsight(
            message=f"Vous avez dépensé {total_spent:.0f}€ ce mois. Définissez un budget pour mieux suivre!",
            emoji="💡",
            data_point=f"Dépenses: {total_spent:.0f}€"
        )
    elif day_of_month <= 5:
        insight = DailyInsight(
            message=f"Début de mois! Votre budget est prêt. Objectif: rester sous {total_budget:.0f}€.",
            emoji="🌟",
            data_point=f"Budget: {total_budget:.0f}€"
        )
    elif day_of_month >= 25:
        remaining = max(0, total_budget - total_spent)
        insight = DailyInsight(
            message=f"Fin de mois! Il vous reste {remaining:.0f}€ sur votre budget.",
            emoji="🏁",
            data_point=f"Reste: {remaining:.0f}€"
        )
    elif day_of_week >= 5:  # Weekend
        # has_budget is True here (checked above), safe to calculate percentage
        pct_used = int(total_spent / total_budget * 100)
        insight = DailyInsight(
            message=f"Week-end! Dépenses actuelles: {total_spent:.0f}€ sur {total_budget:.0f}€ ce mois.",
            emoji="🎉",
            data_point=f"{pct_used}% utilisé"
        )
    else:
        # has_budget is True here (checked above), safe to calculate percentage
        pct_used = int(total_spent / total_budget * 100)
        days_passed = day_of_month
        days_in_month = 30  # Approximation
        pct_month = int(days_passed / days_in_month * 100)

        if pct_used < pct_month - 10:
            insight = DailyInsight(
                message=f"Bravo! Vous êtes sous votre rythme de dépenses habituel.",
                emoji="✨",
                data_point=f"{pct_used}% budget / {pct_month}% mois"
            )
        elif pct_used > pct_month + 10:
            insight = DailyInsight(
                message=f"Attention: vous dépensez un peu plus vite que prévu ce mois.",
                emoji="⚠️",
                data_point=f"{pct_used}% budget / {pct_month}% mois"
            )
        else:
            insight = DailyInsight(
                message=f"Vous êtes dans les temps! {total_spent:.0f}€ dépensés sur {total_budget:.0f}€.",
                emoji="👍",
                data_point=f"{pct_used}% utilisé"
            )

    return insight


def generate_quick_actions(db: Session, month: str) -> List[QuickAction]:
    """Generate contextual quick actions."""
    actions = list(QUICK_ACTIONS_BASE)  # Start with base actions

    # Add contextual action based on untagged count
    untagged = count_untagged_transactions(db, month)
    if untagged > 0:
        actions.insert(0, QuickAction(
            id='qa_tag',
            label=f"Taguer {untagged} transactions",
            action_type='navigate',
            target='/transactions?filter=untagged',
            icon='🏷️'
        ))

    # Add action based on budget warnings
    progress = get_budget_progress(db, month)
    over_budget = [p for p in progress if p['pct'] > 100]
    if over_budget:
        actions.insert(0, QuickAction(
            id='qa_over',
            label=f"{len(over_budget)} catégorie(s) dépassées",
            action_type='navigate',
            target='/analytics?tab=budget',
            icon='🚨'
        ))

    return actions[:4]  # Limit to 4 actions


# Endpoints
@router.get("/dashboard-tips", response_model=DashboardTipsResponse)
async def get_dashboard_tips(
    month: str,
    limit: int = 3,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get rotating tips for the dashboard widget.
    Tips refresh every 30 minutes.
    """
    cache_service = AICacheService(db)
    cache_key = generate_cache_key('coach', 'tips', month, datetime.now().strftime('%Y-%m-%d-%H'))

    # Check cache
    cached = cache_service.get_cached(cache_key, 'coach')
    if cached:
        return DashboardTipsResponse(**cached)

    # Generate new tips
    tips = generate_contextual_tips(db, month)[:limit]

    # Calculate next refresh
    now = datetime.now()
    next_refresh = now + timedelta(minutes=30)

    response = DashboardTipsResponse(
        tips=tips,
        refresh_at=next_refresh.isoformat()
    )

    # Cache result
    cache_service.set_cached(
        cache_key=cache_key,
        cache_type='coach',
        data=response.model_dump(),
        month=month
    )

    return response


@router.get("/daily-insight", response_model=DailyInsightResponse)
async def get_daily_insight(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get the personalized daily insight.
    Refreshes at midnight.
    """
    today = datetime.now()
    month = today.strftime('%Y-%m')

    cache_service = AICacheService(db)
    cache_key = generate_cache_key('coach', 'daily', today.strftime('%Y-%m-%d'))

    # Check cache
    cached = cache_service.get_cached(cache_key, 'daily')
    if cached:
        return DailyInsightResponse(**cached)

    # Generate daily insight
    insight = generate_daily_insight(db, month)

    # Valid until midnight
    tomorrow = (today + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    response = DailyInsightResponse(
        insight=insight,
        valid_until=tomorrow.isoformat()
    )

    # Cache with TTL until midnight
    hours_until_midnight = (tomorrow - today).total_seconds() / 3600
    cache_service.set_cached(
        cache_key=cache_key,
        cache_type='daily',
        data=response.model_dump(),
        ttl_hours=hours_until_midnight,
        month=month
    )

    return response


@router.get("/quick-actions", response_model=QuickActionsResponse)
async def get_quick_actions(
    month: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get contextual quick actions for the dashboard.
    """
    actions = generate_quick_actions(db, month)

    return QuickActionsResponse(actions=actions)


@router.post("/refresh-tips")
async def refresh_tips(
    month: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Force refresh of dashboard tips cache.
    """
    cache_service = AICacheService(db)
    invalidated = cache_service.invalidate(f"coach:tips:{month}%")

    return {"invalidated": invalidated, "message": "Tips cache refreshed"}
