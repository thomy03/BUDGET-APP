"""
Cache management and health check endpoints for Budget Famille v2.3
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from models.database import get_db
from auth import get_current_user
from services.redis_cache import get_redis_cache, invalidate_cache_for_user, invalidate_cache_for_month, warm_cache_for_month
from services.calculations import (
    get_cache_stats, clear_calculation_cache, invalidate_calculations_for_month,
    warm_calculations_cache
)
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/cache",
    tags=["cache"],
    responses={404: {"description": "Not found"}}
)


@router.get("/health", response_model=Dict[str, Any])
async def cache_health_check():
    """
    Perform comprehensive Redis cache health check
    """
    try:
        cache = get_redis_cache()
        health_result = await cache.ahealth_check()
        
        # Determine overall status
        is_healthy = health_result.get("status") == "healthy"
        status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        
        response_data = {
            "service": "redis_cache",
            "timestamp": health_result.get("last_check"),
            "healthy": is_healthy,
            "details": health_result,
            "configuration": {
                "host": settings.redis.host,
                "port": settings.redis.port,
                "db": settings.redis.db,
                "key_prefix": settings.redis.key_prefix,
                "max_connections": settings.redis.max_connections,
                "default_ttl": settings.redis.default_ttl
            }
        }
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
        
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "service": "redis_cache",
                "healthy": False,
                "error": str(e),
                "fallback_mode": True
            }
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_cache_statistics(current_user: dict = Depends(get_current_user)):
    """
    Get comprehensive cache statistics and performance metrics
    """
    try:
        stats = get_cache_stats()
        cache = get_redis_cache()
        
        # Add real-time performance metrics
        performance_stats = await cache.ahealth_check()
        
        return {
            "cache_stats": stats,
            "performance": {
                "response_time_ms": performance_stats.get("response_time_ms"),
                "connection_status": performance_stats.get("status"),
                "last_health_check": performance_stats.get("last_check")
            },
            "configuration": {
                "enabled": settings.cache.enable_cache,
                "redis_host": f"{settings.redis.host}:{settings.redis.port}",
                "key_prefix": settings.redis.key_prefix,
                "ttl_settings": {
                    "default": settings.redis.default_ttl,
                    "summary": settings.redis.summary_ttl,
                    "trends": settings.redis.trends_ttl,
                    "anomaly": settings.redis.anomaly_ttl
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cache statistics: {str(e)}"
        )


@router.delete("/clear")
async def clear_cache(
    user_id: Optional[str] = Query(None, description="User ID to clear cache for (admin only)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Clear cache entries
    - If user_id is provided: clear cache for specific user (admin only)
    - If user_id is None: clear cache for current user
    """
    try:
        # For now, treat all users as having access to their own cache
        # In production, add admin role checking for user_id parameter
        target_user_id = user_id if user_id else current_user.get("username")
        
        deleted_count = clear_calculation_cache(target_user_id)
        
        return {
            "message": "Cache cleared successfully",
            "deleted_entries": deleted_count,
            "user_id": target_user_id,
            "timestamp": dt.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.delete("/invalidate/month/{month}")
async def invalidate_month_cache(
    month: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Invalidate cache entries for a specific month
    Month format: YYYY-MM (e.g., "2024-03")
    """
    try:
        # Validate month format
        import re
        if not re.match(r'^\d{4}-\d{2}$', month):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid month format. Use YYYY-MM (e.g., '2024-03')"
            )
        
        user_id = current_user.get("username")
        deleted_count = invalidate_calculations_for_month(month, user_id)
        
        return {
            "message": f"Cache invalidated for month {month}",
            "deleted_entries": deleted_count,
            "month": month,
            "user_id": user_id,
            "timestamp": dt.datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to invalidate month cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate month cache: {str(e)}"
        )


@router.post("/warm/month/{month}")
async def warm_month_cache(
    month: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Warm cache for a specific month by pre-computing common calculations
    Month format: YYYY-MM (e.g., "2024-03")
    """
    try:
        # Validate month format
        import re
        if not re.match(r'^\d{4}-\d{2}$', month):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid month format. Use YYYY-MM (e.g., '2024-03')"
            )
        
        user_id = current_user.get("username")
        
        # Warm calculations cache
        success = warm_calculations_cache(db, month, user_id)
        
        if success:
            return {
                "message": f"Cache successfully warmed for month {month}",
                "month": month,
                "user_id": user_id,
                "timestamp": dt.datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to warm cache for month {month}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to warm month cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to warm month cache: {str(e)}"
        )


@router.post("/warm/auto/{month}")
async def auto_warm_cache(
    month: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Automatically warm cache using advanced warming strategies
    This endpoint uses the async Redis cache warming function
    """
    try:
        # Validate month format
        import re
        if not re.match(r'^\d{4}-\d{2}$', month):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid month format. Use YYYY-MM (e.g., '2024-03')"
            )
        
        user_id = current_user.get("username")
        
        # Use async cache warming
        result = await warm_cache_for_month(db, month, user_id)
        
        return {
            "message": f"Advanced cache warming completed for month {month}",
            "month": month,
            "user_id": user_id,
            "warmed_keys": result["warmed_keys"],
            "total_warmed": result["total_warmed"],
            "errors": result["errors"],
            "timestamp": dt.datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to auto-warm cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to auto-warm cache: {str(e)}"
        )


@router.get("/performance")
async def get_cache_performance_metrics(current_user: dict = Depends(get_current_user)):
    """
    Get detailed cache performance metrics
    """
    try:
        cache = get_redis_cache()
        
        # Get comprehensive stats
        stats = cache.get_stats()
        health = await cache.ahealth_check()
        
        # Calculate performance indicators
        total_requests = stats.get("total_requests", 0)
        hit_rate = stats.get("hit_rate_percent", 0)
        
        # Performance classification
        if hit_rate >= 80:
            performance_grade = "Excellent"
        elif hit_rate >= 60:
            performance_grade = "Good"
        elif hit_rate >= 40:
            performance_grade = "Fair"
        else:
            performance_grade = "Poor"
        
        response_time = health.get("response_time_ms", 0)
        
        return {
            "performance_summary": {
                "grade": performance_grade,
                "hit_rate_percent": hit_rate,
                "avg_response_time_ms": response_time,
                "total_requests": total_requests
            },
            "detailed_stats": stats,
            "health_status": health,
            "recommendations": _get_performance_recommendations(hit_rate, response_time, stats)
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve performance metrics: {str(e)}"
        )


def _get_performance_recommendations(hit_rate: float, response_time: float, stats: dict) -> list:
    """Generate performance recommendations based on metrics"""
    recommendations = []
    
    if hit_rate < 50:
        recommendations.append({
            "type": "cache_efficiency",
            "message": "Consider warming cache for frequently accessed months",
            "action": "Use /cache/warm/month/{month} endpoints"
        })
    
    if response_time > 100:  # > 100ms
        recommendations.append({
            "type": "performance",
            "message": "Redis response time is high - check network or Redis server performance",
            "action": "Monitor Redis server metrics and network latency"
        })
    
    error_count = stats.get("errors", 0)
    if error_count > 0:
        recommendations.append({
            "type": "reliability",
            "message": f"Cache has {error_count} errors - check Redis connectivity",
            "action": "Review Redis logs and connection settings"
        })
    
    if not recommendations:
        recommendations.append({
            "type": "status",
            "message": "Cache performance is optimal",
            "action": "Continue monitoring"
        })
    
    return recommendations


# Add missing import
import datetime as dt