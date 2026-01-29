"""
Chat Memory Service for Budget Famille v4.1
Provides multi-turn conversation memory with Redis storage and SQLite fallback.

Features:
- Session-based conversation storage (TTL 30 minutes)
- Last 10 messages per session
- Financial context injection
- Redis primary with SQLite fallback
"""
import logging
import uuid
import datetime as dt
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_SESSION_TTL = 1800  # 30 minutes
MAX_MESSAGES_PER_SESSION = 10
SESSION_KEY_PREFIX = "chat_session"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ChatMessage:
    """Represents a single chat message."""
    role: MessageRole
    content: str
    timestamp: str
    message_id: str = ""

    def __post_init__(self):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())[:8]
        if isinstance(self.role, str):
            self.role = MessageRole(self.role)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_id": self.message_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=data["timestamp"],
            message_id=data.get("message_id", "")
        )


@dataclass
class ChatSession:
    """Represents a chat session with message history."""
    session_id: str
    user_id: str
    messages: List[ChatMessage]
    created_at: str
    updated_at: str
    financial_context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "financial_context": self.financial_context,
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatSession":
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            messages=[ChatMessage.from_dict(m) for m in data.get("messages", [])],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            financial_context=data.get("financial_context"),
            metadata=data.get("metadata")
        )

    def add_message(self, role: MessageRole, content: str) -> ChatMessage:
        """Add a message to the session."""
        msg = ChatMessage(
            role=role,
            content=content,
            timestamp=dt.datetime.now().isoformat()
        )
        self.messages.append(msg)

        # Keep only last N messages
        if len(self.messages) > MAX_MESSAGES_PER_SESSION:
            self.messages = self.messages[-MAX_MESSAGES_PER_SESSION:]

        self.updated_at = dt.datetime.now().isoformat()
        return msg

    def get_conversation_history(self, include_system: bool = False) -> List[Dict[str, str]]:
        """Get conversation history formatted for LLM context."""
        history = []
        for msg in self.messages:
            if not include_system and msg.role == MessageRole.SYSTEM:
                continue
            history.append({
                "role": msg.role.value,
                "content": msg.content
            })
        return history

    def build_context_prompt(self) -> str:
        """Build a context string from recent messages for LLM."""
        if not self.messages:
            return ""

        lines = ["HISTORIQUE DE CONVERSATION RECENT:"]
        for msg in self.messages[-5:]:  # Last 5 messages for context
            role_label = "Utilisateur" if msg.role == MessageRole.USER else "Assistant"
            # Truncate long messages
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            lines.append(f"{role_label}: {content}")

        return "\n".join(lines)


