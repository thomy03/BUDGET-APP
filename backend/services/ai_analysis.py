"""
AI Analysis Service for Budget Famille v4.0
Integrates with OpenRouter for intelligent budget explanations and suggestions.

Supports multiple LLM providers through OpenRouter's unified API:
- DeepSeek V3.2 (recommended for international use)
- Mistral 8B (economical, excellent for French)
- Claude Haiku (higher quality but more expensive)

v4.1 additions:
- Streaming responses via SSE for better UX
- Redis caching for AI responses (configurable TTLs)
"""
import os
import logging
import httpx
import json
import hashlib
from typing import Dict, Any, Optional, List, AsyncGenerator

# Ensure environment variables are loaded before anything else
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Redis cache integration
_cache_service = None

def get_cache_service():
    """Lazy load cache service to avoid circular imports"""
    global _cache_service
    if _cache_service is None:
        try:
            from services.redis_cache import get_redis_cache
            _cache_service = get_redis_cache()
            logger.info("AI cache service initialized")
        except Exception as e:
            logger.warning(f"Could not initialize cache for AI service: {e}")
            _cache_service = None
    return _cache_service


def _make_cache_key(prefix: str, *args) -> str:
    """Generate a cache key from prefix and arguments"""
    # Hash long arguments to keep keys manageable
    content = ":".join(str(arg)[:100] for arg in args)
    content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
    return f"ai:{prefix}:{content_hash}"


class AIAnalysisService:
    """
    Service for AI-powered budget analysis and explanations.

    Uses OpenRouter API to access various LLM models for:
    - Variance explanation
    - Savings suggestions
    - Monthly summaries
    - Q&A about budget data
    """

    DEFAULT_MODEL = "deepseek/deepseek-chat"  # DeepSeek V3.2 - excellent multilingual
    FALLBACK_MODEL = "mistralai/ministral-8b-2412"  # Mistral 8B - economical

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7
    ):
        """
        Initialize the AI Analysis Service.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            model: Model to use (defaults to DeepSeek V3.2)
            max_tokens: Maximum response tokens
            temperature: Creativity level (0-1)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("OPENROUTER_MODEL", self.DEFAULT_MODEL)
        self.max_tokens = int(os.getenv("AI_MAX_TOKENS", max_tokens))
        self.temperature = float(os.getenv("AI_TEMPERATURE", temperature))
        self.base_url = "https://openrouter.ai/api/v1"

        # Detect language preference
        self.language = os.getenv("AI_LANGUAGE", "fr")  # fr, en, es, de, etc.

        # Cache configuration
        self.cache_enabled = os.getenv("AI_CACHE_ENABLED", "true").lower() == "true"
        self.cache_ttl_variance = int(os.getenv("AI_CACHE_TTL_VARIANCE", 300))  # 5 min
        self.cache_ttl_summary = int(os.getenv("AI_CACHE_TTL_SUMMARY", 900))  # 15 min
        self.cache_ttl_savings = int(os.getenv("AI_CACHE_TTL_SAVINGS", 600))  # 10 min
        self.cache_ttl_answer = int(os.getenv("AI_CACHE_TTL_ANSWER", 180))  # 3 min

        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set - AI features will be disabled")

    @property
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return bool(self.api_key)

    async def _call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Call the OpenRouter API with the given prompt.

        Args:
            prompt: User message/prompt
            system_prompt: Optional system message for context

        Returns:
            LLM response text
        """
        if not self.is_configured:
            return "Service IA non configure. Veuillez definir OPENROUTER_API_KEY."

        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": "https://budget-famille.app",
                        "X-Title": "Budget Famille"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_msg = f"OpenRouter API error: {response.status_code}"
                    logger.error(f"{error_msg} - {response.text}")

                    # Try fallback model
                    if self.model != self.FALLBACK_MODEL:
                        logger.info(f"Trying fallback model: {self.FALLBACK_MODEL}")
                        self.model = self.FALLBACK_MODEL
                        return await self._call_llm(prompt, system_prompt)

                    return f"Erreur API: {error_msg}"

        except httpx.TimeoutException:
            logger.error("OpenRouter API timeout")
            return "Le service IA n'a pas repondu a temps. Veuillez reessayer."
        except Exception as e:
            logger.error(f"OpenRouter API exception: {str(e)}")
            return f"Erreur lors de l'appel au service IA: {str(e)}"

    async def _stream_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream responses from OpenRouter API using SSE.

        Args:
            prompt: User message/prompt
            system_prompt: Optional system message for context

        Yields:
            Chunks of the LLM response as they arrive
        """
        if not self.is_configured:
            yield "Service IA non configure. Veuillez definir OPENROUTER_API_KEY."
            return

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": "https://budget-famille.app",
                        "X-Title": "Budget Famille",
                        "Accept": "text/event-stream"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                        "stream": True
                    }
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"OpenRouter streaming error: {response.status_code} - {error_text}")
                        yield f"Erreur API: {response.status_code}"
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        # Skip non-data lines
                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:]  # Remove "data: " prefix

                        # Check for stream end
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            # Skip malformed JSON lines
                            continue

        except httpx.TimeoutException:
            logger.error("OpenRouter streaming timeout")
            yield "\n[Timeout - reponse incomplete]"
        except Exception as e:
            logger.error(f"OpenRouter streaming exception: {str(e)}")
            yield f"\n[Erreur: {str(e)}]"

    async def stream_answer(
        self,
        question: str,
        budget_context: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """
        Stream an answer to a budget question.

        Args:
            question: User's question
            budget_context: Relevant budget data for context

        Yields:
            Chunks of the AI answer as they arrive
        """
        # Build context summary
        month = budget_context.get("month", "current")
        total_expenses = budget_context.get("total_expenses", 0)
        total_income = budget_context.get("total_income", 0)
        categories = budget_context.get("categories", {})

        if self.language == "fr":
            context_text = f"""Contexte budget ({month}):
