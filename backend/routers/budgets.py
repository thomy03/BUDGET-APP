"""
Budgets router for Budget Famille v4.0
Handles category/tag budget management and suggestions
"""
import logging
from typing import List, Optional
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from dependencies.auth import get_current_user
from dependencies.database import get_db
from audit_logger import get_audit_logger, AuditEventType

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/budgets",
    tags=["budgets"],
    responses={404: {"description": "Not found"}}
)

# Import models and schemas
from models.database import CategoryBudget, Transaction
from models.schemas import (
    CategoryBudgetCreate,
    CategoryBudgetUpdate,
    CategoryBudgetResponse,
    CategoryBudgetSuggestion,
    BudgetSuggestionsResponse
)


@router.get("/categories", response_model=List[CategoryBudgetResponse])
def list_category_budgets(
    month: Optional[str] = None,
    active_only: bool = True,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all category budgets.

    - If month is provided, returns budgets specific to that month + default budgets
    - If month is None, returns all budgets
    - active_only=True filters to only active budgets
    """
    logger.info(f"Liste budgets categories demandee par: {current_user.username}, month={month}")

    query = db.query(CategoryBudget)

    if active_only:
        query = query.filter(CategoryBudget.is_active == True)

    if month:
        # Get budgets for specific month OR default budgets (month is NULL)
        query = query.filter(
            (CategoryBudget.month == month) | (CategoryBudget.month == None)
        )

    budgets = query.order_by(CategoryBudget.category).all()

    return budgets


@router.post("/categories", response_model=CategoryBudgetResponse, status_code=status.HTTP_201_CREATED)
def create_category_budget(
    payload: CategoryBudgetCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new budget target for a category or tag"""
    audit_logger = get_audit_logger()
    logger.info(f"Creation budget categorie '{payload.category}' par: {current_user.username}")

    # Check for duplicates (same category + month combination)
    existing = db.query(CategoryBudget).filter(
        CategoryBudget.category == payload.category.lower(),
        CategoryBudget.month == payload.month,
        CategoryBudget.is_active == True
    ).first()

    if existing:
        month_str = payload.month or "default"
        raise HTTPException(
            status_code=400,
            detail=f"Un budget pour '{payload.category}' existe deja pour {month_str}"
        )

    # Create the budget
    budget = CategoryBudget(
        category=payload.category.lower(),
        tag_name=payload.tag_name.lower() if payload.tag_name else None,
        month=payload.month,
        budget_amount=payload.budget_amount,
        alert_threshold=payload.alert_threshold,
        notes=payload.notes,
        created_by=current_user.username
    )

    db.add(budget)
    db.commit()
    db.refresh(budget)

    # Audit log
    audit_logger.log_event(
        AuditEventType.CONFIG_UPDATE,
        username=current_user.username,
        details={"budget_category": payload.category, "amount": payload.budget_amount, "action": "create"},
        success=True
    )

    logger.info(f"Budget categorie cree avec ID: {budget.id}")
    return budget


@router.get("/categories/{budget_id}", response_model=CategoryBudgetResponse)
def get_category_budget(
    budget_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific category budget by ID"""
    budget = db.query(CategoryBudget).filter(CategoryBudget.id == budget_id).first()

    if not budget:
        raise HTTPException(status_code=404, detail=f"Budget {budget_id} non trouve")

    return budget


@router.put("/categories/{budget_id}", response_model=CategoryBudgetResponse)
def update_category_budget(
    budget_id: int,
    payload: CategoryBudgetUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing category budget"""
    audit_logger = get_audit_logger()
    logger.info(f"Modification budget ID {budget_id} par: {current_user.username}")

    budget = db.query(CategoryBudget).filter(CategoryBudget.id == budget_id).first()

    if not budget:
        raise HTTPException(status_code=404, detail=f"Budget {budget_id} non trouve")

    # Check for duplicate if category/month changed
    update_data = payload.model_dump(exclude_unset=True)
    new_category = update_data.get('category', budget.category)
    new_month = update_data.get('month', budget.month)

    if new_category != budget.category or new_month != budget.month:
        existing = db.query(CategoryBudget).filter(
            CategoryBudget.category == new_category.lower() if new_category else budget.category,
            CategoryBudget.month == new_month,
            CategoryBudget.id != budget_id,
            CategoryBudget.is_active == True
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Un budget pour cette categorie/mois existe deja"
            )

    # Update fields
    for field, value in update_data.items():
        if field == 'category' and value:
            value = value.lower()
        elif field == 'tag_name' and value:
            value = value.lower()
        setattr(budget, field, value)

    db.commit()
    db.refresh(budget)

    # Audit log
    audit_logger.log_event(
        AuditEventType.CONFIG_UPDATE,
        username=current_user.username,
        details={"budget_id": budget_id, "action": "update"},
        success=True
    )

    logger.info(f"Budget {budget_id} mis a jour")
    return budget


@router.delete("/categories/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category_budget(
    budget_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a category budget"""
    audit_logger = get_audit_logger()
    logger.info(f"Suppression budget ID {budget_id} par: {current_user.username}")

    budget = db.query(CategoryBudget).filter(CategoryBudget.id == budget_id).first()

    if not budget:
        raise HTTPException(status_code=404, detail=f"Budget {budget_id} non trouve")

    category_name = budget.category
    db.delete(budget)
    db.commit()

    # Audit log
    audit_logger.log_event(
        AuditEventType.CONFIG_UPDATE,
        username=current_user.username,
        details={"budget_id": budget_id, "category": category_name, "action": "delete"},
        success=True
    )

    logger.info(f"Budget '{category_name}' (ID {budget_id}) supprime")
    return


@router.get("/suggestions", response_model=BudgetSuggestionsResponse)
def get_budget_suggestions(
    months_history: int = 6,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get budget suggestions based on historical spending.

    Analyzes the last N months of transactions to suggest budget amounts
    for each category/tag.
    """
    logger.info(f"Calcul suggestions budget par: {current_user.username}, historique={months_history} mois")

    # Calculate date range
    today = datetime.now()
    end_month = today.strftime("%Y-%m")
    start_date = today - relativedelta(months=months_history)
    start_month = start_date.strftime("%Y-%m")

    # Get all transactions in the date range, grouped by tag
    # Only expenses (amount < 0), not excluded
    transactions = db.query(Transaction).filter(
        Transaction.month >= start_month,
        Transaction.month <= end_month,
        Transaction.amount < 0,
        Transaction.exclude == False
    ).all()

    # Group by tag and month
    tag_monthly_spending = {}  # {tag: {month: total}}

    for tx in transactions:
        # Use tags if available, otherwise use category
        tags = [t.strip().lower() for t in (tx.tags or "").split(",") if t.strip()]
        if not tags:
            tags = [tx.category.lower()] if tx.category else ["non-categorise"]

        for tag in tags:
            if tag not in tag_monthly_spending:
                tag_monthly_spending[tag] = {}

            month = tx.month
            if month not in tag_monthly_spending[tag]:
                tag_monthly_spending[tag][month] = 0

            tag_monthly_spending[tag][month] += abs(tx.amount)

    # Calculate suggestions for each tag
    suggestions = []
    total_suggested = 0

    for tag, monthly_data in tag_monthly_spending.items():
        if not monthly_data:
            continue

        amounts = list(monthly_data.values())
        months_with_data = len(amounts)

        # Calculate averages
        avg_all = sum(amounts) / len(amounts) if amounts else 0

        # Get last 3 months specifically
        sorted_months = sorted(monthly_data.keys(), reverse=True)
        last_3_months = sorted_months[:3]
        avg_3_months = sum(monthly_data.get(m, 0) for m in last_3_months) / min(3, len(last_3_months))

        last_6_months = sorted_months[:6]
        avg_6_months = sum(monthly_data.get(m, 0) for m in last_6_months) / min(6, len(last_6_months))

        # Determine trend
        if len(amounts) >= 2:
            recent_avg = sum(amounts[:min(3, len(amounts))]) / min(3, len(amounts))
            older_avg = sum(amounts[min(3, len(amounts)):]) / max(1, len(amounts) - min(3, len(amounts)))

            if older_avg > 0:
                change_pct = (recent_avg - older_avg) / older_avg * 100
                if change_pct > 10:
                    trend = "increasing"
                elif change_pct < -10:
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Suggested amount: use 3-month average, rounded to nearest 10
        suggested = round(avg_3_months / 10) * 10
        if suggested < 10:
            suggested = round(avg_3_months)

        suggestion = CategoryBudgetSuggestion(
            category=tag,
            suggested_amount=round(suggested, 2),
            average_3_months=round(avg_3_months, 2),
            average_6_months=round(avg_6_months, 2),
            min_amount=round(min(amounts), 2),
            max_amount=round(max(amounts), 2),
            months_with_data=months_with_data,
            trend=trend
        )

        suggestions.append(suggestion)
        total_suggested += suggested

    # Sort by suggested amount (highest first)
    suggestions.sort(key=lambda x: x.suggested_amount, reverse=True)

    return BudgetSuggestionsResponse(
        suggestions=suggestions,
        total_suggested_budget=round(total_suggested, 2),
        analysis_period_start=start_month,
        analysis_period_end=end_month
    )


@router.post("/bulk-create", response_model=List[CategoryBudgetResponse])
def bulk_create_budgets(
    budgets: List[CategoryBudgetCreate],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create multiple category budgets at once"""
    audit_logger = get_audit_logger()
    logger.info(f"Creation en masse de {len(budgets)} budgets par: {current_user.username}")

    created_budgets = []
    errors = []

    for i, payload in enumerate(budgets):
        try:
            # Check for duplicates
            existing = db.query(CategoryBudget).filter(
                CategoryBudget.category == payload.category.lower(),
                CategoryBudget.month == payload.month,
                CategoryBudget.is_active == True
            ).first()

            if existing:
                errors.append(f"Budget pour '{payload.category}' ({payload.month or 'default'}) existe deja")
                continue

            budget = CategoryBudget(
                category=payload.category.lower(),
                tag_name=payload.tag_name.lower() if payload.tag_name else None,
                month=payload.month,
                budget_amount=payload.budget_amount,
                alert_threshold=payload.alert_threshold,
                notes=payload.notes,
                created_by=current_user.username
            )

            db.add(budget)
            created_budgets.append(budget)

        except Exception as e:
            errors.append(f"Erreur pour '{payload.category}': {str(e)}")

    if created_budgets:
        db.commit()
        for budget in created_budgets:
            db.refresh(budget)

    # Audit log
    audit_logger.log_event(
        AuditEventType.CONFIG_UPDATE,
        username=current_user.username,
        details={
            "action": "bulk_create",
            "created_count": len(created_budgets),
            "error_count": len(errors)
        },
        success=len(created_budgets) > 0
    )

    if errors:
        logger.warning(f"Erreurs lors de la creation en masse: {errors}")

    logger.info(f"{len(created_budgets)} budgets crees avec succes")
    return created_budgets


@router.post("/apply-suggestions", response_model=List[CategoryBudgetResponse])
def apply_budget_suggestions(
    month: str,
    min_amount: float = 50,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply budget suggestions for a specific month.

    Creates budgets based on historical analysis for categories
    that don't already have a budget set.

    - month: Target month (YYYY-MM)
    - min_amount: Minimum suggested amount to create a budget (default 50)
    """
    audit_logger = get_audit_logger()
    logger.info(f"Application suggestions pour {month} par: {current_user.username}")

    # Get existing budgets for this month
    existing_categories = set(
        b.category for b in db.query(CategoryBudget).filter(
            (CategoryBudget.month == month) | (CategoryBudget.month == None),
            CategoryBudget.is_active == True
        ).all()
    )

    # Get suggestions
    suggestions_response = get_budget_suggestions(
        months_history=6,
        current_user=current_user,
        db=db
    )

    created_budgets = []

    for suggestion in suggestions_response.suggestions:
        # Skip if already has budget or amount too low
        if suggestion.category in existing_categories:
            continue
        if suggestion.suggested_amount < min_amount:
            continue

        budget = CategoryBudget(
            category=suggestion.category,
            tag_name=None,
            month=month,
            budget_amount=suggestion.suggested_amount,
            alert_threshold=0.8,
            notes=f"Auto-genere depuis historique ({suggestion.months_with_data} mois)",
            created_by=current_user.username
        )

        db.add(budget)
        created_budgets.append(budget)

    if created_budgets:
        db.commit()
        for budget in created_budgets:
            db.refresh(budget)

    # Audit log
    audit_logger.log_event(
        AuditEventType.CONFIG_UPDATE,
        username=current_user.username,
        details={
            "action": "apply_suggestions",
            "month": month,
            "created_count": len(created_budgets)
        },
        success=True
    )

    logger.info(f"{len(created_budgets)} budgets crees depuis suggestions pour {month}")
    return created_budgets
