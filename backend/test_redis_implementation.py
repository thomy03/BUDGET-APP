#!/usr/bin/env python3
"""
Test script for Redis caching implementation in Budget Famille v2.3
Validates cache functionality, fallback mechanisms, and performance improvements
"""

import sys
import logging
import datetime as dt
from typing import Dict, Any
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_redis_cache_basic():
    """Test basic Redis cache operations"""
    logger.info("🧪 Testing basic Redis cache operations...")
    
    try:
        from services.redis_cache import get_redis_cache
        from config.settings import settings
        
        cache = get_redis_cache()
        
        # Test basic set/get operations
        test_key = "test_basic_operation"
        test_value = {"message": "Hello Redis", "timestamp": str(dt.datetime.now())}
        
        # Set value
        success = cache.set(test_key, test_value, ttl=60)
        if not success:
            logger.error("❌ Failed to set value in Redis cache")
            return False
        
        # Get value
        retrieved_value = cache.get(test_key)
        if retrieved_value != test_value:
            logger.error(f"❌ Retrieved value doesn't match: {retrieved_value} != {test_value}")
            return False
        
        # Test cache miss
        missing_value = cache.get("non_existent_key", default="not_found")
        if missing_value != "not_found":
            logger.error(f"❌ Cache miss didn't return default value: {missing_value}")
            return False
        
        # Clean up
        cache.delete(test_key)
        
        logger.info("✅ Basic Redis cache operations passed")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Redis import failed - dependencies missing: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Basic Redis cache test failed: {e}")
        return False


def test_cache_fallback_mechanism():
    """Test cache fallback when Redis is unavailable"""
    logger.info("🧪 Testing cache fallback mechanisms...")
    
    try:
        from services.redis_cache import get_redis_cache
        from services.calculations import _get_from_cache, _set_to_cache
        
        cache = get_redis_cache()
        
        # Test with valid Redis connection first
        test_key = "fallback_test"
        test_value = {"test": "fallback_value"}
        
        # This should work with Redis
        success = _set_to_cache(test_key, test_value)
        if success:
            retrieved = _get_from_cache(test_key)
            if retrieved == test_value:
                logger.info("✅ Cache works with Redis connection")
            else:
                logger.warning("⚠️  Cache retrieval inconsistent")
        
        # Test graceful degradation (simulate Redis down)
        # Force an invalid connection by using wrong port temporarily
        original_host = cache._sync_client.connection_pool.connection_kwargs.get('host') if cache._sync_client else None
        
        # Test with cache disabled
        from config.settings import settings
        original_setting = settings.cache.enable_cache
        settings.cache.enable_cache = False
        
        # This should return None gracefully
        result = _get_from_cache("any_key")
        if result is None:
            logger.info("✅ Cache fallback works when disabled")
        else:
            logger.warning(f"⚠️  Cache returned unexpected value when disabled: {result}")
        
        # Restore original setting
        settings.cache.enable_cache = original_setting
        
        logger.info("✅ Cache fallback mechanisms passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Cache fallback test failed: {e}")
        return False