class ChatMemoryService:
    """
    Service for managing chat conversation memory.
    Uses Redis when available, falls back to in-memory storage.
    """

    def __init__(self):
        self._cache: Any = None
        self._fallback_storage: Dict[str, Any] = {}
        self._initialized = False

    def _get_cache(self):
        """Lazy-load cache service."""
        if self._cache is None:
            try:
                from services.redis_cache import get_redis_cache
                self._cache = get_redis_cache()
                logger.info("Chat memory using Redis cache")
            except Exception as e:
                logger.warning(f"Redis unavailable for chat memory: {e}")
                self._cache = None
        return self._cache

    def _make_session_key(self, user_id: str, session_id: str) -> str:
        """Create a cache key for a session."""
        return f"{SESSION_KEY_PREFIX}:{user_id}:{session_id}"

    def _make_user_sessions_key(self, user_id: str) -> str:
        """Create a cache key for user's session list."""
        return f"{SESSION_KEY_PREFIX}:{user_id}:sessions"

    def create_session(
        self,
        user_id: str,
        financial_context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatSession:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())
        now = dt.datetime.now().isoformat()

        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            messages=[],
            created_at=now,
            updated_at=now,
            financial_context=financial_context,
            metadata=metadata
        )

        # Save to storage
        self._save_session(session)

        # Track session in user's session list
        self._add_to_user_sessions(user_id, session_id)

        logger.info(f"Created chat session {session_id} for user {user_id}")
        return session

    def get_session(self, user_id: str, session_id: str) -> Optional[ChatSession]:
        """Retrieve a chat session."""
        cache = self._get_cache()
        key = self._make_session_key(user_id, session_id)

        if cache:
            data = cache.get(key)
            if data:
                return ChatSession.from_dict(data)
        else:
            # Fallback storage
            if key in self._fallback_storage:
                return ChatSession.from_dict(self._fallback_storage[key])

        return None

    def get_or_create_session(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        financial_context: Optional[Dict[str, Any]] = None
    ) -> ChatSession:
        """Get existing session or create new one."""
        if session_id:
            session = self.get_session(user_id, session_id)
            if session:
                # Update financial context if provided
                if financial_context:
                    session.financial_context = financial_context
                    self._save_session(session)
                return session

        # Create new session
        return self.create_session(user_id, financial_context)

    def _save_session(self, session: ChatSession) -> bool:
        """Save session to storage."""
        cache = self._get_cache()
        key = self._make_session_key(session.user_id, session.session_id)
        data = session.to_dict()

        if cache:
            return cache.set(key, data, ttl=DEFAULT_SESSION_TTL)
        else:
            # Fallback storage
            self._fallback_storage[key] = data
            return True

    def _add_to_user_sessions(self, user_id: str, session_id: str):
        """Track session in user's session list."""
        cache = self._get_cache()
        key = self._make_user_sessions_key(user_id)

        if cache:
            # Get existing sessions
            sessions = cache.get(key) or []
            if session_id not in sessions:
                sessions.append(session_id)
                # Keep only last 10 sessions
                sessions = sessions[-10:]
                cache.set(key, sessions, ttl=DEFAULT_SESSION_TTL * 2)
        else:
            # For fallback, store session lists separately
            if key not in self._fallback_storage:
                self._fallback_storage[key] = {"sessions": []}
            sessions_data = self._fallback_storage[key]
            if isinstance(sessions_data, dict) and "sessions" in sessions_data:
                session_list: List[str] = sessions_data["sessions"]
                if session_id not in session_list:
                    session_list.append(session_id)
                    sessions_data["sessions"] = session_list[-10:]

    def add_message(
        self,
        user_id: str,
        session_id: str,
        role: MessageRole,
        content: str
    ) -> Optional[ChatMessage]:
        """Add a message to a session."""
        session = self.get_session(user_id, session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for user {user_id}")
            return None

        msg = session.add_message(role, content)
        self._save_session(session)

        return msg

    def add_user_message(self, user_id: str, session_id: str, content: str) -> Optional[ChatMessage]:
        """Convenience method to add a user message."""
        return self.add_message(user_id, session_id, MessageRole.USER, content)

    def add_assistant_message(self, user_id: str, session_id: str, content: str) -> Optional[ChatMessage]:
        """Convenience method to add an assistant message."""
        return self.add_message(user_id, session_id, MessageRole.ASSISTANT, content)

    def get_conversation_history(
        self,
        user_id: str,
        session_id: str,
        include_system: bool = False
    ) -> List[Dict[str, str]]:
        """Get conversation history for a session."""
        session = self.get_session(user_id, session_id)
        if not session:
            return []
        return session.get_conversation_history(include_system)

    def build_llm_context(
        self,
        user_id: str,
        session_id: str,
        current_question: str,
        financial_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Build complete context for LLM including conversation history.

        Returns:
            Tuple of (system_prompt, messages_history)
        """
        session = self.get_session(user_id, session_id)

        # Build financial context section
        financial_section = ""
        ctx = financial_context or (session.financial_context if session else None)
        if ctx:
            financial_section = f"""
CONTEXTE FINANCIER DE L'UTILISATEUR ({ctx.get('month', 'actuel')}):
- Revenus totaux: {ctx.get('total_income', 0):.2f} EUR
- Depenses totales: {ctx.get('total_expenses', 0):.2f} EUR
- Epargne/Deficit: {ctx.get('savings', 0):.2f} EUR
- Nombre de transactions: {ctx.get('transaction_count', 0)}
- Statut global: {ctx.get('budget_status', 'inconnu')}
"""
            if ctx.get('top_categories'):
                financial_section += "\nTOP CATEGORIES DE DEPENSES:\n"
                for i, cat in enumerate(ctx['top_categories'][:5], 1):
                    financial_section += f"  {i}. {cat['name']}: {cat['amount']:.2f} EUR\n"

        # Build conversation history section
        history_section = ""
        if session and session.messages:
            history_section = "\n" + session.build_context_prompt() + "\n"

        system_prompt = f"""Tu es un coach budget familial bienveillant et expert.
{financial_section}
{history_section}
INSTRUCTIONS:
- Reponds de maniere personnalisee basee sur les donnees ci-dessus
- Sois pratique avec des conseils actionnables
- Sois encourageant mais honnete
- Sois concis (2-3 paragraphes max)
- Utilise des emojis avec moderation
- Tiens compte de l'historique de conversation si present
"""

        # Build messages list for chat completion API
        messages = []
        if session:
            for msg in session.messages[-6:]:  # Last 6 messages
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        # Add current question
        messages.append({
            "role": "user",
            "content": current_question
        })

        return system_prompt, messages

    def delete_session(self, user_id: str, session_id: str) -> bool:
        """Delete a chat session."""
        cache = self._get_cache()
        key = self._make_session_key(user_id, session_id)

        if cache:
            return cache.delete(key)
        else:
            if key in self._fallback_storage:
                del self._fallback_storage[key]
                return True
        return False

    def list_user_sessions(self, user_id: str) -> List[str]:
        """List all session IDs for a user."""
        cache = self._get_cache()
        key = self._make_user_sessions_key(user_id)

        if cache:
            result = cache.get(key)
            if isinstance(result, list):
                return result
            return []
        else:
            sessions_data = self._fallback_storage.get(key, {"sessions": []})
            if isinstance(sessions_data, dict) and "sessions" in sessions_data:
                return sessions_data["sessions"]
            return []

    def get_active_session(self, user_id: str) -> Optional[ChatSession]:
        """Get the most recent active session for a user."""
        sessions = self.list_user_sessions(user_id)
        if not sessions:
            return None

        # Get the most recent session
        for session_id in reversed(sessions):
            session = self.get_session(user_id, session_id)
            if session:
                return session

        return None

    def clear_user_sessions(self, user_id: str) -> int:
        """Clear all sessions for a user."""
        sessions = self.list_user_sessions(user_id)
        count = 0
        for session_id in sessions:
            if self.delete_session(user_id, session_id):
                count += 1

        # Clear session list
        cache = self._get_cache()
        key = self._make_user_sessions_key(user_id)
        if cache:
            cache.delete(key)
        elif key in self._fallback_storage:
            del self._fallback_storage[key]

        logger.info(f"Cleared {count} sessions for user {user_id}")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get memory service statistics."""
        cache = self._get_cache()

        return {
            "storage_type": "redis" if cache else "in_memory_fallback",
            "fallback_session_count": len([k for k in self._fallback_storage if k.startswith(SESSION_KEY_PREFIX)]),
            "session_ttl_seconds": DEFAULT_SESSION_TTL,
            "max_messages_per_session": MAX_MESSAGES_PER_SESSION
        }


# Singleton instance
_chat_memory_instance: Optional[ChatMemoryService] = None


def get_chat_memory() -> ChatMemoryService:
    """Get the chat memory service singleton."""
    global _chat_memory_instance
    if _chat_memory_instance is None:
        _chat_memory_instance = ChatMemoryService()
        logger.info("Chat memory service initialized")
    return _chat_memory_instance


def reset_chat_memory():
    """Reset the chat memory service (useful for testing)."""
    global _chat_memory_instance
    _chat_memory_instance = None
