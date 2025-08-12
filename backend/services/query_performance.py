"""
Query Performance Monitoring Service for Budget Famille v2.3

Provides real-time query performance monitoring, slow query detection,
and database optimization recommendations.
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine
from sqlalchemy import event, text

logger = logging.getLogger(__name__)


@dataclass
class QueryMetric:
    """Single query execution metric"""
    query_hash: str
    sql_text: str
    execution_time: float
    timestamp: datetime
    parameters: Dict = field(default_factory=dict)
    result_count: Optional[int] = None
    table_names: List[str] = field(default_factory=list)
    is_slow: bool = False


@dataclass
class QueryStats:
    """Aggregated statistics for a query pattern"""
    query_hash: str
    sql_pattern: str
    total_executions: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    median_time: float = 0.0
    p95_time: float = 0.0
    slow_query_count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    recent_executions: deque = field(default_factory=lambda: deque(maxlen=100))


class QueryPerformanceMonitor:
    """Advanced query performance monitoring and analysis"""
    
    def __init__(self, slow_query_threshold: float = 1.0, enable_monitoring: bool = True):
        self.slow_query_threshold = slow_query_threshold  # seconds
        self.enable_monitoring = enable_monitoring
        self.metrics_lock = threading.Lock()
        
        # Storage for query metrics
        self.query_stats: Dict[str, QueryStats] = {}
        self.recent_queries: deque = deque(maxlen=1000)  # Last 1000 queries
        self.slow_queries: deque = deque(maxlen=100)     # Last 100 slow queries
        
        # Performance thresholds
        self.performance_thresholds = {
            'critical': 2.0,    # > 2 seconds
            'warning': 1.0,     # > 1 second
            'info': 0.5,        # > 0.5 seconds
        }
        
        # Query pattern cache
        self.query_patterns: Dict[str, str] = {}
        
        logger.info(f"Query performance monitor initialized (threshold: {slow_query_threshold}s)")
    
    def _normalize_query(self, sql: str) -> str:
        """Normalize SQL query to create a pattern for grouping similar queries"""
        import re
        
        # Convert to lowercase and remove extra whitespace
        normalized = re.sub(r'\s+', ' ', sql.lower().strip())
        
        # Replace literal values with placeholders
        # Numbers
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        # String literals
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        # IN clauses with multiple values
        normalized = re.sub(r'in\s*\([^)]+\)', 'in (?)', normalized)
        
        return normalized
    
    def _extract_table_names(self, sql: str) -> List[str]:
        """Extract table names from SQL query"""
        import re
        
        # Simple regex to find table names after FROM and JOIN
        tables = []
        
        # FROM clause
        from_matches = re.findall(r'\bfrom\s+(\w+)', sql.lower())
        tables.extend(from_matches)
        
        # JOIN clauses
        join_matches = re.findall(r'\bjoin\s+(\w+)', sql.lower())
        tables.extend(join_matches)
        
        # UPDATE and DELETE
        update_matches = re.findall(r'\bupdate\s+(\w+)', sql.lower())
        tables.extend(update_matches)
        
        delete_matches = re.findall(r'\bdelete\s+from\s+(\w+)', sql.lower())
        tables.extend(delete_matches)
        
        return list(set(tables))  # Remove duplicates
    
    def _calculate_query_hash(self, sql: str) -> str:
        """Calculate hash for query pattern grouping"""
        import hashlib
        pattern = self._normalize_query(sql)
        return hashlib.md5(pattern.encode()).hexdigest()[:12]
    
    def record_query(self, sql: str, execution_time: float, parameters: Dict = None, result_count: int = None):
        """Record a query execution metric"""
        if not self.enable_monitoring:
            return
        
        timestamp = datetime.now()
        query_hash = self._calculate_query_hash(sql)
        table_names = self._extract_table_names(sql)
        is_slow = execution_time > self.slow_query_threshold
        
        metric = QueryMetric(
            query_hash=query_hash,
            sql_text=sql[:500],  # Truncate very long queries
            execution_time=execution_time,
            timestamp=timestamp,
            parameters=parameters or {},
            result_count=result_count,
            table_names=table_names,
            is_slow=is_slow
        )
        
        with self.metrics_lock:
            # Add to recent queries
            self.recent_queries.append(metric)
            
            # Track slow queries
            if is_slow:
                self.slow_queries.append(metric)
                logger.warning(f"Slow query detected ({execution_time:.3f}s): {sql[:100]}...")
            
            # Update aggregated statistics
            if query_hash not in self.query_stats:
                pattern = self._normalize_query(sql)
                self.query_stats[query_hash] = QueryStats(
                    query_hash=query_hash,
                    sql_pattern=pattern,
                    first_seen=timestamp
                )
            
            stats = self.query_stats[query_hash]
            stats.total_executions += 1
            stats.total_time += execution_time
            stats.last_seen = timestamp
            stats.recent_executions.append(execution_time)
            
            if execution_time < stats.min_time:
                stats.min_time = execution_time
            if execution_time > stats.max_time:
                stats.max_time = execution_time
            
            if is_slow:
                stats.slow_query_count += 1
            
            # Calculate statistics
            if stats.total_executions > 0:
                stats.avg_time = stats.total_time / stats.total_executions
                
                if len(stats.recent_executions) > 1:
                    recent_times = list(stats.recent_executions)
                    stats.median_time = statistics.median(recent_times)
                    stats.p95_time = statistics.quantiles(recent_times, n=20)[18]  # 95th percentile
    
    @contextmanager
    def monitor_query(self, sql: str, parameters: Dict = None):
        """Context manager for monitoring query execution"""
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            self.record_query(sql, execution_time, parameters)
    
    def get_performance_summary(self, hours: int = 24) -> Dict:
        """Get performance summary for the specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.metrics_lock:
            # Filter recent queries
            recent = [q for q in self.recent_queries if q.timestamp > cutoff_time]
            slow_recent = [q for q in recent if q.is_slow]
            
            if not recent:
                return {
                    'period_hours': hours,
                    'total_queries': 0,
                    'slow_queries': 0,
                    'average_time': 0.0,
                    'median_time': 0.0,
                    'p95_time': 0.0,
                    'status': 'no_data'
                }
            
            # Calculate metrics
            execution_times = [q.execution_time for q in recent]
            total_queries = len(recent)
            slow_queries = len(slow_recent)
            
            summary = {
                'period_hours': hours,
                'total_queries': total_queries,
                'slow_queries': slow_queries,
                'slow_query_percentage': (slow_queries / total_queries) * 100,
                'average_time': statistics.mean(execution_times),
                'median_time': statistics.median(execution_times),
                'min_time': min(execution_times),
                'max_time': max(execution_times),
                'total_time': sum(execution_times),
                'queries_per_hour': total_queries / hours,
            }
            
            if len(execution_times) > 1:
                summary['p95_time'] = statistics.quantiles(execution_times, n=20)[18]
            else:
                summary['p95_time'] = execution_times[0] if execution_times else 0
            
            # Performance status
            if summary['p95_time'] > self.performance_thresholds['critical']:
                summary['status'] = 'critical'
            elif summary['p95_time'] > self.performance_thresholds['warning']:
                summary['status'] = 'warning'
            elif summary['p95_time'] > self.performance_thresholds['info']:
                summary['status'] = 'info'
            else:
                summary['status'] = 'good'
            
            return summary
    
    def get_slowest_queries(self, limit: int = 10) -> List[Dict]:
        """Get the slowest query patterns"""
        with self.metrics_lock:
            # Sort by average execution time
            sorted_stats = sorted(
                self.query_stats.values(),
                key=lambda s: s.avg_time,
                reverse=True
            )
            
            return [{
                'query_hash': stats.query_hash,
                'sql_pattern': stats.sql_pattern[:200],
                'total_executions': stats.total_executions,
                'avg_time': stats.avg_time,
                'max_time': stats.max_time,
                'p95_time': stats.p95_time,
                'slow_query_count': stats.slow_query_count,
                'slow_percentage': (stats.slow_query_count / stats.total_executions) * 100,
                'last_seen': stats.last_seen.isoformat() if stats.last_seen else None,
            } for stats in sorted_stats[:limit]]
    
    def get_table_performance(self) -> Dict[str, Dict]:
        """Get performance statistics by table"""
        table_stats = defaultdict(lambda: {
            'query_count': 0,
            'total_time': 0.0,
            'slow_queries': 0,
            'avg_time': 0.0,
            'max_time': 0.0
        })
        
        with self.metrics_lock:
            for metric in self.recent_queries:
                for table in metric.table_names:
                    stats = table_stats[table]
                    stats['query_count'] += 1
                    stats['total_time'] += metric.execution_time
                    stats['max_time'] = max(stats['max_time'], metric.execution_time)
                    
                    if metric.is_slow:
                        stats['slow_queries'] += 1
            
            # Calculate averages
            for table, stats in table_stats.items():
                if stats['query_count'] > 0:
                    stats['avg_time'] = stats['total_time'] / stats['query_count']
                    stats['slow_percentage'] = (stats['slow_queries'] / stats['query_count']) * 100
        
        return dict(table_stats)
    
    def get_optimization_recommendations(self) -> List[Dict]:
        """Generate database optimization recommendations"""
        recommendations = []
        
        with self.metrics_lock:
            # Analyze query patterns for optimization opportunities
            for stats in self.query_stats.values():
                if stats.slow_query_count > 0 and stats.total_executions >= 5:
                    recommendation = {
                        'type': 'slow_query_pattern',
                        'priority': 'high' if stats.avg_time > 2.0 else 'medium',
                        'query_pattern': stats.sql_pattern[:200],
                        'issue': f'Query pattern executing slowly ({stats.avg_time:.3f}s avg)',
                        'frequency': stats.total_executions,
                        'impact_score': stats.slow_query_count * stats.avg_time,
                    }
                    
                    # Specific recommendations based on query patterns
                    if 'where month =' in stats.sql_pattern and 'exclude =' in stats.sql_pattern:
                        recommendation['suggestion'] = 'Consider composite index on (month, exclude, is_expense)'
                    elif 'where category =' in stats.sql_pattern and 'month =' in stats.sql_pattern:
                        recommendation['suggestion'] = 'Consider composite index on (category, month)'
                    elif 'order by' in stats.sql_pattern and 'where' in stats.sql_pattern:
                        recommendation['suggestion'] = 'Consider index covering WHERE and ORDER BY columns'
                    else:
                        recommendation['suggestion'] = 'Analyze query execution plan for index opportunities'
                    
                    recommendations.append(recommendation)
            
            # Table-level recommendations
            table_perf = self.get_table_performance()
            for table, stats in table_perf.items():
                if stats['slow_percentage'] > 20 and stats['query_count'] > 10:
                    recommendations.append({
                        'type': 'table_performance',
                        'priority': 'medium',
                        'table': table,
                        'issue': f'Table {table} has {stats["slow_percentage"]:.1f}% slow queries',
                        'suggestion': f'Review indexes on {table} table for optimization',
                        'impact_score': stats['slow_queries'] * stats['avg_time']
                    })
        
        # Sort by impact score
        recommendations.sort(key=lambda r: r.get('impact_score', 0), reverse=True)
        
        return recommendations[:10]  # Top 10 recommendations
    
    def clear_metrics(self):
        """Clear all collected metrics"""
        with self.metrics_lock:
            self.query_stats.clear()
            self.recent_queries.clear()
            self.slow_queries.clear()
            logger.info("Query performance metrics cleared")
    
    def export_metrics_report(self) -> Dict:
        """Export comprehensive metrics report"""
        return {
            'report_timestamp': datetime.now().isoformat(),
            'monitoring_enabled': self.enable_monitoring,
            'slow_query_threshold': self.slow_query_threshold,
            'performance_summary_24h': self.get_performance_summary(24),
            'performance_summary_1h': self.get_performance_summary(1),
            'slowest_queries': self.get_slowest_queries(20),
            'table_performance': self.get_table_performance(),
            'optimization_recommendations': self.get_optimization_recommendations(),
            'total_tracked_patterns': len(self.query_stats),
            'recent_queries_count': len(self.recent_queries),
            'slow_queries_count': len(self.slow_queries)
        }


