"""
AI Cache Service for managing AI-generated content caching.
Provides intelligent caching with TTL, invalidation, and hit tracking.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.ai_cache import AICache

logger = logging.getLogger(__name__)


# TTL configuration by cache type (in hours)
CACHE_TTL_HOURS = {
    'import': 24,        # Import insights - stable after import
    'tip': 168,          # Transaction tips - 7 days (pattern-based, stable)
    'coach': 0.5,        # Dashboard tips - 30 minutes (rotate frequently)
    'variance': 1,       # Variance explanations - 1 hour
    'daily': 24,         # Daily insights - until next day
}


class AICacheService:
    """Service for managing AI response caching."""

    def __init__(self, db: Session):
        self.db = db

    def get_cached(
        self,
        cache_key: str,
        cache_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached AI response if valid and not expired.

        Args:
            cache_key: Unique cache key
            cache_type: Optional type filter for validation

        Returns:
            Cached data dict or None if not found/expired
        """
        try:
            query = self.db.query(AICache).filter(
                and_(
                    AICache.cache_key == cache_key,
                    AICache.is_valid == True,
                    AICache.expires_at > datetime.utcnow()
                )
            )

            if cache_type:
                query = query.filter(AICache.cache_type == cache_type)

            cached = query.first()

            if cached:
                # Update hit metrics
                cached.hit_count += 1
                cached.last_accessed = datetime.utcnow()
                self.db.commit()

                logger.debug(f"Cache hit for key: {cache_key} (hits: {cached.hit_count})")
                return json.loads(cached.response_data)

            return None

        except Exception as e:
            logger.error(f"Error retrieving cache for key {cache_key}: {e}")
            return None

    def set_cached(
        self,
        cache_key: str,
        cache_type: str,
        data: Dict[str, Any],
        ttl_hours: Optional[float] = None,
        user_id: Optional[str] = None,
        month: Optional[str] = None
    ) -> bool:
        """
        Store AI response in cache.

        Args:
            cache_key: Unique cache key
            cache_type: Type of cache (import, tip, coach, variance)
            data: Data to cache (will be JSON serialized)
            ttl_hours: Optional override for TTL (uses default by type if not specified)
            user_id: Optional user context
            month: Optional month context (YYYY-MM)

        Returns:
            True if cached successfully
        """
        try:
            # Determine TTL
            if ttl_hours is None:
                ttl_hours = CACHE_TTL_HOURS.get(cache_type, 1)

            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

            # Check if entry exists
            existing = self.db.query(AICache).filter(
                AICache.cache_key == cache_key
            ).first()

            if existing:
                # Update existing entry
                existing.response_data = json.dumps(data, ensure_ascii=False)
                existing.expires_at = expires_at
                existing.is_valid = True
                existing.hit_count = 0
                existing.last_accessed = None
                if user_id:
                    existing.user_id = user_id
                if month:
                    existing.month = month
            else:
                # Create new entry
                cache_entry = AICache(
                    cache_key=cache_key,
                    cache_type=cache_type,
                    response_data=json.dumps(data, ensure_ascii=False),
                    expires_at=expires_at,
                    user_id=user_id,
                    month=month
                )
                self.db.add(cache_entry)

            self.db.commit()
            logger.debug(f"Cached data for key: {cache_key} (type: {cache_type}, TTL: {ttl_hours}h)")
            return True

        except Exception as e:
            logger.error(f"Error caching data for key {cache_key}: {e}")
            self.db.rollback()
            return False

    def invalidate(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.

        Args:
            pattern: Pattern to match cache keys (supports % wildcard)

        Returns:
            Number of entries invalidated
        """
        try:
            result = self.db.query(AICache).filter(
                AICache.cache_key.like(pattern)
            ).update({AICache.is_valid: False}, synchronize_session='fetch')

            self.db.commit()
            logger.info(f"Invalidated {result} cache entries matching pattern: {pattern}")
            return result

        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
            self.db.rollback()
            return 0

    def invalidate_by_type(self, cache_type: str) -> int:
        """
        Invalidate all cache entries of a specific type.

        Args:
            cache_type: Type of cache to invalidate

        Returns:
            Number of entries invalidated
        """
        try:
            result = self.db.query(AICache).filter(
                AICache.cache_type == cache_type
            ).update({AICache.is_valid: False}, synchronize_session='fetch')

            self.db.commit()
            logger.info(f"Invalidated {result} cache entries of type: {cache_type}")
            return result

        except Exception as e:
            logger.error(f"Error invalidating cache type {cache_type}: {e}")
            self.db.rollback()
            return 0

    def invalidate_by_month(self, month: str) -> int:
        """
        Invalidate all cache entries for a specific month.

        Args:
            month: Month to invalidate (YYYY-MM format)

        Returns:
            Number of entries invalidated
        """
        try:
            result = self.db.query(AICache).filter(
                AICache.month == month
            ).update({AICache.is_valid: False}, synchronize_session='fetch')

            self.db.commit()
            logger.info(f"Invalidated {result} cache entries for month: {month}")
            return result

        except Exception as e:
            logger.error(f"Error invalidating cache for month {month}: {e}")
            self.db.rollback()
            return 0

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        try:
            result = self.db.query(AICache).filter(
                or_(
                    AICache.expires_at < datetime.utcnow(),
                    AICache.is_valid == False
                )
            ).delete(synchronize_session='fetch')

            self.db.commit()
            logger.info(f"Cleaned up {result} expired/invalid cache entries")
            return result

        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
            self.db.rollback()
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics
        """
        try:
            total = self.db.query(AICache).count()
            valid = self.db.query(AICache).filter(
                and_(
                    AICache.is_valid == True,
                    AICache.expires_at > datetime.utcnow()
                )
            ).count()

            # Stats by type
            type_stats = {}
            for cache_type in CACHE_TTL_HOURS.keys():
                type_count = self.db.query(AICache).filter(
                    and_(
                        AICache.cache_type == cache_type,
                        AICache.is_valid == True,
                        AICache.expires_at > datetime.utcnow()
                    )
                ).count()
                type_stats[cache_type] = type_count

            # Total hits
            from sqlalchemy import func
            total_hits = self.db.query(func.sum(AICache.hit_count)).scalar() or 0

            return {
                'total_entries': total,
                'valid_entries': valid,
                'expired_entries': total - valid,
                'by_type': type_stats,
                'total_hits': total_hits,
                'cache_hit_ratio': round(total_hits / max(valid, 1), 2)
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}


def generate_cache_key(*args) -> str:
    """
    Generate a consistent cache key from multiple arguments.

    Args:
        *args: Components to include in the key

    Returns:
        Cache key string
    """
    return ':'.join(str(arg) for arg in args if arg is not None)