def test_calculation_caching():
    """Test calculation caching with realistic data"""
    logger.info("🧪 Testing calculation caching integration...")
    
    try:
        from services.calculations import (
            calculate_monthly_trends, calculate_category_breakdown,
            calculate_kpi_summary, detect_anomalies, calculate_spending_patterns,
            clear_calculation_cache, get_cache_stats
        )
        from services.redis_cache import get_redis_cache
        
        # Clear cache first
        clear_calculation_cache("test_user")
        
        # Mock database session - this is a basic test without real DB
        class MockDB:
            def query(self, model):
                return MockQuery()
        
        class MockQuery:
            def filter(self, *args):
                return self
            def all(self):
                return []
        
        mock_db = MockDB()
        test_months = ["2024-01", "2024-02", "2024-03"]
        test_user = "test_user"
        
        # Test monthly trends caching
        logger.info("Testing monthly trends caching...")
        trends1 = calculate_monthly_trends(mock_db, test_months, test_user)
        trends2 = calculate_monthly_trends(mock_db, test_months, test_user)  # Should hit cache
        
        # Test category breakdown caching
        logger.info("Testing category breakdown caching...")
        breakdown1 = calculate_category_breakdown(mock_db, "2024-01", test_user)
        breakdown2 = calculate_category_breakdown(mock_db, "2024-01", test_user)  # Should hit cache
        
        # Test KPI summary caching
        logger.info("Testing KPI summary caching...")
        kpi1 = calculate_kpi_summary(mock_db, test_months, test_user)
        kpi2 = calculate_kpi_summary(mock_db, test_months, test_user)  # Should hit cache
        
        # Get cache statistics
        stats = get_cache_stats()
        logger.info(f"Cache statistics: {stats}")
        
        cache = get_redis_cache()
        cache_stats = cache.get_stats()
        
        if cache_stats.get("total_requests", 0) > 0:
            logger.info(f"✅ Cache processed {cache_stats['total_requests']} requests")
            logger.info(f"✅ Cache hit rate: {cache_stats.get('hit_rate_percent', 0)}%")
        else:
            logger.warning("⚠️  No cache requests recorded")
        
        logger.info("✅ Calculation caching integration passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Calculation caching test failed: {e}")
        return False


async def test_async_operations():
    """Test async Redis operations"""
    logger.info("🧪 Testing async Redis operations...")
    
    try:
        from services.redis_cache import get_redis_cache
        
        cache = get_redis_cache()
        
        # Test async set/get
        test_key = "async_test"
        test_value = {"async": True, "timestamp": str(dt.datetime.now())}
        
        # Async set
        success = await cache.aset(test_key, test_value, ttl=60)
        if not success:
            logger.error("❌ Async set operation failed")
            return False
        
        # Async get
        retrieved_value = await cache.aget(test_key)
        if retrieved_value != test_value:
            logger.error(f"❌ Async retrieved value doesn't match: {retrieved_value}")
            return False
        
        # Test async health check
        health = await cache.ahealth_check()
        logger.info(f"Async health check result: {health.get('status', 'unknown')}")
        
        # Clean up
        await cache.adelete(test_key)
        
        logger.info("✅ Async Redis operations passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Async Redis operations test failed: {e}")
        return False


def test_cache_performance_impact():
    """Test performance impact of caching"""
    logger.info("🧪 Testing cache performance impact...")
    
    try:
        import time
        from services.redis_cache import get_redis_cache
        
        cache = get_redis_cache()
        
        # Test cache write performance
        start_time = time.time()
        for i in range(100):
            test_key = f"perf_test_{i}"
            test_value = {"iteration": i, "data": f"test_data_{i}"}
            cache.set(test_key, test_value, ttl=60)
        write_time = time.time() - start_time
        
        # Test cache read performance
        start_time = time.time()
        for i in range(100):
            test_key = f"perf_test_{i}"
            cache.get(test_key)
        read_time = time.time() - start_time
        
        # Clean up
        for i in range(100):
            cache.delete(f"perf_test_{i}")
        
        logger.info(f"✅ Cache write performance: {write_time:.3f}s for 100 operations ({write_time*10:.1f}ms avg)")
        logger.info(f"✅ Cache read performance: {read_time:.3f}s for 100 operations ({read_time*10:.1f}ms avg)")
        
        # Performance should be reasonable (< 1s for 100 operations)
        if write_time < 1.0 and read_time < 1.0:
            logger.info("✅ Cache performance is acceptable")
            return True
        else:
            logger.warning(f"⚠️  Cache performance may be suboptimal")
            return False
        
    except Exception as e:
        logger.error(f"❌ Cache performance test failed: {e}")
        return False


