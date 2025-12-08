"""
AI Router for Budget Famille v4.0
Provides AI-powered budget analysis endpoints using OpenRouter.
"""
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from dependencies.auth import get_current_user
from dependencies.database import get_db
from services.ai_analysis import get_ai_service
from models.database import Transaction, CategoryBudget

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai",
    tags=["ai-analysis"],
    responses={
        404: {"description": "Not found"},
        503: {"description": "AI service unavailable"}
    }
)


# Request/Response Schemas

class AIExplanationRequest(BaseModel):
    """Request schema for AI variance explanation."""
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Month in YYYY-MM format")


class AIExplanationResponse(BaseModel):
    """Response schema for AI explanations."""
    explanation: str = Field(description="AI-generated explanation")
    model_used: str = Field(description="AI model that generated the response")
    language: str = Field(description="Language of the response")


class AISavingsRequest(BaseModel):
    """Request schema for savings suggestions."""
    category: str = Field(..., min_length=1, description="Category to analyze")
    months_history: int = Field(default=6, ge=1, le=12, description="Months of history to analyze")


class AISavingsResponse(BaseModel):
    """Response schema for savings suggestions."""
    category: str
    suggestions: str = Field(description="AI-generated savings suggestions")
    average_spending: float = Field(description="Average monthly spending in this category")
    model_used: str


class AIMonthlySummaryRequest(BaseModel):
    """Request schema for monthly summary."""
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Month in YYYY-MM format")


class AIMonthlySummaryResponse(BaseModel):
    """Response schema for monthly summary."""
    month: str
    summary: str = Field(description="AI-generated monthly summary")
    income: float
    expenses: float
    savings: float
    model_used: str


class AIQuestionRequest(BaseModel):
    """Request schema for free-form questions."""
    question: str = Field(..., min_length=5, max_length=500, description="Question about the budget")
    month: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$", description="Month context")


class AIQuestionResponse(BaseModel):
    """Response schema for Q&A."""
    question: str
    answer: str
    model_used: str


class AIStatusResponse(BaseModel):
    """Response schema for AI service status."""
    configured: bool
    model: str
    language: str
    max_tokens: int


# Endpoints

@router.get("/status", response_model=AIStatusResponse)
def get_ai_status(
    current_user = Depends(get_current_user)
):
    """
    Get AI service configuration status.

    Returns whether the service is configured and which model is being used.
    """
    ai_service = get_ai_service()

    return AIStatusResponse(
        configured=ai_service.is_configured,
        model=ai_service.model,
        language=ai_service.language,
        max_tokens=ai_service.max_tokens
    )


@router.post("/explain-variance", response_model=AIExplanationResponse)
async def explain_variance(
    request: AIExplanationRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate an AI explanation of budget variances for a given month.

    Requires category budgets to be set up for meaningful analysis.
    """
    logger.info(f"AI variance explanation requested for {request.month} by {current_user.username}")

    ai_service = get_ai_service()

    if not ai_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Set OPENROUTER_API_KEY environment variable."
        )

    # Get variance data by calling the analytics endpoint logic
    from routers.analytics import get_variance_analysis

    try:
        variance_data = get_variance_analysis(
            month=request.month,
            current_user=current_user,
            db=db
        )
        variance_dict = variance_data.model_dump()
    except Exception as e:
        logger.error(f"Error getting variance data: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting variance data: {str(e)}")

    # Generate AI explanation
    explanation = await ai_service.explain_variance(variance_dict)

    return AIExplanationResponse(
        explanation=explanation,
        model_used=ai_service.model,
        language=ai_service.language
    )


@router.post("/suggest-savings", response_model=AISavingsResponse)
async def suggest_savings(
    request: AISavingsRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered savings suggestions for a specific category.

    Analyzes spending history to provide personalized recommendations.
    """
    logger.info(f"AI savings suggestions for '{request.category}' requested by {current_user.username}")

    ai_service = get_ai_service()

    if not ai_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Set OPENROUTER_API_KEY environment variable."
        )

    # Get spending history for the category
    import datetime as dt
    from dateutil.relativedelta import relativedelta

    today = dt.datetime.now()
    months_data = []
    total_spending = 0

    for i in range(request.months_history):
        month_date = today - relativedelta(months=i)
        month_str = month_date.strftime("%Y-%m")

        # Get transactions for this month and category
        transactions = db.query(Transaction).filter(
            Transaction.month == month_str,
            Transaction.amount < 0,
            Transaction.exclude == False
        ).all()

        # Filter by tag/category
        category_lower = request.category.lower()
        month_amount = 0
        month_transactions = []

        for tx in transactions:
            tags = [t.strip().lower() for t in (tx.tags or "").split(",") if t.strip()]
            if not tags:
                tags = [tx.category.lower()] if tx.category else []

            if category_lower in tags:
                month_amount += abs(tx.amount)
                month_transactions.append({
                    "label": tx.label,
                    "amount": abs(tx.amount),
                    "date": tx.date_op.isoformat() if tx.date_op else None
                })

        months_data.append({
            "month": month_str,
            "amount": month_amount,
            "transactions": month_transactions
        })
        total_spending += month_amount

    avg_spending = total_spending / request.months_history if request.months_history > 0 else 0

    # Generate AI suggestions
    suggestions = await ai_service.suggest_savings(request.category, months_data)

    return AISavingsResponse(
        category=request.category,
        suggestions=suggestions,
        average_spending=round(avg_spending, 2),
        model_used=ai_service.model
    )