- Revenus: {total_income:.0f}EUR
- Depenses totales: {total_expenses:.0f}EUR
- Solde: {total_income - total_expenses:.0f}EUR

Depenses par categorie:
"""
        else:
            context_text = f"""Budget context ({month}):
- Income: {total_income:.0f}EUR
- Total expenses: {total_expenses:.0f}EUR
- Balance: {total_income - total_expenses:.0f}EUR

Expenses by category:
"""

        for cat, amount in list(categories.items())[:10]:
            context_text += f"- {cat}: {amount:.0f}EUR\n"

        prompt = f"""{context_text}

Question: {question}

Reponds de facon concise et utile.""" if self.language == "fr" else f"""{context_text}

Question: {question}

Answer concisely and helpfully."""

        async for chunk in self._stream_llm(prompt, self._get_system_prompt("general")):
            yield chunk

    def _get_system_prompt(self, context: str = "general") -> str:
        """Get the appropriate system prompt based on context and language."""
        prompts = {
            "fr": {
                "general": """Tu es un conseiller budget familial expert et bienveillant.
Tu aides les familles a mieux gerer leur argent de facon simple et concrete.
Tes reponses sont courtes, claires et encourageantes.
Tu donnes des conseils pratiques et actionnables.""",
                "variance": """Tu es un analyste budget expert.
Tu expliques les ecarts budgetaires de facon simple et comprehensible.
Tu identifies les causes principales et proposes des solutions concretes.
Sois direct et constructif, pas moralisateur.""",
                "savings": """Tu es un expert en gestion financiere familiale.
Tu proposes des moyens concrets et realistes de reduire les depenses.
Tes suggestions sont pratiques et adaptees a la vie quotidienne.
Evite les conseils generiques, sois specifique.""",
                "summary": """Tu es un coach budget familial.
