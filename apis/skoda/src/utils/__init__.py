"""
Skoda Connect API Utilities
Infrastructure utilities for production-ready Skoda Connect API integration
"""

from .circuit_breaker import (
    SkodaCircuitBreaker,
    CircuitState,
    circuit_breaker
)
from .cache_manager import (
    SkodaCacheManager,
    CacheEntry,
    cached
)
from .error_handler import (
    SkodaAPIError,
    SkodaErrorCode,
    AuthenticationError,
    SpinRequiredError,
    ValidationError,
    VehicleError,
    RemoteServiceError,
    RateLimitError,
    ExternalServiceError,
    TimeoutError,
    create_error_response,
    handle_api_error,
    error_tracker,
    map_http_error
)
from .rate_limiter import (
    SkodaRateLimiter,
    RateLimitRule,
    UserRateLimit,
    rate_limit
)
from .logger import (
    SkodaLoggerManager,
    get_logger,
    set_request_context,
    clear_request_context,
    LoggingContext
)

__version__ = "1.0.0"
__author__ = "DRAIV Development Team"

__all__ = [
    # Circuit Breaker
    "SkodaCircuitBreaker",
    "CircuitState", 
    "circuit_breaker",
    
    # Cache Manager
    "SkodaCacheManager",
    "CacheEntry",
    "cached",
    
    # Error Handling
    "SkodaAPIError",
    "SkodaErrorCode",
    "AuthenticationError",
    "SpinRequiredError",
    "ValidationError",
    "VehicleError",
    "RemoteServiceError",
    "RateLimitError",
    "ExternalServiceError",
    "TimeoutError",
    "create_error_response",
    "handle_api_error",
    "error_tracker",
    "map_http_error",
    
    # Rate Limiter
    "SkodaRateLimiter",
    "RateLimitRule",
    "UserRateLimit",
    "rate_limit",
    
    # Logger
    "SkodaLoggerManager",
    "get_logger",
    "set_request_context", 
    "clear_request_context",
    "LoggingContext",
]

# Default configurations optimized for Skoda Connect API
DEFAULT_CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 5,
    "recovery_timeout": 60,
    "name": "skoda-connect"
}

DEFAULT_CACHE_CONFIG = {
    "max_memory_size": 1000,
    "default_ttl": 300,
    "key_prefix": "skoda:",
    "ttls": {
        "vehicle_list": 300,    # 5 minutes
        "vehicle_status": 60,   # 1 minute
        "location": 30,         # 30 seconds
        "auth_token": 3600,     # 1 hour
        "user_info": 1800,      # 30 minutes
        "trip_data": 900,       # 15 minutes
    }
}

DEFAULT_RATE_LIMIT_CONFIG = {
    "limits": {
        "status": {"requests": 30, "window": 60, "burst_requests": 10, "burst_window": 10},
        "control": {"requests": 10, "window": 60, "burst_requests": 3, "burst_window": 10},
        "auth": {"requests": 5, "window": 60, "burst_requests": 2, "burst_window": 30},
        "location": {"requests": 60, "window": 60, "burst_requests": 15, "burst_window": 10},
        "trip": {"requests": 20, "window": 60, "burst_requests": 5, "burst_window": 15},
    }
}

DEFAULT_LOGGER_CONFIG = {
    "name": "skoda-connect-api",
    "level": "INFO",
    "json_format": True,
    "console_output": True,
    "max_file_size": 50 * 1024 * 1024,  # 50MB
    "backup_count": 5
}

def create_default_infrastructure():
    """
    Create default infrastructure components for Skoda Connect API
    
    Returns:
        Dictionary with pre-configured infrastructure components
    """
    import os
    
    # Get configuration from environment or use defaults
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    log_dir = os.getenv("LOG_DIR", "./logs")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    # Create components
    circuit_breaker = SkodaCircuitBreaker(**DEFAULT_CIRCUIT_BREAKER_CONFIG)
    
    cache_manager = SkodaCacheManager(
        redis_url=redis_url,
        **DEFAULT_CACHE_CONFIG
    )
    
    rate_limiter = SkodaRateLimiter(
        redis_url=redis_url,
        **DEFAULT_RATE_LIMIT_CONFIG
    )
    
    logger_manager = SkodaLoggerManager(
        level=log_level,
        log_dir=log_dir if os.path.exists(os.path.dirname(log_dir) or ".") else None,
        **{k: v for k, v in DEFAULT_LOGGER_CONFIG.items() if k not in ["name", "level"]}
    )
    
    return {
        "circuit_breaker": circuit_breaker,
        "cache_manager": cache_manager,
        "rate_limiter": rate_limiter,
        "logger_manager": logger_manager,
        "logger": logger_manager.get_logger()
    }

def get_component_health():
    """
    Get health status of all infrastructure components
    
    Returns:
        Dictionary with health status of each component
    """
    health = {
        "timestamp": get_logger().handlers[0].formatter.formatTime(None) if get_logger().handlers else None,
        "components": {}
    }
    
    try:
        # This would require actual component instances
        # For now, return basic health check structure
        health["components"] = {
            "circuit_breaker": {"status": "unknown", "message": "No instance available"},
            "cache_manager": {"status": "unknown", "message": "No instance available"},
            "rate_limiter": {"status": "unknown", "message": "No instance available"},
            "logger": {"status": "healthy", "message": "Logger is operational"},
            "error_tracker": {"status": "healthy", "message": "Error tracker is operational"}
        }
        
        health["overall_status"] = "operational"
        
    except Exception as e:
        health["overall_status"] = "degraded"
        health["error"] = str(e)
    
    return health

# Utility functions for common patterns
def setup_request_logging(request_id: str, user_id: str, operation: str):
    """
    Setup logging context for a request
    
    Args:
        request_id: Unique request identifier
        user_id: User making the request
        operation: Operation being performed
    """
    set_request_context(request_id, user_id, operation)
    logger = get_logger()
    logger.info(f"Starting {operation} for user", extra={
        "event_type": "request_start",
        "operation": operation,
        "user_id": user_id,
        "request_id": request_id
    })

def cleanup_request_logging(request_id: str, success: bool = True, duration_ms: float = None):
    """
    Cleanup logging context after request completion
    
    Args:
        request_id: Request identifier
        success: Whether request was successful
        duration_ms: Request duration in milliseconds
    """
    logger = get_logger()
    logger.info("Request completed", extra={
        "event_type": "request_end",
        "request_id": request_id,
        "success": success,
        "duration_ms": duration_ms
    })
    clear_request_context()

# Version information
def get_version_info():
    """Get version and component information"""
    return {
        "version": __version__,
        "author": __author__,
        "components": {
            "circuit_breaker": "Production-ready circuit breaker with failure detection",
            "cache_manager": "Redis-backed cache with memory fallback",
            "error_handler": "Skoda-specific error handling with tracking",
            "rate_limiter": "Per-user rate limiting with sliding window",
            "logger": "Structured logging with security filtering"
        },
        "features": [
            "Security filtering (masks sensitive data)",
            "Performance monitoring",
            "Request tracing", 
            "Error tracking and analytics",
            "Circuit breaker pattern",
            "Distributed caching",
            "Rate limiting",
            "Structured JSON logging"
        ]
    }