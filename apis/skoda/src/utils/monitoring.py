"""
Monitoring and Metrics Collection for Skoda API
"""
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from collections import defaultdict, Counter
import threading

logger = logging.getLogger(__name__)

class MetricsCollector:
    """
    Collects and tracks API metrics
    """
    
    def __init__(self, service_name: str = "skoda-api"):
        self.service_name = service_name
        self.start_time = datetime.utcnow()
        
        # Thread-safe counters
        self._lock = threading.RLock()
        
        # Basic metrics
        self.counters = defaultdict(int)
        self.timers = defaultdict(list)
        self.gauges = {}
        
        # Request tracking
        self.request_counts = Counter()
        self.error_counts = Counter()
        self.response_times = []
        
        # Circuit breaker events
        self.circuit_breaker_events = []
        
        # Cache metrics
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    def increment(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric"""
        with self._lock:
            key = self._make_key(metric_name, tags)
            self.counters[key] += value
    
    def gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric"""
        with self._lock:
            key = self._make_key(metric_name, tags)
            self.gauges[key] = value
    
    def timing(self, metric_name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timing metric"""
        with self._lock:
            key = self._make_key(metric_name, tags)
            self.timers[key].append(duration)
            
            # Keep only last 1000 measurements for memory efficiency
            if len(self.timers[key]) > 1000:
                self.timers[key] = self.timers[key][-1000:]
    
    def track_request(
        self, 
        method: str, 
        endpoint: str, 
        status_code: int, 
        duration: float
    ) -> None:
        """Track HTTP request metrics"""
        with self._lock:
            # Count requests
            self.request_counts[f"{method}_{endpoint}"] += 1
            
            # Track errors
            if status_code >= 400:
                self.error_counts[f"{status_code}_{endpoint}"] += 1
            
            # Track response times
            self.response_times.append(duration)
            
            # Keep only last 1000 response times
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
    
    def track_circuit_breaker_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Track circuit breaker events"""
        with self._lock:
            event = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": event_type,
                "details": details
            }
            self.circuit_breaker_events.append(event)
            
            # Keep only last 100 events
            if len(self.circuit_breaker_events) > 100:
                self.circuit_breaker_events = self.circuit_breaker_events[-100:]
    
    def track_cache_hit(self) -> None:
        """Track cache hit"""
        with self._lock:
            self.cache_stats["hits"] += 1
    
    def track_cache_miss(self) -> None:
        """Track cache miss"""
        with self._lock:
            self.cache_stats["misses"] += 1
    
    def track_cache_set(self) -> None:
        """Track cache set operation"""
        with self._lock:
            self.cache_stats["sets"] += 1
    
    def track_cache_delete(self) -> None:
        """Track cache delete operation"""
        with self._lock:
            self.cache_stats["deletes"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        with self._lock:
            now = datetime.utcnow()
            uptime_seconds = (now - self.start_time).total_seconds()
            
            metrics = {
                "service": self.service_name,
                "timestamp": now.isoformat(),
                "uptime_seconds": uptime_seconds,
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "timers": self._summarize_timers(),
                "requests": self._get_request_metrics(),
                "cache": self._get_cache_metrics(),
                "circuit_breaker": {
                    "recent_events": len(self.circuit_breaker_events),
                    "last_event": self.circuit_breaker_events[-1] if self.circuit_breaker_events else None
                }
            }
            
            return metrics
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics including detailed stats"""
        base_metrics = self.get_metrics()
        
        # Add detailed breakdowns
        base_metrics["detailed"] = {
            "request_breakdown": dict(self.request_counts),
            "error_breakdown": dict(self.error_counts),
            "circuit_breaker_events": self.circuit_breaker_events[-10:],  # Last 10 events
            "response_time_percentiles": self._calculate_percentiles(self.response_times)
        }
        
        return base_metrics
    
    def _make_key(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Create metric key with optional tags"""
        if not tags:
            return metric_name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{metric_name}[{tag_str}]"
    
    def _summarize_timers(self) -> Dict[str, Dict[str, float]]:
        """Summarize timer metrics with stats"""
        summaries = {}
        
        for timer_name, values in self.timers.items():
            if values:
                summaries[timer_name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "p50": self._percentile(values, 50),
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99)
                }
            else:
                summaries[timer_name] = {
                    "count": 0,
                    "min": 0,
                    "max": 0,
                    "avg": 0,
                    "p50": 0,
                    "p95": 0,
                    "p99": 0
                }
        
        return summaries
    
    def _get_request_metrics(self) -> Dict[str, Any]:
        """Get request-related metrics"""
        total_requests = sum(self.request_counts.values())
        total_errors = sum(self.error_counts.values())
        
        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": (total_errors / total_requests * 100) if total_requests > 0 else 0,
            "avg_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
            "response_time_p95": self._percentile(self.response_times, 95) if self.response_times else 0
        }
    
    def _get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache-related metrics"""
        total_operations = self.cache_stats["hits"] + self.cache_stats["misses"]
        
        return {
            **self.cache_stats,
            "hit_rate": (self.cache_stats["hits"] / total_operations * 100) if total_operations > 0 else 0,
            "total_operations": total_operations
        }
    
    def _percentile(self, values: list, percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * percentile / 100
        f = int(k)
        c = k - f
        
        if f == len(sorted_values) - 1:
            return sorted_values[f]
        
        return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c
    
    def _calculate_percentiles(self, values: list) -> Dict[str, float]:
        """Calculate common percentiles"""
        if not values:
            return {"p50": 0, "p90": 0, "p95": 0, "p99": 0}
        
        return {
            "p50": self._percentile(values, 50),
            "p90": self._percentile(values, 90),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99)
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing)"""
        with self._lock:
            self.counters.clear()
            self.gauges.clear()
            self.timers.clear()
            self.request_counts.clear()
            self.error_counts.clear()
            self.response_times.clear()
            self.circuit_breaker_events.clear()
            
            self.cache_stats = {
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "deletes": 0
            }
            
            self.start_time = datetime.utcnow()

class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, metrics_collector: MetricsCollector, metric_name: str, tags: Optional[Dict[str, str]] = None):
        self.metrics_collector = metrics_collector
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.metrics_collector.timing(self.metric_name, duration, self.tags)
        
        # Track errors if exception occurred
        if exc_type:
            self.metrics_collector.increment("errors", tags={"type": exc_type.__name__})

def timed_operation(metrics_collector: MetricsCollector, operation_name: str):
    """Decorator for timing function calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with PerformanceTimer(metrics_collector, f"operation_{operation_name}"):
                return func(*args, **kwargs)
        return wrapper
    return decorator