Tu fais des bilans mensuels engageants et constructifs.
Tu soulignes les points positifs tout en identifiant les axes d'amelioration.
Commence par un emoji adapte au contexte."""
            },
            "en": {
                "general": """You are an expert and caring family budget advisor.
You help families manage their money better in a simple and practical way.
Your responses are short, clear and encouraging.
You give practical and actionable advice.""",
                "variance": """You are an expert budget analyst.
You explain budget variances in a simple and understandable way.
You identify the main causes and propose concrete solutions.
Be direct and constructive, not preachy.""",
                "savings": """You are an expert in family financial management.
You propose concrete and realistic ways to reduce expenses.
Your suggestions are practical and adapted to daily life.
Avoid generic advice, be specific.""",
                "summary": """You are a family budget coach.
You make engaging and constructive monthly reviews.
You highlight the positives while identifying areas for improvement.
Start with an emoji appropriate to the context."""
            }
        }

        lang_prompts = prompts.get(self.language, prompts["en"])
        return lang_prompts.get(context, lang_prompts["general"])

    async def explain_variance(self, variance_data: Dict[str, Any]) -> str:
        """
        Generate an AI explanation of budget variances.

        Args:
            variance_data: Variance analysis data from /analytics/variance endpoint

        Returns:
            Human-readable explanation of the variances
        """
        # Check cache first
        cache = get_cache_service()
        if self.cache_enabled and cache:
            cache_key = _make_cache_key("variance", json.dumps(variance_data, sort_keys=True, default=str))
            cached = cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for variance explanation")
                return cached

        # Build context from variance data
        global_info = variance_data.get("global_variance", {})
        categories = variance_data.get("by_category", [])

        # Get over-budget categories
        over_budget = [c for c in categories if c.get("status") == "over_budget"]
        under_budget = [c for c in categories if c.get("status") == "under_budget"]

        if self.language == "fr":
            prompt = f"""Analyse ces ecarts budgetaires et explique simplement:

Budget prevu: {global_info.get('budgeted', 0):.2f}EUR
Depenses reelles: {global_info.get('actual', 0):.2f}EUR
Ecart: {global_info.get('variance', 0):.2f}EUR ({global_info.get('variance_pct', 0):.1f}%)
Statut global: {global_info.get('status', 'inconnu')}

Categories en depassement ({len(over_budget)}):
"""
            for cat in over_budget[:5]:  # Top 5 over budget
                prompt += f"- {cat['category']}: +{cat['variance']:.0f}EUR ({cat['variance_pct']:.0f}%)"
                if cat.get('vs_last_month'):
                    prompt += f" vs mois precedent: {cat['vs_last_month']}"
                prompt += "\n"

            if under_budget:
                prompt += f"\nCategories economisees ({len(under_budget)}):\n"
                for cat in under_budget[:3]:
                    prompt += f"- {cat['category']}: {cat['variance']:.0f}EUR\n"

            prompt += "\nDonne une explication claire en 2-3 phrases et 2 suggestions concretes."
        else:
            prompt = f"""Analyze these budget variances and explain simply:

Planned budget: {global_info.get('budgeted', 0):.2f}EUR
Actual expenses: {global_info.get('actual', 0):.2f}EUR
Variance: {global_info.get('variance', 0):.2f}EUR ({global_info.get('variance_pct', 0):.1f}%)
Overall status: {global_info.get('status', 'unknown')}

