#!/usr/bin/env python3
"""
Redis Cache Performance Monitoring for Budget Famille v2.3
Monitors cache performance, hit rates, and provides optimization recommendations
"""

import time
import json
import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheMonitor:
    """Monitor Redis cache performance and health"""
    
    def __init__(self):
        self.metrics_history: List[Dict[str, Any]] = []
        self.monitoring = False
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect current cache metrics"""
        try:
            from services.redis_cache import get_redis_cache
            from services.calculations import get_cache_stats
            
            cache = get_redis_cache()
            
            # Get current stats
            stats = cache.get_stats()
            health = await cache.ahealth_check()
            
            # Calculate additional metrics
            current_time = datetime.now()
            
            metrics = {
                "timestamp": current_time.isoformat(),
                "stats": stats,
                "health": health,
                "performance": {
                    "response_time_ms": health.get("response_time_ms", 0),
                    "hit_rate_percent": stats.get("hit_rate_percent", 0),
                    "total_requests": stats.get("total_requests", 0),
                    "error_count": stats.get("errors", 0)
                }
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect cache metrics: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "available": False
            }
    
    def analyze_performance(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cache performance and provide recommendations"""
        performance = metrics.get("performance", {})
        hit_rate = performance.get("hit_rate_percent", 0)
        response_time = performance.get("response_time_ms", 0)
        error_count = performance.get("error_count", 0)
        total_requests = performance.get("total_requests", 0)
        
        analysis = {
            "overall_grade": "N/A",
            "strengths": [],
            "issues": [],
            "recommendations": []
        }
        
        # Analyze hit rate
        if hit_rate >= 80:
            analysis["strengths"].append(f"Excellent cache hit rate: {hit_rate:.1f}%")
            hit_grade = "A"
        elif hit_rate >= 60:
            analysis["strengths"].append(f"Good cache hit rate: {hit_rate:.1f}%")
            hit_grade = "B"
        elif hit_rate >= 40:
            analysis["issues"].append(f"Fair cache hit rate: {hit_rate:.1f}%")
            analysis["recommendations"].append("Consider implementing cache warming strategies")
            hit_grade = "C"
        else:
            analysis["issues"].append(f"Poor cache hit rate: {hit_rate:.1f}%")
            analysis["recommendations"].append("Review caching strategy and implement cache warming")
            hit_grade = "D"
        
        # Analyze response time
        if response_time <= 10:
            analysis["strengths"].append(f"Excellent response time: {response_time:.1f}ms")
            response_grade = "A"
        elif response_time <= 50:
            analysis["strengths"].append(f"Good response time: {response_time:.1f}ms")
            response_grade = "B"
        elif response_time <= 100:
            analysis["issues"].append(f"Fair response time: {response_time:.1f}ms")
            analysis["recommendations"].append("Monitor Redis server performance")
            response_grade = "C"
        else:
            analysis["issues"].append(f"Poor response time: {response_time:.1f}ms")
            analysis["recommendations"].append("Check Redis server resources and network latency")
            response_grade = "D"
        
        # Analyze error rate
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        if error_rate == 0:
            analysis["strengths"].append("No cache errors detected")
            error_grade = "A"
        elif error_rate < 1:
            analysis["strengths"].append(f"Low error rate: {error_rate:.2f}%")
            error_grade = "B"
        elif error_rate < 5:
            analysis["issues"].append(f"Moderate error rate: {error_rate:.2f}%")
            analysis["recommendations"].append("Review Redis connection stability")
            error_grade = "C"
        else:
            analysis["issues"].append(f"High error rate: {error_rate:.2f}%")
            analysis["recommendations"].append("Investigate Redis connectivity issues")
            error_grade = "D"
        
        # Calculate overall grade
        grades = {"A": 4, "B": 3, "C": 2, "D": 1}
        avg_grade = (grades[hit_grade] + grades[response_grade] + grades[error_grade]) / 3
        
        if avg_grade >= 3.5:
            analysis["overall_grade"] = "A"
        elif avg_grade >= 2.5:
            analysis["overall_grade"] = "B"
        elif avg_grade >= 1.5:
            analysis["overall_grade"] = "C"
        else:
            analysis["overall_grade"] = "D"
        
        return analysis
    
    def print_metrics_report(self, metrics: Dict[str, Any], analysis: Dict[str, Any]):
        """Print formatted metrics report"""
        print("=" * 60)
        print("📊 REDIS CACHE PERFORMANCE REPORT")
        print("=" * 60)
        print(f"Timestamp: {metrics.get('timestamp', 'N/A')}")
        print(f"Overall Grade: {analysis['overall_grade']}")
        print()
        
        # Performance metrics
        performance = metrics.get("performance", {})
        print("📈 PERFORMANCE METRICS:")
        print(f"  Hit Rate:      {performance.get('hit_rate_percent', 0):.1f}%")
        print(f"  Response Time: {performance.get('response_time_ms', 0):.1f}ms")
        print(f"  Total Requests: {performance.get('total_requests', 0)}")
        print(f"  Errors:        {performance.get('error_count', 0)}")
        print()
        
        # Health status
        health = metrics.get("health", {})
        print("🏥 HEALTH STATUS:")
        print(f"  Status: {health.get('status', 'unknown').upper()}")
        print(f"  Connected: {health.get('is_connected', False)}")
        print()
        
        # Analysis
        if analysis["strengths"]:
            print("✅ STRENGTHS:")
            for strength in analysis["strengths"]:
                print(f"  • {strength}")
            print()
        
        if analysis["issues"]:
            print("⚠️  ISSUES:")
            for issue in analysis["issues"]:
                print(f"  • {issue}")
            print()
        
        if analysis["recommendations"]:
            print("💡 RECOMMENDATIONS:")
            for rec in analysis["recommendations"]:
                print(f"  • {rec}")
            print()
        
        print("=" * 60)
    
    async def monitor_continuous(self, interval: int = 30, duration: int = 300):
        """Monitor cache performance continuously"""
        logger.info(f"Starting continuous monitoring (interval: {interval}s, duration: {duration}s)")
        
        self.monitoring = True
        start_time = time.time()
        
        try:
            while self.monitoring and (time.time() - start_time) < duration:
                # Collect metrics
                metrics = await self.collect_metrics()
                analysis = self.analyze_performance(metrics)
                
                # Store in history
                self.metrics_history.append({
                    "metrics": metrics,
                    "analysis": analysis
                })
                
                # Print report
                self.print_metrics_report(metrics, analysis)
                
                # Wait for next interval
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        finally:
            self.monitoring = False
    
    def save_metrics_history(self, filename: str = None):
        """Save metrics history to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cache_metrics_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.metrics_history, f, indent=2, default=str)
            
            logger.info(f"Metrics history saved to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to save metrics history: {e}")
            return None
    
    def generate_performance_summary(self) -> Dict[str, Any]:
        """Generate performance summary from history"""
        if not self.metrics_history:
            return {"error": "No metrics history available"}
        
        # Calculate averages
        hit_rates = []
        response_times = []
        error_counts = []
        
        for entry in self.metrics_history:
            performance = entry.get("metrics", {}).get("performance", {})
            hit_rates.append(performance.get("hit_rate_percent", 0))
            response_times.append(performance.get("response_time_ms", 0))
            error_counts.append(performance.get("error_count", 0))
        
        summary = {
            "monitoring_period": {
                "start": self.metrics_history[0]["metrics"]["timestamp"],
                "end": self.metrics_history[-1]["metrics"]["timestamp"],
                "data_points": len(self.metrics_history)
            },
            "averages": {
                "hit_rate_percent": sum(hit_rates) / len(hit_rates) if hit_rates else 0,
                "response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
                "total_errors": sum(error_counts)
            },
            "trends": {
                "hit_rate_trend": "improving" if hit_rates[-1] > hit_rates[0] else "declining" if hit_rates[-1] < hit_rates[0] else "stable",
                "response_time_trend": "improving" if response_times[-1] < response_times[0] else "declining" if response_times[-1] > response_times[0] else "stable"
            }
        }
        
        return summary


async def main():
    """Main monitoring function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Redis Cache Performance Monitor")
    parser.add_argument("--mode", choices=["single", "continuous"], default="single",
                       help="Monitoring mode (default: single)")
    parser.add_argument("--interval", type=int, default=30,
                       help="Monitoring interval in seconds (default: 30)")
    parser.add_argument("--duration", type=int, default=300,
                       help="Monitoring duration in seconds (default: 300)")
    parser.add_argument("--save", action="store_true",
                       help="Save metrics to file")
    
    args = parser.parse_args()
    
    monitor = CacheMonitor()
    
    try:
        if args.mode == "single":
            # Single metrics collection
            metrics = await monitor.collect_metrics()
            analysis = monitor.analyze_performance(metrics)
            monitor.print_metrics_report(metrics, analysis)
            
        elif args.mode == "continuous":
            # Continuous monitoring
            await monitor.monitor_continuous(args.interval, args.duration)
            
            # Generate summary
            summary = monitor.generate_performance_summary()
            print("\n📋 MONITORING SUMMARY:")
            print(json.dumps(summary, indent=2, default=str))
        
        if args.save and monitor.metrics_history:
            filename = monitor.save_metrics_history()
            if filename:
                print(f"\n💾 Metrics saved to: {filename}")
                
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user")
        exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)