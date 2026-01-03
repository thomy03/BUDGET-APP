"""
Redis caching service for Budget Famille v2.3
Provides high-performance caching with connection pooling and fallback mechanisms
"""
import json
import logging
import asyncio
import datetime as dt
from typing import Any, Dict, Optional, List, Union
from contextlib import asynccontextmanager

import redis

# aioredis is not compatible with Python 3.11+ (duplicate base class TimeoutError)
# Try to import, fall back gracefully if not available
try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except (ImportError, TypeError) as e:
    aioredis = None  # type: ignore
    AIOREDIS_AVAILABLE = False
    logging.getLogger(__name__).warning(f"aioredis not available: {e}. Using sync-only mode.")

from config.settings import settings

logger = logging.getLogger(__name__)


class RedisCacheService:
    """
    Redis-based caching service with connection pooling and error handling.
    Provides both synchronous and asynchronous interfaces for maximum compatibility.
    """
    
    def __init__(self):
        self._sync_pool: Optional[redis.ConnectionPool] = None
        self._async_pool: Optional[Any] = None  # aioredis.ConnectionPool if available
        self._sync_client: Optional[redis.Redis] = None
        self._async_client: Optional[Any] = None  # aioredis.Redis if available
        self._is_connected = False
        self._connection_attempts = 0
        self._last_health_check = None
        
        # Cache statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "total_requests": 0,
            "last_error": None
        }
    
    def _create_sync_connection(self) -> redis.Redis:
        """Create synchronous Redis connection with pool"""
        try:
            pool = redis.ConnectionPool(
                host=settings.redis.host,
                port=settings.redis.port,
                db=settings.redis.db,
                password=settings.redis.password,
                username=settings.redis.username,
                ssl=settings.redis.ssl,
                max_connections=settings.redis.max_connections,
                retry_on_timeout=settings.redis.retry_on_timeout,
                socket_timeout=settings.redis.socket_timeout,
                socket_connect_timeout=settings.redis.socket_connect_timeout,
                decode_responses=True,
                **settings.redis.connection_pool_kwargs
            )
            
            client = redis.Redis(connection_pool=pool)
            
            # Test connection
            client.ping()
            
            self._sync_pool = pool
            self._sync_client = client
            logger.info("✅ Redis synchronous connection established")
            return client
            
        except Exception as e:
            logger.error(f"❌ Failed to create Redis sync connection: {e}")
            self._stats["errors"] += 1
            self._stats["last_error"] = str(e)
            raise
    
    async def _create_async_connection(self) -> Any:
        """Create asynchronous Redis connection with pool"""
        if not AIOREDIS_AVAILABLE:
            raise RuntimeError("aioredis is not available (Python 3.11+ compatibility issue)")

        try:
            redis_url = f"redis://{settings.redis.host}:{settings.redis.port}/{settings.redis.db}"
            if settings.redis.password:
                redis_url = f"redis://:{settings.redis.password}@{settings.redis.host}:{settings.redis.port}/{settings.redis.db}"

            pool = aioredis.ConnectionPool.from_url(
                redis_url,
                max_connections=settings.redis.max_connections,
                retry_on_timeout=settings.redis.retry_on_timeout,
                socket_timeout=settings.redis.socket_timeout,
                socket_connect_timeout=settings.redis.socket_connect_timeout,
                decode_responses=True,
                **settings.redis.connection_pool_kwargs
            )

            client = aioredis.Redis(connection_pool=pool)

            # Test connection
            await client.ping()

            self._async_pool = pool
            self._async_client = client
            logger.info("✅ Redis asynchronous connection established")
            return client

        except Exception as e:
            logger.error(f"❌ Failed to create Redis async connection: {e}")
            self._stats["errors"] += 1
            self._stats["last_error"] = str(e)
            raise
    
    def get_sync_client(self) -> redis.Redis:
        """Get synchronous Redis client with connection management"""
        if not self._sync_client:
            self._sync_client = self._create_sync_connection()
        
        try:
            # Test connection
            self._sync_client.ping()
            self._is_connected = True
            return self._sync_client
        except Exception as e:
            logger.warning(f"Redis connection lost, attempting to reconnect: {e}")
            try:
                self._sync_client = self._create_sync_connection()
                return self._sync_client
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect to Redis: {reconnect_error}")
                self._is_connected = False
                raise
    
    async def get_async_client(self) -> Any:
        """Get asynchronous Redis client with connection management"""
        if not self._async_client:
            self._async_client = await self._create_async_connection()
        
        try:
            # Test connection
            await self._async_client.ping()
            self._is_connected = True
            return self._async_client
        except Exception as e:
            logger.warning(f"Async Redis connection lost, attempting to reconnect: {e}")
            try:
                self._async_client = await self._create_async_connection()
                return self._async_client
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect to async Redis: {reconnect_error}")
                self._is_connected = False
                raise
    
    def _make_key(self, *parts: str) -> str:
        """Create a properly prefixed cache key"""
        return settings.redis.key_prefix + ":".join(str(part) for part in parts)
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for Redis storage"""
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        return str(value)
    
    def _deserialize_value(self, value: str) -> Any:
        """Deserialize value from Redis"""
        if not value:
            return None
        
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache (synchronous)"""
        self._stats["total_requests"] += 1
        
        try:
            client = self.get_sync_client()
            cache_key = self._make_key(key)
            
            value = client.get(cache_key)
            if value is not None:
                self._stats["hits"] += 1
                return self._deserialize_value(value)
            else:
                self._stats["misses"] += 1
                return default
                
        except Exception as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            self._stats["errors"] += 1
            self._stats["misses"] += 1
            self._stats["last_error"] = str(e)
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache (synchronous)"""
        try:
            client = self.get_sync_client()
            cache_key = self._make_key(key)
            serialized_value = self._serialize_value(value)
            
            if ttl is None:
                ttl = settings.redis.default_ttl
            
            success = client.setex(cache_key, ttl, serialized_value)
            return bool(success)
            
        except Exception as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            self._stats["errors"] += 1
            self._stats["last_error"] = str(e)
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache (synchronous)"""
        try:
            client = self.get_sync_client()
            cache_key = self._make_key(key)
            
            deleted_count = client.delete(cache_key)
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")
            self._stats["errors"] += 1
            self._stats["last_error"] = str(e)
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern (synchronous)"""
        try:
            client = self.get_sync_client()
            cache_pattern = self._make_key(pattern)
            
            keys = client.keys(cache_pattern)
            if keys:
                deleted_count = client.delete(*keys)
                logger.info(f"Deleted {deleted_count} keys matching pattern '{pattern}'")
                return deleted_count
            return 0
            
        except Exception as e:
            logger.error(f"Redis DELETE_PATTERN error for pattern '{pattern}': {e}")
            self._stats["errors"] += 1
            self._stats["last_error"] = str(e)
            return 0
    
    async def aget(self, key: str, default: Any = None) -> Any:
        """Get value from cache (asynchronous)"""
        self._stats["total_requests"] += 1
        
        try:
            client = await self.get_async_client()
            cache_key = self._make_key(key)
            
            value = await client.get(cache_key)
            if value is not None:
                self._stats["hits"] += 1
                return self._deserialize_value(value)
            else:
                self._stats["misses"] += 1
                return default
                
        except Exception as e:
            logger.error(f"Async Redis GET error for key '{key}': {e}")
            self._stats["errors"] += 1
            self._stats["misses"] += 1
            self._stats["last_error"] = str(e)
            return default
    
    async def aset(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache (asynchronous)"""
        try:
            client = await self.get_async_client()
            cache_key = self._make_key(key)
            serialized_value = self._serialize_value(value)
            
            if ttl is None:
                ttl = settings.redis.default_ttl
            
            success = await client.setex(cache_key, ttl, serialized_value)
            return bool(success)
            
        except Exception as e:
            logger.error(f"Async Redis SET error for key '{key}': {e}")
            self._stats["errors"] += 1
            self._stats["last_error"] = str(e)
            return False
    
    async def adelete(self, key: str) -> bool:
        """Delete value from cache (asynchronous)"""
        try:
            client = await self.get_async_client()
            cache_key = self._make_key(key)
            
            deleted_count = await client.delete(cache_key)
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Async Redis DELETE error for key '{key}': {e}")
            self._stats["errors"] += 1
            self._stats["last_error"] = str(e)
            return False
    
    async def adelete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern (asynchronous)"""
        try:
            client = await self.get_async_client()
            cache_pattern = self._make_key(pattern)
            
            keys = await client.keys(cache_pattern)
            if keys:
                deleted_count = await client.delete(*keys)
                logger.info(f"Deleted {deleted_count} keys matching pattern '{pattern}'")
                return deleted_count
            return 0
            
        except Exception as e:
            logger.error(f"Async Redis DELETE_PATTERN error for pattern '{pattern}': {e}")
            self._stats["errors"] += 1
            self._stats["last_error"] = str(e)
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """Perform Redis health check"""
        try:
            start_time = dt.datetime.now()
            client = self.get_sync_client()
            
            # Basic connectivity test
            client.ping()
            
            # Performance test
            test_key = self._make_key("health_check", str(start_time.timestamp()))
            client.set(test_key, "OK", ex=10)  # 10 second expiry
            retrieved = client.get(test_key)
            client.delete(test_key)
            
            response_time = (dt.datetime.now() - start_time).total_seconds() * 1000
            
            self._last_health_check = dt.datetime.now()
            self._is_connected = True
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "connection_pool_size": len(self._sync_pool._available_connections) if self._sync_pool else 0,
                "is_connected": self._is_connected,
                "last_check": self._last_health_check.isoformat(),
                "stats": self.get_stats()
            }
            
        except Exception as e:
            self._is_connected = False
            self._stats["errors"] += 1
            self._stats["last_error"] = str(e)
            
            return {
                "status": "unhealthy",
                "error": str(e),
                "is_connected": self._is_connected,
                "last_check": dt.datetime.now().isoformat(),
                "stats": self.get_stats()
            }
    
    async def ahealth_check(self) -> Dict[str, Any]:
        """Perform async Redis health check"""
        try:
            start_time = dt.datetime.now()
            client = await self.get_async_client()
            
            # Basic connectivity test
            await client.ping()
            
            # Performance test
            test_key = self._make_key("async_health_check", str(start_time.timestamp()))
            await client.setex(test_key, 10, "OK")  # 10 second expiry
            retrieved = await client.get(test_key)
            await client.delete(test_key)
            
            response_time = (dt.datetime.now() - start_time).total_seconds() * 1000
            
            self._last_health_check = dt.datetime.now()
            self._is_connected = True
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "is_connected": self._is_connected,
                "last_check": self._last_health_check.isoformat(),
                "stats": self.get_stats()
            }
            
        except Exception as e:
            self._is_connected = False
            self._stats["errors"] += 1
            self._stats["last_error"] = str(e)
            
            return {
                "status": "unhealthy",
                "error": str(e),
                "is_connected": self._is_connected,
                "last_check": dt.datetime.now().isoformat(),
                "stats": self.get_stats()
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "errors": self._stats["errors"],
            "total_requests": self._stats["total_requests"],
            "hit_rate_percent": round(hit_rate, 2),
            "last_error": self._stats["last_error"],
            "is_connected": self._is_connected
        }
    
    def reset_stats(self) -> None:
        """Reset cache statistics"""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "total_requests": 0,
            "last_error": None
        }
        logger.info("Cache statistics reset")
    
    def close(self) -> None:
        """Close Redis connections"""
        try:
            if self._sync_pool:
                self._sync_pool.disconnect()
                logger.info("Redis synchronous connection pool closed")
            
            if self._async_pool:
                asyncio.create_task(self._async_pool.disconnect())
                logger.info("Redis asynchronous connection pool closed")
                
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.close()


# Fallback in-memory cache for when Redis is unavailable
class InMemoryCacheService:
    """In-memory fallback cache when Redis is unavailable"""
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}  # key -> {value, expires_at}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "total_requests": 0,
            "last_error": None
        }
        logger.info("🔄 Using in-memory cache fallback (Redis unavailable)")
    
    def _is_expired(self, entry: Dict) -> bool:
        """Check if cache entry is expired"""
        if 'expires_at' not in entry:
            return False
        return dt.datetime.now().timestamp() > entry['expires_at']
    
    def _make_key(self, *parts: str) -> str:
        """Create a cache key"""
        return ":".join(str(part) for part in parts)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from in-memory cache"""
        self._stats["total_requests"] += 1
        cache_key = self._make_key(key)
        
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if not self._is_expired(entry):
                self._stats["hits"] += 1
                return entry['value']
            else:
                # Clean up expired entry
                del self._cache[cache_key]
        
        self._stats["misses"] += 1
        return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in in-memory cache"""
        try:
            cache_key = self._make_key(key)
            
            entry = {'value': value}
            if ttl is not None:
                entry['expires_at'] = dt.datetime.now().timestamp() + ttl
            
            self._cache[cache_key] = entry
            return True
        except Exception as e:
            self._stats["errors"] += 1
            self._stats["last_error"] = str(e)
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from in-memory cache"""
        cache_key = self._make_key(key)
        if cache_key in self._cache:
            del self._cache[cache_key]
            return True
        return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        cache_pattern = self._make_key(pattern)
        # Simple pattern matching with * wildcards
        import fnmatch
        keys_to_delete = [k for k in self._cache.keys() if fnmatch.fnmatch(k, cache_pattern)]
        for key in keys_to_delete:
            del self._cache[key]
        return len(keys_to_delete)
    
    # Async methods (same as sync for in-memory)
    async def aget(self, key: str, default: Any = None) -> Any:
        return self.get(key, default)
    
    async def aset(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        return self.set(key, value, ttl)
    
    async def adelete(self, key: str) -> bool:
        return self.delete(key)
    
    async def adelete_pattern(self, pattern: str) -> int:
        return self.delete_pattern(pattern)
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for in-memory cache"""
        return {
            "status": "healthy",
            "cache_type": "in_memory_fallback",
            "response_time_ms": 0.1,  # Very fast for in-memory
            "is_connected": True,
            "last_check": dt.datetime.now().isoformat(),
            "stats": self.get_stats(),
            "cache_size": len(self._cache)
        }
    
    async def ahealth_check(self) -> Dict[str, Any]:
        """Async health check"""
        return self.health_check()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "errors": self._stats["errors"],
            "total_requests": self._stats["total_requests"],
            "hit_rate_percent": round(hit_rate, 2),
            "last_error": self._stats["last_error"],
            "is_connected": True,
            "cache_type": "in_memory_fallback"
        }


# Global cache instance
_redis_cache_instance: Optional[Union[RedisCacheService, InMemoryCacheService]] = None


def get_redis_cache() -> Union[RedisCacheService, InMemoryCacheService]:
    """Get cache instance (Redis if available, in-memory fallback otherwise)"""
    global _redis_cache_instance
    
    if _redis_cache_instance is None:
        try:
            # Try to initialize Redis cache first
            _redis_cache_instance = RedisCacheService()
            # Test Redis connection
            _redis_cache_instance.health_check()
            logger.info("✅ Redis cache service initialized")
        except Exception as e:
            # Fall back to in-memory cache
            logger.warning(f"⚠️  Redis unavailable ({e}), using in-memory cache fallback")
            _redis_cache_instance = InMemoryCacheService()
    
    return _redis_cache_instance


def invalidate_cache_for_user(user_id: Optional[str] = None) -> int:
    """Invalidate all cache entries for a specific user or all users"""
    cache = get_redis_cache()
    
    if user_id:
        pattern = f"user:{user_id}:*"
    else:
        pattern = "*"
    
    deleted_count = cache.delete_pattern(pattern)
    logger.info(f"Invalidated {deleted_count} cache entries for user pattern '{pattern}'")
    return deleted_count


def invalidate_cache_for_month(month: str, user_id: Optional[str] = None) -> int:
    """Invalidate cache entries for a specific month"""
    cache = get_redis_cache()
    
    if user_id:
        pattern = f"user:{user_id}:*:{month}:*"
    else:
        pattern = f"*:{month}:*"
    
    deleted_count = cache.delete_pattern(pattern)
    logger.info(f"Invalidated {deleted_count} cache entries for month '{month}'")
    return deleted_count


async def warm_cache_for_month(db_session, month: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Warm up cache for a specific month with common calculations"""
    from services.calculations import (
        calculate_monthly_trends, calculate_category_breakdown,
        calculate_kpi_summary, detect_anomalies, calculate_spending_patterns
    )
    
    cache = get_redis_cache()
    warmed_keys = []
    errors = []
    
    try:
        # Warm monthly trends
        trends = calculate_monthly_trends(db_session, [month])
        key = f"monthly_trends:{month}"
        if user_id:
            key = f"user:{user_id}:{key}"
        await cache.aset(key, trends, ttl=settings.redis.trends_ttl)
        warmed_keys.append(key)
        
        # Warm category breakdown
        breakdown = calculate_category_breakdown(db_session, month)
        key = f"category_breakdown:{month}"
        if user_id:
            key = f"user:{user_id}:{key}"
        await cache.aset(key, breakdown, ttl=settings.redis.default_ttl)
        warmed_keys.append(key)
        
        # Warm KPI summary
        kpi_summary = calculate_kpi_summary(db_session, [month])
        key = f"kpi_summary:{month}"
        if user_id:
            key = f"user:{user_id}:{key}"
        await cache.aset(key, kpi_summary, ttl=settings.redis.summary_ttl)
        warmed_keys.append(key)
        
        # Warm anomaly detection
        anomalies = detect_anomalies(db_session, month)
        key = f"anomalies:{month}"
        if user_id:
            key = f"user:{user_id}:{key}"
        await cache.aset(key, anomalies, ttl=settings.redis.anomaly_ttl)
        warmed_keys.append(key)
        
        # Warm spending patterns (last 6 months including current)
        try:
            year, month_num = map(int, month.split('-'))
            months = []
            for i in range(6):
                calc_month_num = month_num - i
                calc_year = year
                if calc_month_num <= 0:
                    calc_month_num += 12
                    calc_year -= 1
                months.append(f"{calc_year:04d}-{calc_month_num:02d}")
            
            patterns = calculate_spending_patterns(db_session, months)
            key = f"spending_patterns:{month}"
            if user_id:
                key = f"user:{user_id}:{key}"
            await cache.aset(key, patterns, ttl=settings.redis.trends_ttl)
            warmed_keys.append(key)
            
        except Exception as e:
            errors.append(f"Failed to warm spending patterns: {e}")
        
    except Exception as e:
        errors.append(f"Cache warming error: {e}")
    
    return {
        "warmed_keys": warmed_keys,
        "errors": errors,
        "total_warmed": len(warmed_keys)
    }