"""
AI Router for Budget Famille v4.0
Provides AI-powered budget analysis endpoints using OpenRouter.

v4.1 additions:
- Streaming chat endpoint via SSE for real-time responses
- Multi-turn chat memory with sessions
"""
import logging
import datetime as dt
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from dependencies.auth import get_current_user
from dependencies.database import get_db
from services.ai_analysis import get_ai_service
from services.chat_memory import get_chat_memory, MessageRole, ChatSession
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
    question: str = Field(..., min_length=3, max_length=5000, description="Question about the budget (can include context)")
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


@router.post("/reload")
def reload_ai_service(
    current_user = Depends(get_current_user)
):
    """
    Force reload of AI service configuration.

    Useful after changing environment variables without restarting the server.
    """
    from services.ai_analysis import reset_ai_service, get_ai_service as get_fresh_service

    # Reset singleton
    reset_ai_service()

    # Get fresh instance
    ai_service = get_fresh_service()

    logger.info(f"AI service reloaded: configured={ai_service.is_configured}, model={ai_service.model}")

    # SECURITE: Ne JAMAIS exposer d'informations sur les cles API
    return {
        "status": "reloaded",
        "configured": ai_service.is_configured,
        "model": ai_service.model
    }


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
    try:
        answer = await ai_service.answer_question(request.question, budget_context)
        logger.info(f"AI answer received, length: {len(answer)}")
    except Exception as e:
        logger.error(f"Error calling AI service: {e}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

    # Return only the user's original question (not the full context)
    # Extract the actual question from the context if present
    original_question = request.question
    if "QUESTION DE L'UTILISATEUR:" in request.question:
        parts = request.question.split("QUESTION DE L'UTILISATEUR:")
        if len(parts) > 1:
            original_question = parts[1].split("INSTRUCTIONS:")[0].strip()

    try:
        response = AIQuestionResponse(
            question=original_question[:500] if len(original_question) > 500 else original_question,
            answer=answer,
            model_used=ai_service.model
        )
        logger.info(f"Returning AI response successfully")
        return response
    except Exception as e:
        logger.error(f"Error creating response: {e}")
        raise HTTPException(status_code=500, detail=f"Response error: {str(e)}")


# =============================================================================
# STREAMING ENDPOINT (v4.1)
# =============================================================================

class AIStreamRequest(BaseModel):
    """Request schema for streaming chat."""
    question: str = Field(..., min_length=3, max_length=5000, description="Question about the budget")
    month: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$", description="Month context")


@router.post("/chat-stream")
async def stream_chat(
    request: AIStreamRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stream an AI response to a budget question using Server-Sent Events.

    Returns a streaming response where each chunk is a portion of the AI's answer.
    The frontend should consume this using EventSource or fetch with readable streams.
    """
    logger.info(f"AI streaming chat from {current_user.username}: {request.question[:50]}...")

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

    async def event_generator():
        """Generate SSE events from AI stream."""
        try:
            async for chunk in ai_service.stream_answer(request.question, budget_context):
                # Format as SSE event
                yield f"data: {chunk}\n\n"

            # Send completion marker
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: [ERROR: {str(e)}]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# =============================================================================
# MULTI-TURN CHAT SESSIONS (v4.1)
# =============================================================================

class ChatSessionCreateRequest(BaseModel):
    """Request to create a new chat session."""
    month: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$", description="Month context")


class ChatSessionResponse(BaseModel):
    """Response with session details."""
    session_id: str
    user_id: str
    created_at: str
    updated_at: str
    message_count: int
    has_context: bool


class SessionChatRequest(BaseModel):
    """Request to chat within a session."""
    question: str = Field(..., min_length=3, max_length=5000, description="Question about the budget")
    month: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$", description="Month context")


class SessionChatResponse(BaseModel):
    """Response from session chat."""
    session_id: str
    question: str
    answer: str
    message_count: int
    model_used: str


class ChatHistoryResponse(BaseModel):
    """Response with chat history."""
    session_id: str
    messages: List[Dict[str, Any]]
    message_count: int


def _build_financial_context(db: Session, month: str) -> Dict[str, Any]:
    """Build financial context from transactions."""
    transactions = db.query(Transaction).filter(
        Transaction.month == month,
        Transaction.exclude == False
    ).all()

    total_income = sum(abs(tx.amount) for tx in transactions if tx.amount > 0)
    total_expenses = sum(abs(tx.amount) for tx in transactions if tx.amount < 0)

    # Category breakdown
    categories: Dict[str, float] = {}
    for tx in transactions:
        if tx.amount >= 0:
            continue
        tags = [t.strip().lower() for t in (tx.tags or "").split(",") if t.strip()]
        if not tags:
            tags = [tx.category.lower()] if tx.category else ["non-categorise"]
        for tag in tags:
            categories[tag] = categories.get(tag, 0) + abs(tx.amount)

    # Top categories
    top_categories = [
        {"name": k, "amount": v}
        for k, v in sorted(categories.items(), key=lambda x: x[1], reverse=True)
    ][:5]

    # Calculate budget status
    savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0
    if savings_rate < 0:
        budget_status = "deficitaire"
    elif savings_rate < 10:
        budget_status = "serre"
    elif savings_rate > 30:
        budget_status = "excellent"
    elif savings_rate > 20:
        budget_status = "bon"
    else:
        budget_status = "equilibre"

    return {
        "month": month,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "savings": total_income - total_expenses,
        "transaction_count": len(transactions),
        "budget_status": budget_status,
        "top_categories": top_categories,
        "categories": categories
    }


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    request: ChatSessionCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new chat session with conversation memory.

    Sessions persist for 30 minutes and store up to 10 messages.
    """
    memory = get_chat_memory()
    month = request.month or dt.datetime.now().strftime("%Y-%m")

    # Build financial context
    financial_context = _build_financial_context(db, month)

    # Create session
    session = memory.create_session(
        user_id=current_user.username,
        financial_context=financial_context,
        metadata={"created_from": "api", "month": month}
    )

    logger.info(f"Created chat session {session.session_id} for {current_user.username}")

    return ChatSessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(session.messages),
        has_context=session.financial_context is not None
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    current_user=Depends(get_current_user)
):
    """
    List all active chat sessions for the current user.
    """
    memory = get_chat_memory()
    session_ids = memory.list_user_sessions(current_user.username)

    sessions = []
    for sid in session_ids:
        session = memory.get_session(current_user.username, sid)
        if session:
            sessions.append(ChatSessionResponse(
                session_id=session.session_id,
                user_id=session.user_id,
                created_at=session.created_at,
                updated_at=session.updated_at,
                message_count=len(session.messages),
                has_context=session.financial_context is not None
            ))

    return sessions


@router.get("/sessions/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    current_user=Depends(get_current_user)
):
    """
    Get chat history for a specific session.
    """
    memory = get_chat_memory()
    session = memory.get_session(current_user.username, session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return ChatHistoryResponse(
        session_id=session.session_id,
        messages=[m.to_dict() for m in session.messages],
        message_count=len(session.messages)
    )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user=Depends(get_current_user)
):
    """
    Delete a chat session.
    """
    memory = get_chat_memory()

    if not memory.get_session(current_user.username, session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    memory.delete_session(current_user.username, session_id)

    return {"status": "deleted", "session_id": session_id}


@router.post("/sessions/{session_id}/chat", response_model=SessionChatResponse)
async def session_chat(
    session_id: str,
    request: SessionChatRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat within a session with conversation memory.

    The AI will remember previous messages in the session for context.
    """
    memory = get_chat_memory()
    ai_service = get_ai_service()

    if not ai_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Set OPENROUTER_API_KEY environment variable."
        )

    # Get or create session
    month = request.month or dt.datetime.now().strftime("%Y-%m")
    session = memory.get_or_create_session(
        user_id=current_user.username,
        session_id=session_id,
        financial_context=_build_financial_context(db, month)
    )

    # Add user message to history
    memory.add_user_message(current_user.username, session.session_id, request.question)

    # Build context with conversation history
    system_prompt, messages = memory.build_llm_context(
        user_id=current_user.username,
        session_id=session.session_id,
        current_question=request.question,
        financial_context=session.financial_context
    )

    # Get AI answer
    try:
        # Combine system prompt with question for the existing answer_question method
        full_prompt = f"{system_prompt}\n\nQUESTION:\n{request.question}"
        answer = await ai_service.answer_question(full_prompt, session.financial_context or {})

        # Save assistant response to history
        memory.add_assistant_message(current_user.username, session.session_id, answer)

        # Get updated session
        updated_session = memory.get_session(current_user.username, session.session_id)

        return SessionChatResponse(
            session_id=session.session_id,
            question=request.question,
            answer=answer,
            message_count=len(updated_session.messages) if updated_session else 0,
            model_used=ai_service.model
        )

    except Exception as e:
        logger.error(f"Error in session chat: {e}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


@router.post("/sessions/{session_id}/chat-stream")
async def session_chat_stream(
    session_id: str,
    request: SessionChatRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stream chat response within a session with conversation memory.

    Uses Server-Sent Events for real-time streaming.
    """
    memory = get_chat_memory()
    ai_service = get_ai_service()

    if not ai_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Set OPENROUTER_API_KEY environment variable."
        )

    # Get or create session
    month = request.month or dt.datetime.now().strftime("%Y-%m")
    session = memory.get_or_create_session(
        user_id=current_user.username,
        session_id=session_id,
        financial_context=_build_financial_context(db, month)
    )

    # Add user message to history
    memory.add_user_message(current_user.username, session.session_id, request.question)

    # Build context with conversation history
    system_prompt, messages = memory.build_llm_context(
        user_id=current_user.username,
        session_id=session.session_id,
        current_question=request.question,
        financial_context=session.financial_context
    )

    async def event_generator():
        """Generate SSE events from AI stream with session context."""
        full_response = ""
        try:
            # Stream the response
            full_prompt = f"{system_prompt}\n\nQUESTION:\n{request.question}"
            async for chunk in ai_service.stream_answer(full_prompt, session.financial_context or {}):
                full_response += chunk
                yield f"data: {chunk}\n\n"

            # Save the complete response to session history
            memory.add_assistant_message(current_user.username, session.session_id, full_response)

            # Send completion marker with session info
            yield f"data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Streaming error in session: {e}")
            yield f"data: [ERROR: {str(e)}]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.delete("/sessions")
async def clear_all_sessions(
    current_user=Depends(get_current_user)
):
    """
    Clear all chat sessions for the current user.
    """
    memory = get_chat_memory()
    count = memory.clear_user_sessions(current_user.username)

    return {"status": "cleared", "sessions_deleted": count}


@router.get("/sessions/active", response_model=Optional[ChatSessionResponse])
async def get_active_session(
    current_user=Depends(get_current_user)
):
    """
    Get the most recent active session, if any.
    """
    memory = get_chat_memory()
    session = memory.get_active_session(current_user.username)

    if not session:
        return None

    return ChatSessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(session.messages),
        has_context=session.financial_context is not None
    )