Over-budget categories ({len(over_budget)}):
"""
            for cat in over_budget[:5]:
                prompt += f"- {cat['category']}: +{cat['variance']:.0f}EUR ({cat['variance_pct']:.0f}%)"
                if cat.get('vs_last_month'):
                    prompt += f" vs previous month: {cat['vs_last_month']}"
                prompt += "\n"

            if under_budget:
                prompt += f"\nUnder-budget categories ({len(under_budget)}):\n"
                for cat in under_budget[:3]:
                    prompt += f"- {cat['category']}: {cat['variance']:.0f}EUR\n"

            prompt += "\nProvide a clear explanation in 2-3 sentences and 2 concrete suggestions."

        result = await self._call_llm(prompt, self._get_system_prompt("variance"))

        # Cache the result
        if self.cache_enabled and cache:
            cache.set(cache_key, result, ttl=self.cache_ttl_variance)
            logger.debug(f"Cached variance explanation (TTL: {self.cache_ttl_variance}s)")

        return result

    async def suggest_savings(self, category: str, spending_history: List[Dict]) -> str:
        """
        Suggest ways to reduce spending in a specific category.

        Args:
            category: Category name
            spending_history: List of monthly spending data for this category

        Returns:
            Personalized savings suggestions
        """
        # Check cache first
        cache = get_cache_service()
        if self.cache_enabled and cache:
            cache_key = _make_cache_key("savings", category, json.dumps(spending_history, default=str))
            cached = cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for savings suggestion: {category}")
                return cached

        # Calculate statistics from history
        amounts = [h.get("amount", 0) for h in spending_history]
        avg_amount = sum(amounts) / len(amounts) if amounts else 0
        max_amount = max(amounts) if amounts else 0
        min_amount = min(amounts) if amounts else 0

        # Get top transactions if available
        top_merchants = []
        for h in spending_history:
            for tx in h.get("transactions", [])[:3]:
                top_merchants.append(tx.get("label", "Unknown"))

        if self.language == "fr":
            prompt = f"""Analyse ces depenses "{category}" et suggere 3 facons concretes de reduire de 15-20%:

Depense moyenne mensuelle: {avg_amount:.0f}EUR
Maximum: {max_amount:.0f}EUR
Minimum: {min_amount:.0f}EUR
Principaux commercants: {', '.join(set(top_merchants[:5]))}

Sois specifique et actionable. Adapte tes conseils a cette categorie."""
        else:
            prompt = f"""Analyze these "{category}" expenses and suggest 3 concrete ways to reduce by 15-20%:

Average monthly spending: {avg_amount:.0f}EUR
Maximum: {max_amount:.0f}EUR
Minimum: {min_amount:.0f}EUR
Main merchants: {', '.join(set(top_merchants[:5]))}

Be specific and actionable. Adapt your advice to this category."""

        result = await self._call_llm(prompt, self._get_system_prompt("savings"))

        # Cache the result
        if self.cache_enabled and cache:
            cache.set(cache_key, result, ttl=self.cache_ttl_savings)
            logger.debug(f"Cached savings suggestion for {category} (TTL: {self.cache_ttl_savings}s)")

        return result

    async def monthly_summary(self, month_data: Dict[str, Any]) -> str:
        """
        Generate an intelligent monthly summary.

        Args:
            month_data: Monthly budget data including income, expenses, categories

        Returns:
            Engaging monthly narrative summary
        """
        # Check cache first
        cache = get_cache_service()
        if self.cache_enabled and cache:
            cache_key = _make_cache_key("summary", json.dumps(month_data, sort_keys=True, default=str))
            cached = cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for monthly summary")
                return cached

        income = month_data.get("income", 0)
        expenses = month_data.get("expenses", 0)
        savings = income - expenses if income > expenses else 0
        savings_rate = (savings / income * 100) if income > 0 else 0

        top_categories = month_data.get("top_categories", [])
        anomalies = month_data.get("anomalies", [])

        if self.language == "fr":
            prompt = f"""Resume ce mois budgetaire de facon engageante:

Revenus: {income:.0f}EUR
Depenses: {expenses:.0f}EUR
Epargne: {savings:.0f}EUR (taux: {savings_rate:.1f}%)

