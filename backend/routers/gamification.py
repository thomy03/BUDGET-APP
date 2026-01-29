"""
Gamification Router for Budget Famille v4.1
Provides endpoints for achievements, challenges, and user progress.
"""
import logging
import datetime as dt
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from dependencies.auth import get_current_user
from dependencies.database import get_db
from models.gamification import (
    Achievement, UserAchievement, Challenge, UserChallenge,
    UserStreak, UserPoints, PREDEFINED_ACHIEVEMENTS, calculate_level
)
from models.database import Transaction, User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/gamification",
    tags=["gamification"],
    responses={404: {"description": "Not found"}}
)


# =============================================================================
# SCHEMAS
# =============================================================================

class AchievementResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str
    icon: str
    category: str
    tier: str
    points: int
    is_hidden: bool
    progress: float = 0
    is_earned: bool = False
    earned_at: Optional[str] = None


class UserStatsResponse(BaseModel):
    total_points: int
    level: int
    level_progress: float
    achievements_earned: int
    total_achievements: int
    challenges_completed: int
    current_streak: int
    longest_streak: int


class ChallengeResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str
    icon: str
    challenge_type: str
    start_date: str
    end_date: str
    goal_type: str
    goal_value: float
    goal_category: Optional[str]
    reward_points: int
    is_joined: bool = False
    progress: float = 0
    progress_percent: float = 0
    is_completed: bool = False


class StreakResponse(BaseModel):
    streak_type: str
    current_streak: int
    longest_streak: int
    last_activity: Optional[str]


class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    total_points: int
    level: int
    achievements_count: int


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_user_id_from_username(db: Session, username: str) -> int:
    """Get the user ID from the database using the username.

    The auth system returns a UserInDB Pydantic model with only username,
    but gamification needs the actual user ID from the database.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        # Create user if not exists (for backwards compatibility with fake_users_db)
        user = User(
            username=username,
            hashed_password="",  # Not used, auth is handled elsewhere
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user record for gamification: {username}")
    return user.id


def ensure_user_points(db: Session, user_id: int) -> UserPoints:
    """Ensure user has a points record, create if not exists."""
    points = db.query(UserPoints).filter(UserPoints.user_id == user_id).first()
    if not points:
        points = UserPoints(user_id=user_id)
        db.add(points)
        db.commit()
        db.refresh(points)
    return points


def add_points(db: Session, user_id: int, points: int, source: str = "action") -> UserPoints:
    """Add points to a user and update their level."""
    user_points = ensure_user_points(db, user_id)

    user_points.total_points += points

    if source == "achievement":
        user_points.points_from_achievements += points
    elif source == "challenge":
        user_points.points_from_challenges += points
    elif source == "streak":
        user_points.points_from_streaks += points
    else:
        user_points.points_from_actions += points

    # Recalculate level
    level, progress = calculate_level(user_points.total_points)
    user_points.level = level
    user_points.level_progress = progress

    db.commit()
    db.refresh(user_points)

    logger.info(f"User {user_id} earned {points} points ({source}). Total: {user_points.total_points}, Level: {level}")

    return user_points


def check_and_award_achievement(db: Session, user_id: int, achievement_code: str, context: Dict = None) -> Optional[UserAchievement]:
    """Check if user qualifies for an achievement and award it."""
    # Get the achievement
    achievement = db.query(Achievement).filter(Achievement.code == achievement_code).first()
    if not achievement or not achievement.is_active:
        return None

    # Check if already earned
    existing = db.query(UserAchievement).filter(
        UserAchievement.user_id == user_id,
        UserAchievement.achievement_id == achievement.id,
        UserAchievement.is_completed == True
    ).first()

    if existing:
        return existing

    # Create or update user achievement
    user_achievement = db.query(UserAchievement).filter(
        UserAchievement.user_id == user_id,
        UserAchievement.achievement_id == achievement.id
    ).first()

    if not user_achievement:
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement.id,
            progress=100,
            is_completed=True,
            context_data=context or {}
        )
        db.add(user_achievement)
    else:
        user_achievement.progress = 100
        user_achievement.is_completed = True
        user_achievement.earned_at = dt.datetime.utcnow()
        user_achievement.context_data = context or {}

    # Award points
    add_points(db, user_id, achievement.points, source="achievement")

    db.commit()
    db.refresh(user_achievement)

    logger.info(f"User {user_id} earned achievement: {achievement.name}")

    return user_achievement


def update_streak(db: Session, user_id: int, streak_type: str) -> UserStreak:
    """Update a user's streak for a given activity type."""
    streak = db.query(UserStreak).filter(
        UserStreak.user_id == user_id,
        UserStreak.streak_type == streak_type
    ).first()

    today = dt.datetime.utcnow().date()

    if not streak:
        streak = UserStreak(
            user_id=user_id,
            streak_type=streak_type,
            current_streak=1,
            longest_streak=1,
            last_activity_date=dt.datetime.utcnow()
        )
        db.add(streak)
    else:
        last_date = streak.last_activity_date.date() if streak.last_activity_date else None

        if last_date == today:
            # Already recorded today
            pass
        elif last_date == today - dt.timedelta(days=1):
            # Consecutive day - increment streak
            streak.current_streak += 1
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak
        else:
            # Streak broken - reset
            streak.current_streak = 1

        streak.last_activity_date = dt.datetime.utcnow()

    db.commit()
    db.refresh(streak)

    # Award points for streaks milestones
    if streak.current_streak in [7, 14, 30, 60, 90]:
        points = streak.current_streak
        add_points(db, user_id, points, source="streak")
        logger.info(f"User {user_id} reached {streak.current_streak}-day streak for {streak_type}")

    return streak


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's gamification stats."""
    user_id = get_user_id_from_username(db, current_user.username)
    user_points = ensure_user_points(db, user_id)

    # Count achievements
    achievements_earned = db.query(UserAchievement).filter(
        UserAchievement.user_id == user_id,
        UserAchievement.is_completed == True
    ).count()

    total_achievements = db.query(Achievement).filter(
        Achievement.is_active == True,
        Achievement.is_hidden == False
    ).count()

    # Count completed challenges
    challenges_completed = db.query(UserChallenge).filter(
        UserChallenge.user_id == user_id,
        UserChallenge.is_completed == True
    ).count()

    # Get longest streak
    login_streak = db.query(UserStreak).filter(
        UserStreak.user_id == user_id,
        UserStreak.streak_type == "daily_login"
    ).first()

    return UserStatsResponse(
        total_points=user_points.total_points,
        level=user_points.level,
        level_progress=user_points.level_progress,
        achievements_earned=achievements_earned,
        total_achievements=total_achievements,
        challenges_completed=challenges_completed,
        current_streak=login_streak.current_streak if login_streak else 0,
        longest_streak=login_streak.longest_streak if login_streak else 0
    )