@router.post("/monthly-summary", response_model=AIMonthlySummaryResponse)
async def generate_monthly_summary(
    request: AIMonthlySummaryRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate an AI-powered intelligent monthly summary.

    Provides an engaging narrative of the month's financial activity.
    """
    logger.info(f"AI monthly summary for {request.month} requested by {current_user.username}")

    ai_service = get_ai_service()

    if not ai_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Set OPENROUTER_API_KEY environment variable."
        )

    # Get month data
    transactions = db.query(Transaction).filter(
        Transaction.month == request.month,
        Transaction.exclude == False
    ).all()

    income = sum(abs(tx.amount) for tx in transactions if tx.amount > 0)
    expenses = sum(abs(tx.amount) for tx in transactions if tx.amount < 0)
    savings = income - expenses

    # Calculate category breakdown
    category_spending = {}
    for tx in transactions:
        if tx.amount >= 0:
            continue

        tags = [t.strip().lower() for t in (tx.tags or "").split(",") if t.strip()]
        if not tags:
            tags = [tx.category.lower()] if tx.category else ["non-categorise"]

        for tag in tags:
            if tag not in category_spending:
                category_spending[tag] = 0
            category_spending[tag] += abs(tx.amount)

    # Sort by amount
    top_categories = [
        {"name": k, "amount": v}
        for k, v in sorted(category_spending.items(), key=lambda x: x[1], reverse=True)
    ][:5]

    # Build month data
    month_data = {
        "month": request.month,
        "income": income,
        "expenses": expenses,
        "savings": savings,
        "top_categories": top_categories,
        "anomalies": []  # Could be enhanced with anomaly detection
    }

    # Generate AI summary
    summary = await ai_service.monthly_summary(month_data)

    return AIMonthlySummaryResponse(
        month=request.month,
        summary=summary,
        income=round(income, 2),
        expenses=round(expenses, 2),
        savings=round(savings, 2),
        model_used=ai_service.model
    )


@router.post("/chat", response_model=AIQuestionResponse)
async def ask_question(
    request: AIQuestionRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ask a free-form question about your budget.

    The AI will answer based on your transaction data.
    """
    logger.info(f"AI question from {current_user.username}: {request.question[:50]}...")

    ai_service = get_ai_service()

    if not ai_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Set OPENROUTER_API_KEY environment variable."
        )

    # Determine month context
    import datetime as dt
    month = request.month or dt.datetime.now().strftime("%Y-%m")

    # Get transactions for context
    transactions = db.query(Transaction).filter(
        Transaction.month == month,
        Transaction.exclude == False
    ).all()

    total_income = sum(abs(tx.amount) for tx in transactions if tx.amount > 0)
    total_expenses = sum(abs(tx.amount) for tx in transactions if tx.amount < 0)

    # Category breakdown
    categories = {}
    for tx in transactions:
        if tx.amount >= 0:
            continue

        tags = [t.strip().lower() for t in (tx.tags or "").split(",") if t.strip()]
        if not tags:
            tags = [tx.category.lower()] if tx.category else ["non-categorise"]

        for tag in tags:
            if tag not in categories:
                categories[tag] = 0
            categories[tag] += abs(tx.amount)

    # Build context
    budget_context = {
        "month": month,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "categories": categories
    }

    # Get AI answer
    answer = await ai_service.answer_question(request.question, budget_context)

    return AIQuestionResponse(
        question=request.question,
        answer=answer,
        model_used=ai_service.model
    )