Top 3 categories de depenses:
"""
            for i, cat in enumerate(top_categories[:3], 1):
                prompt += f"{i}. {cat.get('name', 'Unknown')}: {cat.get('amount', 0):.0f}EUR\n"

            if anomalies:
                prompt += f"\nAnomalies detectees: {len(anomalies)}\n"
                for a in anomalies[:2]:
                    prompt += f"- {a.get('description', 'Depense inhabituelle')}\n"

            prompt += "\nCommence par un emoji adapte. Fais un bilan en 3-4 phrases: points positifs, axes d'amelioration, et un objectif pour le mois prochain."
        else:
            prompt = f"""Summarize this budget month in an engaging way:

Income: {income:.0f}EUR
Expenses: {expenses:.0f}EUR
Savings: {savings:.0f}EUR (rate: {savings_rate:.1f}%)

Top 3 expense categories:
"""
            for i, cat in enumerate(top_categories[:3], 1):
                prompt += f"{i}. {cat.get('name', 'Unknown')}: {cat.get('amount', 0):.0f}EUR\n"

            if anomalies:
                prompt += f"\nDetected anomalies: {len(anomalies)}\n"
                for a in anomalies[:2]:
                    prompt += f"- {a.get('description', 'Unusual expense')}\n"

            prompt += "\nStart with an appropriate emoji. Give a summary in 3-4 sentences: positives, areas for improvement, and a goal for next month."

        result = await self._call_llm(prompt, self._get_system_prompt("summary"))

        # Cache the result
        if self.cache_enabled and cache:
            cache.set(cache_key, result, ttl=self.cache_ttl_summary)
            logger.debug(f"Cached monthly summary (TTL: {self.cache_ttl_summary}s)")

        return result

    async def answer_question(self, question: str, budget_context: Dict[str, Any]) -> str:
        """
        Answer a free-form question about the user's budget.

        Args:
            question: User's question
            budget_context: Relevant budget data for context

        Returns:
            AI answer based on the budget data
        """
        # Check cache first (short TTL for Q&A as questions are often unique)
        cache = get_cache_service()
        if self.cache_enabled and cache:
            cache_key = _make_cache_key("answer", question, json.dumps(budget_context, sort_keys=True, default=str))
            cached = cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for answer question")
                return cached

        # Build context summary
        month = budget_context.get("month", "current")
        total_expenses = budget_context.get("total_expenses", 0)
        total_income = budget_context.get("total_income", 0)
        categories = budget_context.get("categories", {})

        if self.language == "fr":
            context_text = f"""Contexte budget ({month}):
- Revenus: {total_income:.0f}EUR
- Depenses totales: {total_expenses:.0f}EUR
- Solde: {total_income - total_expenses:.0f}EUR

Depenses par categorie:
"""
        else:
            context_text = f"""Budget context ({month}):
- Income: {total_income:.0f}EUR
- Total expenses: {total_expenses:.0f}EUR
- Balance: {total_income - total_expenses:.0f}EUR

Expenses by category:
"""

        for cat, amount in list(categories.items())[:10]:
            context_text += f"- {cat}: {amount:.0f}EUR\n"

        prompt = f"""{context_text}

Question: {question}

Reponds de facon concise et utile.""" if self.language == "fr" else f"""{context_text}

Question: {question}

Answer concisely and helpfully."""

        result = await self._call_llm(prompt, self._get_system_prompt("general"))

        # Cache the result
        if self.cache_enabled and cache:
            cache.set(cache_key, result, ttl=self.cache_ttl_answer)
            logger.debug(f"Cached answer (TTL: {self.cache_ttl_answer}s)")

        return result


# Singleton instance
_ai_service: Optional[AIAnalysisService] = None


def get_ai_service() -> AIAnalysisService:
    """Get or create the AI Analysis Service singleton."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIAnalysisService()
        logger.info(f"AI Service initialized: configured={_ai_service.is_configured}, model={_ai_service.model}")
    return _ai_service


def reset_ai_service() -> None:
    """Reset the singleton for testing or configuration changes."""
    global _ai_service
    _ai_service = None
    logger.info("AI Service singleton reset")