@router.get("/achievements", response_model=List[AchievementResponse])
async def get_achievements(
    category: Optional[str] = None,
    include_hidden: bool = False,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all achievements with user progress."""
    user_id = get_user_id_from_username(db, current_user.username)
    query = db.query(Achievement).filter(Achievement.is_active == True)

    if not include_hidden:
        query = query.filter(Achievement.is_hidden == False)

    if category:
        query = query.filter(Achievement.category == category)

    achievements = query.all()

    # Get user achievements
    user_achievements = {
        ua.achievement_id: ua
        for ua in db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id
        ).all()
    }

    result = []
    for ach in achievements:
        user_ach = user_achievements.get(ach.id)
        result.append(AchievementResponse(
            id=ach.id,
            code=ach.code,
            name=ach.name,
            description=ach.description,
            icon=ach.icon,
            category=ach.category,
            tier=ach.tier,
            points=ach.points,
            is_hidden=ach.is_hidden,
            progress=user_ach.progress if user_ach else 0,
            is_earned=user_ach.is_completed if user_ach else False,
            earned_at=user_ach.earned_at.isoformat() if user_ach and user_ach.earned_at else None
        ))

    return result


@router.get("/achievements/recent", response_model=List[AchievementResponse])
async def get_recent_achievements(
    limit: int = 5,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recently earned achievements."""
    user_id = get_user_id_from_username(db, current_user.username)
    user_achievements = db.query(UserAchievement).filter(
        UserAchievement.user_id == user_id,
        UserAchievement.is_completed == True
    ).order_by(UserAchievement.earned_at.desc()).limit(limit).all()

    result = []
    for ua in user_achievements:
        ach = ua.achievement
        result.append(AchievementResponse(
            id=ach.id,
            code=ach.code,
            name=ach.name,
            description=ach.description,
            icon=ach.icon,
            category=ach.category,
            tier=ach.tier,
            points=ach.points,
            is_hidden=ach.is_hidden,
            progress=100,
            is_earned=True,
            earned_at=ua.earned_at.isoformat() if ua.earned_at else None
        ))

    return result


@router.get("/challenges", response_model=List[ChallengeResponse])
async def get_active_challenges(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all active challenges."""
    user_id = get_user_id_from_username(db, current_user.username)
    now = dt.datetime.utcnow()

    challenges = db.query(Challenge).filter(
        Challenge.is_active == True,
        Challenge.start_date <= now,
        Challenge.end_date >= now
    ).all()

    # Get user challenges
    user_challenges = {
        uc.challenge_id: uc
        for uc in db.query(UserChallenge).filter(
            UserChallenge.user_id == user_id
        ).all()
    }

    result = []
    for ch in challenges:
        user_ch = user_challenges.get(ch.id)
        result.append(ChallengeResponse(
            id=ch.id,
            code=ch.code,
            name=ch.name,
            description=ch.description,
            icon=ch.icon,
            challenge_type=ch.challenge_type,
            start_date=ch.start_date.isoformat(),
            end_date=ch.end_date.isoformat(),
            goal_type=ch.goal_type,
            goal_value=ch.goal_value,
            goal_category=ch.goal_category,
            reward_points=ch.reward_points,
            is_joined=user_ch is not None,
            progress=user_ch.current_progress if user_ch else 0,
            progress_percent=user_ch.progress_percent if user_ch else 0,
            is_completed=user_ch.is_completed if user_ch else False
        ))

    return result


@router.post("/challenges/{challenge_id}/join")
async def join_challenge(
    challenge_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a challenge."""
    user_id = get_user_id_from_username(db, current_user.username)
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    # Check if already joined
    existing = db.query(UserChallenge).filter(
        UserChallenge.user_id == user_id,
        UserChallenge.challenge_id == challenge_id
    ).first()

    if existing:
        return {"status": "already_joined", "challenge_id": challenge_id}

    # Join the challenge
    user_challenge = UserChallenge(
        user_id=user_id,
        challenge_id=challenge_id
    )
    db.add(user_challenge)
    db.commit()

    return {"status": "joined", "challenge_id": challenge_id, "challenge_name": challenge.name}


@router.get("/streaks", response_model=List[StreakResponse])
async def get_user_streaks(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all user streaks."""
    user_id = get_user_id_from_username(db, current_user.username)
    streaks = db.query(UserStreak).filter(
        UserStreak.user_id == user_id
    ).all()

    return [
        StreakResponse(
            streak_type=s.streak_type,
            current_streak=s.current_streak,
            longest_streak=s.longest_streak,
            last_activity=s.last_activity_date.isoformat() if s.last_activity_date else None
        )
        for s in streaks
    ]


@router.post("/track-activity")
async def track_activity(
    activity_type: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Track a user activity (login, import, budget_check, etc.)."""
    user_id = get_user_id_from_username(db, current_user.username)
    valid_types = ["daily_login", "import", "budget_check", "ai_chat", "tag"]

    if activity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid activity type. Valid types: {valid_types}")

    streak = update_streak(db, user_id, activity_type)

    # Check for streak-based achievements
    if activity_type == "daily_login" and streak.current_streak >= 7:
        check_and_award_achievement(db, user_id, "analyzer")

    return {
        "status": "tracked",
        "activity_type": activity_type,
        "current_streak": streak.current_streak,
        "longest_streak": streak.longest_streak
    }


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    limit: int = 10,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get top users by points."""
    top_users = db.query(UserPoints).order_by(UserPoints.total_points.desc()).limit(limit).all()

    result = []
    for i, up in enumerate(top_users, 1):
        # Get username
        user = db.query(User).filter(User.id == up.user_id).first()

        # Count achievements
        achievements_count = db.query(UserAchievement).filter(
            UserAchievement.user_id == up.user_id,
            UserAchievement.is_completed == True
        ).count()

        result.append(LeaderboardEntry(
            rank=i,
            username=user.username if user else "Unknown",
            total_points=up.total_points,
            level=up.level,
            achievements_count=achievements_count
        ))

    return result


@router.post("/init-achievements")
async def initialize_achievements(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initialize predefined achievements in the database."""
    created = 0
    updated = 0

    for ach_data in PREDEFINED_ACHIEVEMENTS:
        existing = db.query(Achievement).filter(Achievement.code == ach_data["code"]).first()

        if not existing:
            achievement = Achievement(**ach_data)
            db.add(achievement)
            created += 1
        else:
            # Update existing
            for key, value in ach_data.items():
                setattr(existing, key, value)
            updated += 1

    db.commit()

    return {
        "status": "initialized",
        "created": created,
        "updated": updated,
        "total": len(PREDEFINED_ACHIEVEMENTS)
    }


@router.post("/check-achievements")
async def check_all_achievements(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check and award any achievements the user qualifies for."""
    user_id = get_user_id_from_username(db, current_user.username)
    awarded = []

    # Get user's transaction data
    transactions = db.query(Transaction).filter(
        Transaction.exclude == False
    ).all()

    # Count tags
    tag_count = sum(1 for tx in transactions if tx.tags)

    # Check tagger_pro achievement
    if tag_count >= 100:
        result = check_and_award_achievement(db, user_id, "tagger_pro")
        if result and result.is_completed:
            awarded.append("tagger_pro")

    # Check budget_starter
    from models.database import CategoryBudget
    budget_count = db.query(CategoryBudget).filter(CategoryBudget.is_active == True).count()

    if budget_count >= 1:
        result = check_and_award_achievement(db, user_id, "budget_starter")
        if result:
            awarded.append("budget_starter")

    if budget_count >= 5:
        result = check_and_award_achievement(db, user_id, "budget_complete")
        if result:
            awarded.append("budget_complete")

    return {
        "status": "checked",
        "awarded": awarded,
        "count": len(awarded)
    }