# Global performance monitor instance
query_monitor = QueryPerformanceMonitor(
    slow_query_threshold=1.0,
    enable_monitoring=True
)


def setup_sqlalchemy_monitoring(engine: Engine):
    """Setup SQLAlchemy event listeners for automatic query monitoring"""
    
    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()
    
    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if hasattr(context, '_query_start_time'):
            execution_time = time.time() - context._query_start_time
            query_monitor.record_query(
                sql=statement,
                execution_time=execution_time,
                parameters=parameters if isinstance(parameters, dict) else {},
                result_count=cursor.rowcount if hasattr(cursor, 'rowcount') else None
            )
    
    logger.info("SQLAlchemy query monitoring enabled")


# Decorator for monitoring function-level queries
def monitor_query_performance(func: Callable) -> Callable:
    """Decorator to monitor query performance in service functions"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Record function-level performance
            query_monitor.record_query(
                sql=f"FUNCTION: {func.__name__}",
                execution_time=execution_time,
                parameters={'args_count': len(args), 'kwargs_count': len(kwargs)},
            )
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper


def get_query_performance_report() -> Dict:
    """Get comprehensive query performance report"""
    return query_monitor.export_metrics_report()


def optimize_query_performance() -> Dict:
    """Get optimization recommendations"""
    return {
        'timestamp': datetime.now().isoformat(),
        'recommendations': query_monitor.get_optimization_recommendations(),
        'performance_summary': query_monitor.get_performance_summary(24),
        'slowest_queries': query_monitor.get_slowest_queries(10)
    }