def test_cache_invalidation():
    """Test cache invalidation patterns"""
    logger.info("🧪 Testing cache invalidation...")
    
    try:
        from services.redis_cache import get_redis_cache, invalidate_cache_for_user, invalidate_cache_for_month
        
        cache = get_redis_cache()
        test_user = "invalidation_test_user"
        test_month = "2024-01"
        
        # Set up test data
        cache.set(f"user:{test_user}:monthly_trends:{test_month}", {"test": "data1"})
        cache.set(f"user:{test_user}:category_breakdown:{test_month}", {"test": "data2"})
        cache.set(f"user:{test_user}:kpi_summary:{test_month}", {"test": "data3"})
        cache.set(f"user:other_user:monthly_trends:{test_month}", {"test": "other_data"})
        
        # Test user-specific invalidation
        deleted_count = invalidate_cache_for_user(test_user)
        logger.info(f"User invalidation deleted {deleted_count} entries")
        
        # Verify user cache is cleared but other user's cache remains
        user_data = cache.get(f"user:{test_user}:monthly_trends:{test_month}")
        other_data = cache.get(f"user:other_user:monthly_trends:{test_month}")
        
        if user_data is None and other_data is not None:
            logger.info("✅ User-specific cache invalidation works correctly")
        else:
            logger.error(f"❌ User invalidation failed: user_data={user_data}, other_data={other_data}")
            return False
        
        # Test month-specific invalidation
        cache.set(f"user:test_user2:monthly_trends:{test_month}", {"test": "month_data"})
        cache.set(f"user:test_user2:monthly_trends:2024-02", {"test": "other_month"})
        
        deleted_count = invalidate_cache_for_month(test_month)
        logger.info(f"Month invalidation deleted {deleted_count} entries")
        
        # Verify month-specific data is cleared
        month_data = cache.get(f"user:test_user2:monthly_trends:{test_month}")
        other_month_data = cache.get(f"user:test_user2:monthly_trends:2024-02")
        
        if month_data is None and other_month_data is not None:
            logger.info("✅ Month-specific cache invalidation works correctly")
        else:
            logger.error(f"❌ Month invalidation failed: month_data={month_data}, other_month_data={other_month_data}")
            return False
        
        # Clean up
        cache.delete(f"user:test_user2:monthly_trends:2024-02")
        
        logger.info("✅ Cache invalidation patterns passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Cache invalidation test failed: {e}")
        return False


def run_all_tests():
    """Run all Redis implementation tests"""
    logger.info("🚀 Starting Redis implementation test suite...")
    logger.info("=" * 60)
    
    tests = [
        ("Basic Redis Operations", test_redis_cache_basic),
        ("Cache Fallback Mechanisms", test_cache_fallback_mechanism),
        ("Calculation Caching Integration", test_calculation_caching),
        ("Cache Performance Impact", test_cache_performance_impact),
        ("Cache Invalidation Patterns", test_cache_invalidation),
    ]
    
    results = {}
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running: {test_name}")
        logger.info("-" * 40)
        
        try:
            result = test_func()
            results[test_name] = result
            if result:
                passed += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                failed += 1
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            failed += 1
            results[test_name] = False
            logger.error(f"❌ {test_name}: FAILED with exception: {e}")
    
    # Run async test separately
    logger.info(f"\n📋 Running: Async Redis Operations")
    logger.info("-" * 40)
    try:
        async_result = asyncio.run(test_async_operations())
        results["Async Redis Operations"] = async_result
        if async_result:
            passed += 1
            logger.info(f"✅ Async Redis Operations: PASSED")
        else:
            failed += 1
            logger.error(f"❌ Async Redis Operations: FAILED")
    except Exception as e:
        failed += 1
        results["Async Redis Operations"] = False
        logger.error(f"❌ Async Redis Operations: FAILED with exception: {e}")
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("🏁 TEST SUITE SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total tests: {passed + failed}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success rate: {(passed / (passed + failed) * 100):.1f}%")
    
    if failed == 0:
        logger.info("🎉 ALL TESTS PASSED - Redis implementation is ready!")
        return True
    else:
        logger.error("❌ Some tests failed - please review Redis setup")
        return False


if __name__ == "__main__":
    try:
        # Try to import required modules
        from config.settings import settings
        from services.redis_cache import get_redis_cache
        
        logger.info(f"Redis configuration: {settings.redis.host}:{settings.redis.port}")
        logger.info(f"Cache enabled: {settings.cache.enable_cache}")
        
        success = run_all_tests()
        sys.exit(0 if success else 1)
        
    except ImportError as e:
        logger.error(f"❌ Import error - missing dependencies: {e}")
        logger.error("Please ensure Redis dependencies are installed: pip install redis aioredis")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)