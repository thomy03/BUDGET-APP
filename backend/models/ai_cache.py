"""
AI Cache Models for Budget App
SQLAlchemy models for caching AI responses
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from datetime import datetime

try:
    from models.database import Base
except ImportError:
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()


class AICache(Base):
    """Cache for AI API responses to reduce costs and latency"""
    __tablename__ = "ai_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(255), unique=True, index=True, nullable=False)
    cache_type = Column(String(50))  # "classification", "suggestion", "research"
    input_hash = Column(String(64))  # SHA256 hash of input
    input_text = Column(Text)
    response_text = Column(Text)
    model_used = Column(String(50))
    confidence = Column(Float)
    hit_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime)
    
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


__all__ = ['AICache']
