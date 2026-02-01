"""
Gamification Models for Budget App
SQLAlchemy models for achievements, challenges, streaks and points
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

# Import Base from the main database module
try:
    from models.database import Base
except ImportError:
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()


class Achievement(Base):
    """User achievements/badges"""
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    icon = Column(String(50))  # Emoji or icon name
    category = Column(String(50))  # e.g., "savings", "tracking", "goals"
    points = Column(Integer, default=10)
    requirement_type = Column(String(50))  # e.g., "streak", "total", "count"
    requirement_value = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user_achievements = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    """Junction table for user-achievement relationship"""
    __tablename__ = "user_achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    unlocked_at = Column(DateTime, default=func.now())
    progress = Column(Float, default=0.0)  # 0.0 to 1.0
    
    # Relationships
    achievement = relationship("Achievement", back_populates="user_achievements")


class Challenge(Base):
    """Weekly/monthly challenges"""
    __tablename__ = "challenges"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    challenge_type = Column(String(50))  # "weekly", "monthly", "special"
    target_type = Column(String(50))  # "spending_limit", "savings_goal", "tracking"
    target_value = Column(Float)
    points_reward = Column(Integer, default=50)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user_challenges = relationship("UserChallenge", back_populates="challenge")


class UserChallenge(Base):
    """User participation in challenges"""
    __tablename__ = "user_challenges"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    challenge_id = Column(Integer, ForeignKey("challenges.id"), nullable=False)
    joined_at = Column(DateTime, default=func.now())
    progress = Column(Float, default=0.0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    challenge = relationship("Challenge", back_populates="user_challenges")


class UserStreak(Base):
    """Track user streaks for various activities"""
    __tablename__ = "user_streaks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    streak_type = Column(String(50))  # "daily_login", "daily_tracking", "savings"
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class UserPoints(Base):
    """Track user points and level"""
    __tablename__ = "user_points"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    total_points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    points_this_week = Column(Integer, default=0)
    points_this_month = Column(Integer, default=0)
    last_point_earned = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# Export all models
__all__ = [
    'Achievement',
    'UserAchievement', 
    'Challenge',
    'UserChallenge',
    'UserStreak',
    'UserPoints'
]


# Predefined achievements for the app
PREDEFINED_ACHIEVEMENTS = [
    {
        "name": "First Steps",
        "description": "Added your first transaction",
        "icon": "🎯",
        "category": "tracking",
        "points": 10,
        "requirement_type": "count",
        "requirement_value": 1
    },
    {
        "name": "Week Warrior",
        "description": "Tracked expenses for 7 consecutive days",
        "icon": "📅",
        "category": "streak",
        "points": 50,
        "requirement_type": "streak",
        "requirement_value": 7
    },
    {
        "name": "Budget Master",
        "description": "Stayed under budget for a full month",
        "icon": "💰",
        "category": "savings",
        "points": 100,
        "requirement_type": "monthly",
        "requirement_value": 1
    },
    {
        "name": "Century Club",
        "description": "Tracked 100 transactions",
        "icon": "💯",
        "category": "tracking",
        "points": 75,
        "requirement_type": "count",
        "requirement_value": 100
    },
    {
        "name": "Savings Star",
        "description": "Saved 10% of your income",
        "icon": "⭐",
        "category": "savings",
        "points": 150,
        "requirement_type": "percentage",
        "requirement_value": 10
    }
]


def calculate_level(total_points: int) -> int:
    """Calculate user level based on total points
    
    Level thresholds:
    - Level 1: 0-99 points
    - Level 2: 100-249 points
    - Level 3: 250-499 points
    - Level 4: 500-999 points
    - Level 5: 1000+ points
    And so on...
    """
    if total_points < 100:
        return 1
    elif total_points < 250:
        return 2
    elif total_points < 500:
        return 3
    elif total_points < 1000:
        return 4
    else:
        # After level 4, each level requires 500 more points
        return 4 + (total_points - 500) // 500


# Update exports
__all__ = [
    'Achievement',
    'UserAchievement', 
    'Challenge',
    'UserChallenge',
    'UserStreak',
    'UserPoints',
    'PREDEFINED_ACHIEVEMENTS',
    'calculate_level'
]
